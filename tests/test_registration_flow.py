import asyncio
import json
import unittest
import websockets
from robot_agent import RobotAgent


class TestRegistrationFlow(unittest.IsolatedAsyncioTestCase):
    async def test_full_registration_flow_pascal_case(self):
        received_messages = []
        assigned_robot_id = "Robot_TB4_007"
        server_port = 8765
        server_url = f"ws://127.0.0.1:{server_port}"

        # Mock Fleet Backend handler
        async def mock_server_handler(websocket):
            try:
                async for raw_msg in websocket:
                    msg = json.loads(raw_msg)
                    received_messages.append(msg)

                    msg_type = msg.get("Type")
                    if msg_type == "RegisterRobot":
                        # Server responds with assigned RobotId in PascalCase
                        response = {
                            "Type": "RegisterRobotResponse",
                            "RequestId": msg.get("RequestId"),
                            "RobotId": assigned_robot_id,
                            "Payload": {
                                "RobotId": assigned_robot_id,
                                "Success": True,
                            },
                        }
                        await websocket.send(json.dumps(response))

                    elif msg_type == "RegisterClient":
                        await asyncio.sleep(0.05)
                        break
            except websockets.exceptions.ConnectionClosed:
                pass

        # Start mock server
        server = await websockets.serve(mock_server_handler, "127.0.0.1", server_port)

        agent = RobotAgent(server_url=server_url)
        agent_task = asyncio.create_task(agent.run())

        try:
            await asyncio.wait_for(agent._registration_event.wait(), timeout=3.0)
            await asyncio.sleep(0.1)
        finally:
            agent_task.cancel()
            server.close()
            await server.wait_closed()

        self.assertEqual(len(received_messages), 2)
        # Check RegisterRobot
        self.assertEqual(received_messages[0]["Type"], "RegisterRobot")
        self.assertEqual(received_messages[0]["Payload"]["Status"], "Idle")
        # Check RobotId assigned
        self.assertEqual(agent.robot_id, assigned_robot_id)
        # Check RegisterClient
        self.assertEqual(received_messages[1]["Type"], "RegisterClient")
        self.assertEqual(received_messages[1]["RobotId"], assigned_robot_id)
        self.assertEqual(received_messages[1]["Payload"], "Robot")
        self.assertTrue(agent.is_client_registered)

    async def test_registration_flow_camel_case_response(self):
        received_messages = []
        assigned_robot_id = "Robot_TB4_999"
        server_port = 8766
        server_url = f"ws://127.0.0.1:{server_port}"

        # Mock Fleet Backend handler returning camelCase
        async def mock_server_handler(websocket):
            try:
                async for raw_msg in websocket:
                    msg = json.loads(raw_msg)
                    received_messages.append(msg)

                    msg_type = msg.get("Type") or msg.get("type")
                    if msg_type == "RegisterRobot":
                        response = {
                            "type": "RegisterRobotResponse",
                            "requestId": msg.get("RequestId"),
                            "robotId": assigned_robot_id,
                            "payload": {
                                "robotId": assigned_robot_id,
                                "success": True,
                            },
                        }
                        await websocket.send(json.dumps(response))

                    elif msg_type == "RegisterClient":
                        await asyncio.sleep(0.05)
                        break
            except websockets.exceptions.ConnectionClosed:
                pass

        server = await websockets.serve(mock_server_handler, "127.0.0.1", server_port)

        agent = RobotAgent(server_url=server_url)
        agent_task = asyncio.create_task(agent.run())

        try:
            await asyncio.wait_for(agent._registration_event.wait(), timeout=3.0)
            await asyncio.sleep(0.1)
        finally:
            agent_task.cancel()
            server.close()
            await server.wait_closed()

        self.assertEqual(len(received_messages), 2)
        self.assertEqual(agent.robot_id, assigned_robot_id)
        self.assertEqual(received_messages[1]["Type"], "RegisterClient")
        self.assertEqual(received_messages[1]["RobotId"], assigned_robot_id)
        self.assertEqual(received_messages[1]["Payload"], "Robot")
        self.assertTrue(agent.is_client_registered)


if __name__ == "__main__":
    unittest.main()
