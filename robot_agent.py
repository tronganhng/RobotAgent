import asyncio
import sys
import json
import uuid
import enum
import datetime
import contextlib
import websockets
from websockets.exceptions import ConnectionClosed

SERVER_URL = "ws://localhost:5055/ws"


async def main():
    print(f"Connecting to {SERVER_URL}...")

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("Connected to Fleet Backend.")
            # Build and send initial robot state message as requested
            class RobotStatus(enum.Enum):
                Idle = "Idle"
                Moving = "Moving"
                Charging = "Charging"
                Error = "Error"

            def build_robot_state(robot_id: str = "") -> dict:
                return {
                    "RobotId": robot_id,
                    "X": 0.0,
                    "Y": 0.0,
                    "Rotation": 0.0,
                    "Battery": 100.0,
                    "Status": RobotStatus.Idle.value,
                    "CurrentTaskId": None,
                    "LastHeartbeat": datetime.datetime.utcnow().isoformat() + "Z",
                }

            async def listen_messages(ws: websockets.WebSocketClientProtocol):
                try:
                    while True:
                        msg = await ws.recv()
                        try:
                            data = json.loads(msg)
                        except Exception:
                            # ignore non-json messages
                            continue

                        payload = data.get("Payload") if isinstance(data, dict) else None
                        if isinstance(payload, dict):
                            robot_id = payload.get("RobotId")
                            if robot_id is not None:
                                print(f"Received RobotId from backend: {robot_id}")
                except ConnectionClosed:
                    return
                except Exception as e:
                    print(f"Listener error: {e}")

            message = {
                "Type": 3,
                "RequestId": str(uuid.uuid4()),
                "RobotId": None,
                "Payload": build_robot_state(),
            }

            try:
                await websocket.send(json.dumps(message))
                print("Sent robot state message:", json.dumps(message))
            except Exception as e:
                print(f"Failed to send robot state: {e}")

            # Start listener task to print RobotId from incoming Payload
            listener = asyncio.create_task(listen_messages(websocket))
            try:
                # Keep connection open until closed by backend or interrupted
                await websocket.wait_closed()
                print("Connection closed by Fleet Backend.")
            except asyncio.CancelledError:
                print("\nDisconnecting from Fleet Backend...")
                await websocket.close()
                print("Disconnected cleanly.")
            finally:
                listener.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await listener
    except ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except (ConnectionRefusedError, OSError) as e:
        print(f"Connection failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nRobot Agent stopped by user.")
        sys.exit(0)