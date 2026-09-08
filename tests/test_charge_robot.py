import asyncio
import json
import unittest
import websockets
from app.robot.robot_agent import RobotAgent
from app.robot.robot_state import RobotStatus
from app.navigation.mock_navigation import MockNavigation


class TestChargeRobotFlow(unittest.IsolatedAsyncioTestCase):
    async def test_charge_robot_flow(self):
        received_messages = []
        assigned_robot_id = "Robot_TB4_CHARGE_01"
        server_port = 8790
        server_url = f"ws://127.0.0.1:{server_port}"
        charge_sent = asyncio.Event()

        # Mock Fleet Backend
        async def mock_server_handler(websocket):
            try:
                async for raw_msg in websocket:
                    msg = json.loads(raw_msg)
                    received_messages.append(msg)
                    msg_type = msg.get("Type")

                    if msg_type == "RegisterRobot":
                        response = {
                            "Type": "RegisterRobotResponse",
                            "RequestId": msg.get("RequestId"),
                            "RobotId": assigned_robot_id,
                            "Payload": {"RobotId": assigned_robot_id},
                        }
                        await websocket.send(json.dumps(response))

                    elif msg_type == "RegisterClient":
                        # Backend sends ChargeRobot message
                        await asyncio.sleep(0.05)
                        charge_cmd = {
                            "Type": "ChargeRobot",
                            "RequestId": None,
                            "RobotId": assigned_robot_id,
                            "Payload": {},
                        }
                        await websocket.send(json.dumps(charge_cmd))
                        charge_sent.set()

            except websockets.exceptions.ConnectionClosed:
                pass

        server = await websockets.serve(mock_server_handler, "127.0.0.1", server_port)

        nav = MockNavigation()
        agent = RobotAgent(server_url=server_url, navigation=nav)
        agent_task = asyncio.create_task(agent.run())

        try:
            # Wait for registration and charge command
            await asyncio.wait_for(charge_sent.wait(), timeout=3.0)
            # Wait for mock charging navigation to finish (MockNavigation takes 1.0s)
            await asyncio.sleep(1.5)
        finally:
            agent_task.cancel()
            server.close()
            await server.wait_closed()

        # Verify robot status transitioned to Charging
        self.assertEqual(agent.robot_state["Status"], RobotStatus.Charging.value)

    async def test_handle_message_charge_robot_pascal_case(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)

        raw_msg = json.dumps({"Type": "ChargeRobot", "RobotId": "Robot_01", "Payload": {}})
        await agent.handle_message(raw_msg)
        await asyncio.sleep(0.01)

        self.assertIsNotNone(agent._current_move_task)
        self.assertEqual(agent.robot_state["Status"], RobotStatus.DoingTask.value)

        # Wait for task to complete
        await agent._current_move_task
        self.assertEqual(agent.robot_state["Status"], RobotStatus.Charging.value)

    async def test_handle_message_charge_robot_camel_case(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)

        raw_msg = json.dumps({"type": "ChargeRobot", "robotId": "Robot_01", "payload": {}})
        await agent.handle_message(raw_msg)
        await asyncio.sleep(0.01)

        self.assertIsNotNone(agent._current_move_task)
        self.assertEqual(agent.robot_state["Status"], RobotStatus.DoingTask.value)

        # Wait for task to complete
        await agent._current_move_task
        self.assertEqual(agent.robot_state["Status"], RobotStatus.Charging.value)

    async def test_charge_robot_cancelled_by_stop(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)

        # Start charge task
        raw_charge = json.dumps({"Type": "ChargeRobot", "RobotId": "Robot_01", "Payload": {}})
        await agent.handle_message(raw_charge)
        self.assertIsNotNone(agent._current_move_task)
        self.assertFalse(agent._current_move_task.done())

        # Send StopRobot to cancel charging navigation
        raw_stop = json.dumps({"Type": "StopRobot", "RobotId": "Robot_01", "Payload": {}})
        await agent.handle_message(raw_stop)

        self.assertIsNone(agent._current_move_task)
        self.assertEqual(agent.robot_state["Status"], RobotStatus.Idle.value)


if __name__ == "__main__":
    unittest.main()
