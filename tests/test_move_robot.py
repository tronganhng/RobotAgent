import asyncio
import json
import unittest
import websockets
from app.robot.robot_agent import RobotAgent
from app.navigation.mock_navigation import MockNavigation


class TestMoveRobotFlow(unittest.IsolatedAsyncioTestCase):
    async def test_move_robot_with_array_payload(self):
        received_messages = []
        assigned_robot_id = "Robot_01"
        server_port = 8770
        server_url = f"ws://127.0.0.1:{server_port}"
        move_sent = asyncio.Event()

        # Mock Fleet Backend
        async def mock_server_handler(websocket):
            try:
                async for raw_msg in websocket:
                    msg = json.loads(raw_msg)
                    received_messages.append(msg)
                    msg_type = msg.get("Type")

                    if msg_type == "RegisterRobot":
                        # Send registration response
                        response = {
                            "Type": "RegisterRobotResponse",
                            "RequestId": msg.get("RequestId"),
                            "RobotId": assigned_robot_id,
                            "Payload": {"RobotId": assigned_robot_id},
                        }
                        await websocket.send(json.dumps(response))

                    elif msg_type == "RegisterClient":
                        # Backend sends MoveRobot message as described by user
                        await asyncio.sleep(0.05)
                        move_cmd = {
                            "Type": "MoveRobot",
                            "RequestId": None,
                            "RobotId": assigned_robot_id,
                            "Payload": [13.29, 20.33],
                        }
                        await websocket.send(json.dumps(move_cmd))
                        move_sent.set()

                    elif msg_type == "RobotArrived":
                        # Received arrival confirmation
                        await asyncio.sleep(0.05)
                        break

            except websockets.exceptions.ConnectionClosed:
                pass

        server = await websockets.serve(mock_server_handler, "127.0.0.1", server_port)

        nav = MockNavigation()
        agent = RobotAgent(server_url=server_url, navigation=nav)
        agent_task = asyncio.create_task(agent.run())

        try:
            # Wait for registration and move command
            await asyncio.wait_for(move_sent.wait(), timeout=3.0)
            # Wait for mock navigation to finish (MockNavigation takes 1.0s)
            await asyncio.sleep(1.5)
        finally:
            agent_task.cancel()
            server.close()
            await server.wait_closed()

        # Verify robot arrived at (13.29, 20.33)
        self.assertEqual(nav.get_current_pose()[:2], (13.29, 20.33))

        # Verify messages sequence: RegisterRobot, RegisterClient, RobotArrived
        msg_types = [m.get("Type") for m in received_messages]
        self.assertIn("RegisterRobot", msg_types)
        self.assertIn("RegisterClient", msg_types)
        self.assertIn("RobotArrived", msg_types)

        # Check RobotArrived payload
        arrived_msg = next(m for m in received_messages if m.get("Type") == "RobotArrived")
        self.assertEqual(arrived_msg["Payload"]["X"], 13.29)
        self.assertEqual(arrived_msg["Payload"]["Y"], 20.33)


if __name__ == "__main__":
    unittest.main()
