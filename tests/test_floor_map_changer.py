import asyncio
import copy
import math
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.navigation.ros2.floor_map_changer import FloorMapChanger
from app.navigation.ros2_navigation import ROS2Navigation


class PoseMessage:
    def __init__(self):
        self.header = NS(frame_id="map", stamp=NS(sec=0, nanosec=0))
        self.pose = NS(pose=NS(position=NS(x=0., y=0., z=0.),
                               orientation=NS(x=0., y=0., z=0., w=1.)), covariance=[])


def stamp():
    value = time.monotonic_ns()
    return NS(sec=value // 1_000_000_000, nanosec=value % 1_000_000_000)


class TestFloorMapChanger(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / "elevator.yaml"
        self.config.write_text('''elevator_id: Elevator_01
floor_2:
  map_file: /robot/maps/floor2.yaml
  parking_pose: {x: 3.0, y: 4.0, yaw: 1.0}
''')
        self.node = MagicMock()
        self.client = MagicMock()
        self.client.service_is_ready.return_value = True
        self.response = NS(result=0)
        self.client.call_async.side_effect = self.load_map
        self.nomotion = MagicMock()
        self.nomotion.service_is_ready.return_value = True
        self.nomotion.call_async.side_effect = self.no_motion
        self.node.create_client.side_effect = [self.nomotion, self.client]
        self.node.get_clock.return_value.now.side_effect = lambda: NS(
            nanoseconds=time.monotonic_ns(), to_msg=stamp)
        self.published = []
        self.node.create_publisher.return_value.publish.side_effect = lambda p: self.published.append(copy.deepcopy(p))
        modules = {
            "geometry_msgs.msg": NS(PoseWithCovarianceStamped=PoseMessage),
            "nav2_msgs.srv": NS(LoadMap=NS(Request=NS)),
            "std_srvs.srv": NS(Empty=NS(Request=NS)),
        }
        with patch.dict('sys.modules', modules):
            self.changer = FloorMapChanger(self.node, self.config, "warehouse/robot7")
        self.changer.MAP_SETTLE_SECONDS = 0
        self.changer.PUBLISH_INTERVAL = .001
        self.changer.POLL_INTERVAL = .001
        self.changer.STABLE_SECONDS = .01
        self.changer.AMCL_SETTLE_SECONDS = .01
        self.changer.LOCALIZATION_TIMEOUT = .06
        self.changer.MAX_POSE_AGE = .01
        self.changer.SERVICE_TIMEOUT = .01
        self.changer.LOAD_TIMEOUT = .01

    def load_map(self, request):
        future = asyncio.get_running_loop().create_future()
        future.set_result(self.response)
        return future

    def no_motion(self, request):
        future = asyncio.get_running_loop().create_future()
        future.set_result(NS())
        return future

    def pose(self, x=3., y=4., yaw=1., old=False, frame="map"):
        message = PoseMessage()
        message.header.frame_id = frame
        message.header.stamp = NS(sec=0, nanosec=0) if old else stamp()
        message.pose.pose.position.x = x
        message.pose.pose.position.y = y
        message.pose.pose.orientation.z = math.sin(yaw / 2)
        message.pose.pose.orientation.w = math.cos(yaw / 2)
        return message

    async def feed(self, **kwargs):
        while True:
            self.changer._on_pose(self.pose(**kwargs))
            await asyncio.sleep(.002)

    async def change_with_pose(self, **kwargs):
        task = asyncio.create_task(self.feed(**kwargs))
        try:
            return await self.changer.change_floor("Elevator_01", 2)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def test_load_then_publish_cabin_pose_and_wait_for_localization(self):
        self.assertTrue(await self.change_with_pose())
        self.assertEqual(self.client.call_async.call_args.args[0].map_url, "/robot/maps/floor2.yaml")
        self.assertEqual(len(self.published), 5)
        initial = self.published[-1]
        self.assertEqual(initial.header.frame_id, "map")
        self.assertEqual(initial.pose.pose.position.x, 3.)
        self.assertEqual(initial.pose.pose.position.y, 4.)
        self.assertAlmostEqual(initial.pose.pose.orientation.z, math.sin(.5))
        self.assertEqual(initial.pose.covariance[0], .04)
        self.nomotion.call_async.assert_called()
        self.assertEqual(self.node.create_client.call_args.args[1], "/warehouse/robot7/map_server/load_map")
        self.assertEqual(self.node.create_publisher.call_args.args[1], "/warehouse/robot7/initialpose")
        self.assertEqual(self.node.create_subscription.call_args.args[1], "/warehouse/robot7/amcl_pose")

    async def test_reject_wrong_floor_or_elevator_before_ros_commands(self):
        for elevator, floor in (("Other", 2), ("Elevator_01", 9)):
            with self.assertRaises(ValueError):
                await self.changer.change_floor(elevator, floor)
        self.client.call_async.assert_not_called()

    async def test_load_failure_does_not_publish_initial_pose(self):
        for response in (None, NS(result=1)):
            self.response = response
            with self.assertRaises(RuntimeError):
                await self.changer.change_floor("Elevator_01", 2)
        self.assertEqual(self.published, [])

    async def test_unavailable_service_times_out(self):
        self.client.service_is_ready.return_value = False
        with self.assertRaisesRegex(TimeoutError, "unavailable"):
            await self.changer.change_floor("Elevator_01", 2)
        self.client.call_async.assert_not_called()

    async def test_wrong_position_heading_frame_and_old_stamp_do_not_acknowledge(self):
        for pose in ({"x": 20.}, {"yaw": -2.}, {"old": True}, {"frame": "odom"}, {"x": float('nan')}):
            with self.subTest(pose=pose), self.assertRaisesRegex(TimeoutError, "AMCL"):
                await self.change_with_pose(**pose)

    async def test_single_old_cached_pose_does_not_establish_stability(self):
        self.changer._on_pose(self.pose())
        with self.assertRaisesRegex(TimeoutError, "AMCL"):
            await self.changer.change_floor("Elevator_01", 2)

    async def test_load_timeout_and_cancellation_cancel_local_future(self):
        for cancel in (False, True):
            future = asyncio.get_running_loop().create_future()
            self.client.call_async.side_effect = lambda request: future
            task = asyncio.create_task(self.changer.change_floor("Elevator_01", 2))
            if cancel:
                await asyncio.sleep(.002)
                task.cancel()
            with self.assertRaises(asyncio.CancelledError if cancel else TimeoutError):
                await task
            self.assertTrue(future.cancelled())
        self.assertEqual(self.published, [])

    def test_default_ros_facade_wires_changer_without_overriding_custom_adapter(self):
        with patch('app.navigation.ros2.floor_map_changer.FloorMapChanger') as factory:
            navigation = ROS2Navigation(node=self.node, nav2_client=MagicMock(),
                                        docking_client=MagicMock(), odometry=MagicMock(),
                                        floor_config_path=str(self.config))
            factory.assert_called_once_with(self.node, str(self.config), "robot3")
            self.assertEqual(navigation._floor_changer, factory.return_value.change_floor)

            factory.reset_mock()
            custom = AsyncMock(return_value=True)
            navigation = ROS2Navigation(node=self.node, nav2_client=MagicMock(),
                                        docking_client=MagicMock(), odometry=MagicMock(),
                                        floor_changer=custom)
            factory.assert_not_called()
            self.assertIs(navigation._floor_changer, custom)

    async def test_pose_stream_that_stops_cannot_establish_readiness(self):
        sent = False

        def publish_once(message):
            nonlocal sent
            if not sent:
                self.changer._on_pose(self.pose())
                sent = True

        self.changer._publisher.publish.side_effect = publish_once
        with self.assertRaisesRegex(TimeoutError, "AMCL"):
            await self.changer.change_floor("Elevator_01", 2)
