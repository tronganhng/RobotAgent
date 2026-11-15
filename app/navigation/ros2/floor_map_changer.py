"""Load a floor map and relocalize at the cabin, following elevator_manager."""

import asyncio
import math
from pathlib import Path
import threading
import time

from app.navigation.ros2.quaternion import quaternion_to_yaw, yaw_to_quaternion
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics


class FloorMapChanger:
    # All waits are asynchronous: the application owns the ROS executor thread.
    SERVICE_TIMEOUT = 10.0
    LOAD_TIMEOUT = 20.0
    LOCALIZATION_TIMEOUT = 25.0
    MAP_SETTLE_SECONDS = 1.0
    PUBLISH_COUNT = 5
    PUBLISH_INTERVAL = 0.3
    STABLE_SECONDS = 1.0
    AMCL_SETTLE_SECONDS = 5.0
    MAX_POSE_AGE = 2.0
    POSITION_TOLERANCE = 0.75
    YAW_TOLERANCE = math.radians(20)
    POLL_INTERVAL = 0.05

    def __init__(self, node, config_path, robot_namespace=DEFAULT_ROBOT_NAMESPACE):
        from geometry_msgs.msg import PoseWithCovarianceStamped
        from nav2_msgs.srv import LoadMap
        from std_srvs.srv import Empty

        self.node = node
        self.config_path = Path(config_path)
        self.topics = RobotTopics(robot_namespace)
        self._pose_type = PoseWithCovarianceStamped
        self._load_map_type = LoadMap
        self._empty_type = Empty
        self._nomotion_client = node.create_client(Empty, self.topics.request_nomotion_update)
        self._client = node.create_client(LoadMap, self.topics.load_map)
        self._publisher = node.create_publisher(
            PoseWithCovarianceStamped, self.topics.initial_pose, 10
        )
        self._sample_lock = threading.Lock()
        self._sample = None
        self._operation_lock = asyncio.Lock()
        # Volatile subscription avoids accepting a retained pose from the old map.
        self._subscription = node.create_subscription(
            PoseWithCovarianceStamped, self.topics.amcl_pose, self._on_pose, 10
        )

    def _configuration(self, elevator_id, floor):
        import yaml

        with self.config_path.open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
        if not isinstance(config, dict) or config.get("elevator_id") != elevator_id:
            raise ValueError(f"Elevator {elevator_id!r} is not configured in {self.config_path}.")
        entry = config.get(f"floor_{floor}")
        if not isinstance(entry, dict) or not isinstance(entry.get("parking_pose"), dict):
            raise ValueError(f"Floor {floor} requires a map_file and cabin parking_pose.")
        map_file = entry.get("map_file")
        if not isinstance(map_file, str) or not map_file.strip():
            raise ValueError(f"Floor {floor} has no map_file.")
        pose = tuple(float(entry["parking_pose"][key]) for key in ("x", "y", "yaw"))
        if not all(math.isfinite(value) for value in pose):
            raise ValueError("Cabin parking_pose must contain finite coordinates and yaw.")
        return map_file, pose

    def _on_pose(self, message):
        if message.header.frame_id != "map":
            return
        pose = message.pose.pose
        orientation = pose.orientation
        yaw = quaternion_to_yaw(orientation.x, orientation.y, orientation.z, orientation.w)
        stamp = message.header.stamp
        sample = (time.monotonic(), stamp.sec * 1_000_000_000 + stamp.nanosec,
                  pose.position.x, pose.position.y, yaw)
        with self._sample_lock:
            self._sample = sample

    async def _wait_response(self, future):
        try:
            while not future.done():
                await asyncio.sleep(self.POLL_INTERVAL)
            return future.result()
        finally:
            if not future.done():
                # Cancels local waiting; LoadMap has no physical rollback contract.
                future.cancel()

    async def change_floor(self, elevator_id, target_floor):
        async with self._operation_lock:
            map_file, parking = self._configuration(elevator_id, target_floor)
            self.node.get_logger().info(f"Loading floor {target_floor}: {map_file}")
            deadline = time.monotonic() + self.SERVICE_TIMEOUT
            while not self._client.service_is_ready():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Map service unavailable: {self.topics.load_map}")
                await asyncio.sleep(self.POLL_INTERVAL)

            request = self._load_map_type.Request()
            request.map_url = map_file
            response = await asyncio.wait_for(
                self._wait_response(self._client.call_async(request)), self.LOAD_TIMEOUT
            )
            if response is None or response.result != 0:
                raise RuntimeError(f"LoadMap failed: result={getattr(response, 'result', None)}")

            await asyncio.sleep(self.MAP_SETTLE_SECONDS)
            initial = self._pose_type()
            initial.header.frame_id = "map"
            initial.pose.pose.position.x, initial.pose.pose.position.y = parking[:2]
            q = yaw_to_quaternion(parking[2])
            orientation = initial.pose.pose.orientation
            orientation.x, orientation.y, orientation.z, orientation.w = q
            covariance = [0.0] * 36
            covariance[0] = covariance[7] = 0.04
            covariance[35] = 0.03046
            initial.pose.covariance = covariance

            # Reject poses generated before this new initial pose, including queued callbacks.
            started = time.monotonic()
            ros_started = self.node.get_clock().now().nanoseconds
            with self._sample_lock:
                self._sample = None
            for _ in range(self.PUBLISH_COUNT):
                initial.header.stamp = self.node.get_clock().now().to_msg()
                self._publisher.publish(initial)
                await asyncio.sleep(self.PUBLISH_INTERVAL)

            # AMCL may otherwise suppress updates while the robot is stationary.
            self._nomotion_future = None
            try:
                await self._wait_localization(parking, started, ros_started)
            finally:
                if self._nomotion_future is not None and not self._nomotion_future.done():
                    self._nomotion_future.cancel()
            self.node.get_logger().info(f"Floor {target_floor} map and cabin localization ready.")
            return True

    async def _wait_localization(self, parking, started, ros_started):
        deadline = time.monotonic() + self.LOCALIZATION_TIMEOUT
        stable_since = None
        next_update = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_update and self._nomotion_client.service_is_ready():
                if self._nomotion_future is None or self._nomotion_future.done():
                    if self._nomotion_future is not None:
                        self._nomotion_future.result()
                    self._nomotion_future = self._nomotion_client.call_async(self._empty_type.Request())
                    next_update = now + 0.5
            with self._sample_lock:
                sample = self._sample
            valid = False
            if sample is not None:
                received, stamp, x, y, yaw = sample
                yaw_error = math.atan2(math.sin(yaw - parking[2]), math.cos(yaw - parking[2]))
                valid = (
                    received >= started and stamp >= ros_started
                    and now - received <= self.MAX_POSE_AGE
                    and all(math.isfinite(v) for v in (x, y, yaw))
                    and math.hypot(x - parking[0], y - parking[1]) <= self.POSITION_TOLERANCE
                    and abs(yaw_error) <= self.YAW_TOLERANCE
                )
            if valid:
                if stable_since is None:
                    stable_since = now
                elif now - stable_since >= self.STABLE_SECONDS + self.AMCL_SETTLE_SECONDS:
                    return
            else:
                stable_since = None
            await asyncio.sleep(self.POLL_INTERVAL)
        raise TimeoutError("AMCL did not stabilize at the target floor cabin parking_pose.")
