import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.navigation.mock_navigation import MockNavigation
from app.navigation.ros2_navigation import ROS2Navigation
from app.robot.robot_agent import RobotAgent


class TestChangeRobotFloor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.navigation = MockNavigation()
        self.navigation.cancel = AsyncMock()
        self.agent = RobotAgent(navigation=self.navigation)
        self.agent.robot_id = "Robot_01"
        self.agent.ws = MagicMock()
        self.agent.ws.send = AsyncMock()
        self.message = {
            "Type": "ChangeRobotFloor", "RequestId": "floor-operation-1",
            "RobotId": "Robot_01",
            "Payload": {"ElevatorId": "Elevator_01", "TargetFloor": 2},
        }

    async def handle(self):
        await self.agent.handle_message(json.dumps(self.message))

    def reply(self):
        return json.loads(self.agent.ws.send.call_args.args[0])

    async def test_success_echoes_backend_correlation_after_motion_cancel(self):
        cancelled = asyncio.Event()

        async def moving():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.agent._current_move_task = asyncio.create_task(moving())
        await asyncio.sleep(0)
        await self.handle()
        self.assertTrue(cancelled.is_set())
        self.navigation.cancel.assert_awaited_once()
        self.assertEqual(self.navigation.floor, 2)
        self.assertEqual(self.agent.robot_state["Floor"], 2)
        self.assertEqual(self.reply(), {
            "Type": "RobotFloorReady", "RequestId": "floor-operation-1",
            "RobotId": "Robot_01",
            "Payload": {"ElevatorId": "Elevator_01", "TargetFloor": 2,
                        "IsReady": True, "ErrorMessage": None},
        })

    async def test_camel_case_and_floor_zero(self):
        self.message = {"type": "ChangeRobotFloor", "requestId": "request-0",
                        "robotId": "Robot_01",
                        "payload": {"elevatorId": "Elevator_01", "targetFloor": 0}}
        await self.handle()
        self.assertEqual(self.reply()["RequestId"], "request-0")
        self.assertEqual(self.agent.robot_state["Floor"], 0)

    async def test_failure_does_not_change_floor(self):
        for result in (False, RuntimeError("Localization failed")):
            with self.subTest(result=result):
                self.agent.robot_state["Floor"] = 1
                self.navigation.change_floor = AsyncMock(return_value=result)
                if isinstance(result, Exception):
                    self.navigation.change_floor.side_effect = result
                await self.handle()
                self.assertFalse(self.reply()["Payload"]["IsReady"])
                self.assertTrue(self.reply()["Payload"]["ErrorMessage"])
                self.assertEqual(self.agent.robot_state["Floor"], 1)
                self.assertEqual(self.agent.robot_state["Status"], "Error")

    async def test_timeout_reports_failure(self):
        async def stuck(*args):
            await asyncio.Event().wait()
        self.navigation.change_floor = stuck
        self.agent._floor_change_timeout = 0.01
        await self.handle()
        self.assertFalse(self.reply()["Payload"]["IsReady"])
        self.assertIn("timed out", self.reply()["Payload"]["ErrorMessage"])

    async def test_invalid_commands_do_not_switch_maps(self):
        original = self.message.copy()
        self.navigation.change_floor = AsyncMock()
        for changes in ({"RobotId": "OtherRobot"}, {"RequestId": None},
                        {"Payload": []}, {"Payload": {"ElevatorId": "E", "TargetFloor": True}},
                        {"Payload": {"ElevatorId": "", "TargetFloor": 2}}):
            self.message = dict(original, **changes)
            await self.handle()
        self.navigation.change_floor.assert_not_awaited()
        self.agent.ws.send.assert_not_awaited()

    async def test_ros2_without_floor_adapter_reports_not_ready(self):
        self.agent.navigation = ROS2Navigation(
            nav2_client=MagicMock(cancel=AsyncMock()),
            docking_client=MagicMock(cancel=AsyncMock()), odometry=MagicMock())
        await self.handle()
        self.assertFalse(self.reply()["Payload"]["IsReady"])
        self.assertIn("not configured", self.reply()["Payload"]["ErrorMessage"])

    async def test_ros2_delegates_to_floor_adapter(self):
        changer = AsyncMock(return_value=True)
        navigation = ROS2Navigation(nav2_client=MagicMock(), docking_client=MagicMock(),
                                    odometry=MagicMock(), floor_changer=changer)
        self.assertTrue(await navigation.change_floor("Elevator_01", 3))
        changer.assert_awaited_once_with("Elevator_01", 3)
