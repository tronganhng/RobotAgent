import unittest
import asyncio
from app.communication.message_protocol import SocketMessageType, format_message
from app.robot.robot_state import RobotStatus, build_initial_robot_state
from app.handlers.message_handler import extract_robot_id
from app.navigation.mock_navigation import MockNavigation


class TestModularComponents(unittest.IsolatedAsyncioTestCase):
    def test_format_message(self):
        msg = format_message(
            message_type=SocketMessageType.RegisterRobot,
            payload={"test": 123},
            robot_id="Robot_01",
            request_id="custom-req-id",
        )
        self.assertEqual(msg["Type"], "RegisterRobot")
        self.assertEqual(msg["RequestId"], "custom-req-id")
        self.assertEqual(msg["RobotId"], "Robot_01")
        self.assertEqual(msg["Payload"], {"test": 123})

    def test_build_initial_robot_state(self):
        state = build_initial_robot_state("Robot_TB4_01")
        self.assertEqual(state["RobotId"], "Robot_TB4_01")
        self.assertEqual(state["X"], 0.0)
        self.assertEqual(state["Y"], 0.0)
        self.assertEqual(state["Rotation"], 0.0)
        self.assertEqual(state["Battery"], 100.0)
        self.assertEqual(state["Status"], RobotStatus.Idle.value)
        self.assertIsNone(state["CurrentTaskId"])
        self.assertIn("LastHeartbeat", state)

    def test_extract_robot_id_top_level(self):
        self.assertEqual(extract_robot_id({"RobotId": "R1"}), "R1")
        self.assertEqual(extract_robot_id({"robotId": "R2"}), "R2")
        self.assertEqual(extract_robot_id({"RobotID": "R3"}), "R3")

    def test_extract_robot_id_payload_dict(self):
        self.assertEqual(extract_robot_id({"Payload": {"RobotId": "R4"}}), "R4")
        self.assertEqual(extract_robot_id({"payload": {"robotId": "R5"}}), "R5")
        self.assertEqual(extract_robot_id({"Payload": {"Id": "R6"}}), "R6")
        self.assertIsNone(extract_robot_id({"Payload": "Robot"}))

    async def test_mock_navigation(self):
        nav = MockNavigation()
        self.assertEqual(nav.get_current_pose(), (0.0, 0.0, 0.0))
        success = await nav.navigate_to(5.0, 10.0, 1.57)
        self.assertTrue(success)
        self.assertEqual(nav.get_current_pose(), (5.0, 10.0, 1.57))

    async def test_mock_navigation_go_charge(self):
        nav = MockNavigation()
        success = await nav.go_charge()
        self.assertTrue(success)



if __name__ == "__main__":
    unittest.main()
