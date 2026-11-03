import logging
import math
from typing import Tuple

from geometry_msgs.msg import PoseWithCovarianceStamped
from sensor_msgs.msg import BatteryState
from rclpy.qos import (
    QoSDurabilityPolicy,
    QoSHistoryPolicy,
    QoSProfile,
    QoSReliabilityPolicy,
    qos_profile_sensor_data,
)

from app.navigation.ros2.quaternion import quaternion_to_yaw
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics

logger = logging.getLogger("RobotAgent")


class Odometry:
    """
    Maintains the robot's map pose from AMCL and battery state.

    The historical class name is retained for callers; pose is never read
    directly from odom, whose coordinates differ from Nav2 map goals.

    The robot namespace is configurable and defaults to ``robot3``.
    """

    def __init__(
        self,
        node,
        robot_namespace: str = DEFAULT_ROBOT_NAMESPACE,
    ) -> None:
        if node is None:
            raise ValueError("Odometry requires an rclpy Node.")

        self.node = node
        self.topics = RobotTopics(robot_namespace)
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: float = 0.0
        self.battery: float = 0.0
        self._odom_received: bool = False
        self._battery_received: bool = False

        # AMCL retains its latest pose; receive it even when this agent starts
        # after localization and the robot has not moved to trigger an update.
        pose_qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._pose_subscription = self.node.create_subscription(
            PoseWithCovarianceStamped,
            self.topics.amcl_pose,
            self._amcl_pose_callback,
            pose_qos,
        )
        self._battery_subscription = self.node.create_subscription(
            BatteryState,
            self.topics.battery_state,
            self._battery_callback,
            qos_profile_sensor_data,
        )
        logger.info("[Odometry] Subscribed to %s.", self.topics.amcl_pose)
        logger.info("[Odometry] Subscribed to %s.", self.topics.battery_state)

    def _amcl_pose_callback(self, msg: PoseWithCovarianceStamped) -> None:
        if msg.header.frame_id != "map":
            logger.warning("[Odometry] Ignoring pose in frame %r; expected map.", msg.header.frame_id)
            return
        pose = msg.pose.pose
        self.x = pose.position.x
        self.y = pose.position.y

        self.rotation = quaternion_to_yaw(
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )
        self._odom_received = True

    @property
    def odom_received(self) -> bool:
        """Compatibility flag: True once an AMCL map pose has arrived."""
        return self._odom_received

    def _battery_callback(self, msg: BatteryState) -> None:
        try:
            percentage = float(msg.percentage)
        except (AttributeError, TypeError, ValueError):
            return

        if not math.isfinite(percentage) or not 0.0 <= percentage <= 1.0:
            return

        self.battery = percentage * 100.0
        self._battery_received = True

    @property
    def battery_received(self) -> bool:
        return self._battery_received

    def get_current_pose(self) -> Tuple[float, float, float, float]:
        """Returns map (x, y), yaw in radians, and battery in percent."""
        if not self._odom_received:
            raise RuntimeError("No AMCL pose in map frame has been received yet.")
        return self.x, self.y, self.rotation, self.battery
