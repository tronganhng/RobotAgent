import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from app.handlers.message_handler import parse_move_pose
from app.navigation.mock_navigation import MockNavigation
from app.robot.robot_agent import RobotAgent


class TestMoveYaw(unittest.IsolatedAsyncioTestCase):
    async def test_backend_cabin_payload_reaches_navigation_before_arrival(self):
        navigation = MockNavigation()
        navigation.cancel = AsyncMock()
        navigation.navigate_to = AsyncMock(return_value=True)
        agent = RobotAgent(navigation=navigation)
        agent.robot_id = "Robot_01"
        agent.ws = MagicMock(send=AsyncMock())
        for payload, expected in (
            ([-3.2704083, 4.136275, -1.6755782], (-3.2704083, 4.136275, -1.6755782)),
            ({"X": 3, "Y": 4, "Yaw": -1.6}, (3., 4., -1.6)),
            ({"x": 3, "y": 4, "yaw": 0}, (3., 4., 0.)),
            ([3, 4], (3., 4., 0.)),
            ({"x": 3, "y": 4}, (3., 4., 0.)),
        ):
            with self.subTest(payload=payload):
                navigation.navigate_to.reset_mock()
                agent.ws.send.reset_mock()
                await agent.handle_message(json.dumps({"Type": "MoveRobot", "Payload": payload}))
                await agent._current_move_task
                navigation.navigate_to.assert_awaited_once_with(*expected)
                self.assertEqual(json.loads(agent.ws.send.call_args.args[0])["Type"], "RobotArrived")

    async def test_invalid_yaw_does_not_cancel_or_start_motion(self):
        navigation = MockNavigation()
        navigation.cancel = AsyncMock()
        navigation.navigate_to = AsyncMock()
        agent = RobotAgent(navigation=navigation)
        for yaw in (None, True, "invalid", float('nan'), float('inf')):
            await agent.handle_message(json.dumps({"Type": "MoveRobot", "Payload": [3, 4, yaw]}))
        navigation.cancel.assert_not_awaited()
        navigation.navigate_to.assert_not_awaited()

    def test_invalid_pose_coordinates_are_rejected(self):
        for payload in ([None, 1, 0], [float('inf'), 1, 0], {"X": 1}, []):
            self.assertIsNone(parse_move_pose(payload))
