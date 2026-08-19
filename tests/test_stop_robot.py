import asyncio
import json
import unittest
import websockets
from app.communication.message_protocol import SocketMessageType
from app.robot.robot_agent import RobotAgent
from app.navigation.mock_navigation import MockNavigation


class TestStopRobotFlow(unittest.IsolatedAsyncioTestCase):
    async def test_stop_robot_cancels_ongoing_move(self):
        received_messages = []
        assigned_robot_id = "Robot_TB4_STOP_01"
        server_port = 8780
        server_url = f"ws://127.0.0.1:{server_port}"
        stop_sent = asyncio.Event()

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
                        # Send MoveRobot
                        move_cmd = {
                            "Type": "MoveRobot",
                            "RequestId": None,
                            "RobotId": assigned_robot_id,
                            "Payload": [50.0, 50.0],
                        }
                        await websocket.send(json.dumps(move_cmd))

                        # Wait briefly while robot starts moving, then send StopRobot
                        await asyncio.sleep(0.2)
                        stop_cmd = {
                            "Type": "StopRobot",
                            "RequestId": None,
                            "RobotId": assigned_robot_id,
                            "Payload": {},
                        }
                        await websocket.send(json.dumps(stop_cmd))
                        stop_sent.set()

            except websockets.exceptions.ConnectionClosed:
                pass

        server = await websockets.serve(mock_server_handler, "127.0.0.1", server_port)

        nav = MockNavigation()
        agent = RobotAgent(server_url=server_url, navigation=nav)
        agent_task = asyncio.create_task(agent.run())

        try:
            await asyncio.wait_for(stop_sent.wait(), timeout=3.0)
            # Wait past the normal navigation time (1.0s) to ensure RobotArrived is not sent
            await asyncio.sleep(1.2)
        finally:
            agent_task.cancel()
            server.close()
            await server.wait_closed()

        # Check that RobotArrived was NOT sent because navigation was cancelled
        msg_types = [m.get("Type") for m in received_messages]
        self.assertIn("RegisterRobot", msg_types)
        self.assertIn("RegisterClient", msg_types)
        self.assertNotIn("RobotArrived", msg_types)

    async def test_stop_robot_when_idle(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)
        # Calling stop directly when idle should not throw any error
        await agent.stop()
        self.assertIsNone(agent._current_move_task)

    async def test_handle_message_stop_robot(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)

        # Start a move task
        agent._current_move_task = asyncio.create_task(asyncio.sleep(5.0))
        self.assertFalse(agent._current_move_task.done())

        # Send StopRobot message (PascalCase)
        raw_msg = json.dumps({"Type": "StopRobot", "RobotId": "Robot_01", "Payload": {}})
        await agent.handle_message(raw_msg)

        self.assertIsNone(agent._current_move_task)

    async def test_handle_message_stop_robot_camel_case(self):
        nav = MockNavigation()
        agent = RobotAgent(navigation=nav)

        # Start a move task
        agent._current_move_task = asyncio.create_task(asyncio.sleep(5.0))
        self.assertFalse(agent._current_move_task.done())

        # Send StopRobot message (camelCase)
        raw_msg = json.dumps({"type": "StopRobot", "robotId": "Robot_01", "payload": {}})
        await agent.handle_message(raw_msg)

        self.assertIsNone(agent._current_move_task)


if __name__ == "__main__":
    unittest.main()
