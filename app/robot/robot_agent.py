import asyncio
import contextlib
import enum
import json
import logging
from typing import Any, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from app.config import DEFAULT_SERVER_URL, logger
from app.communication.message_protocol import SocketMessageType, format_message
from app.robot.robot_state import build_initial_robot_state
from app.handlers.message_handler import extract_robot_id


class RobotAgent:
    """
    Robot Agent client that interfaces between Fleet Backend and robot hardware/simulation.

    Registration flow:
    1. Connect to Fleet Backend WebSocket endpoint.
    2. Send 'RegisterRobot' request with initial robot state.
    3. Receive assigned 'RobotId' from server.
    4. Send 'RegisterClient' message with ClientType = 'Robot' and assigned RobotId.
    """

    def __init__(self, server_url: str = DEFAULT_SERVER_URL) -> None:
        self.server_url: str = server_url
        self.robot_id: Optional[str] = None
        self.is_client_registered: bool = False
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._registration_event: asyncio.Event = asyncio.Event()

    async def send_message(
        self,
        message_type: SocketMessageType,
        payload: Optional[Any] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Constructs and sends a standardized JSON message over the WebSocket connection."""
        if self.ws is None:
            raise RuntimeError("WebSocket connection is not established.")

        message = format_message(
            message_type=message_type,
            payload=payload,
            robot_id=self.robot_id,
            request_id=request_id,
        )

        raw_payload = json.dumps(message)
        await self.ws.send(raw_payload)
        logger.info(f"Sent [{message_type}] (RequestId: {message['RequestId']}): {raw_payload}")

    async def register_robot(self) -> None:
        """Step 1: Send RegisterRobot request with the initial state to the Backend."""
        logger.info("Step 1/3: Sending RegisterRobot request...")
        initial_state = build_initial_robot_state(robot_id=self.robot_id or "")
        await self.send_message(
            message_type=SocketMessageType.RegisterRobot,
            payload=initial_state,
        )

    async def register_client(self, robot_id: str) -> None:
        """Step 3: Send RegisterClient message with Payload: 'Robot'."""
        logger.info(f"Step 3/3: Sending RegisterClient message for RobotId: '{robot_id}'...")
        await self.send_message(
            message_type=SocketMessageType.RegisterClient,
            payload="Robot",
        )
        self.is_client_registered = True
        logger.info(f"Successfully sent RegisterClient (Payload: 'Robot', RobotId: {robot_id}).")

    def _extract_robot_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extracts RobotId from data or payload with case-insensitivity."""
        return extract_robot_id(data)

    async def handle_message(self, raw_msg: str) -> None:
        """Parses and handles incoming JSON messages from the Fleet Backend."""
        try:
            data = json.loads(raw_msg)
        except Exception:
            logger.warning(f"Ignored non-JSON incoming message: {raw_msg}")
            return

        if not isinstance(data, dict):
            return

        msg_type = data.get("Type") or data.get("type") or "Unknown"
        logger.info(f"Received message [{msg_type}]: {raw_msg}")

        # Check for RobotId assignment if not yet received
        if not self.robot_id:
            extracted_id = self._extract_robot_id(data)
            if extracted_id:
                self.robot_id = extracted_id
                self._registration_event.set()
                logger.info(f"Step 2/3: Received assigned RobotId: '{self.robot_id}' from backend.")

                # Automatically trigger Step 3: RegisterClient with ClientType = Robot
                await self.register_client(self.robot_id)

    async def listen(self) -> None:
        """Listens for incoming messages until connection closes."""
        if not self.ws:
            return

        try:
            async for raw_msg in self.ws:
                await self.handle_message(str(raw_msg))
        except ConnectionClosed as e:
            logger.info(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error during message receiving: {e}", exc_info=True)

    async def run(self) -> None:
        """Main lifecycle loop of the Robot Agent."""
        logger.info(f"Connecting to Fleet Backend at {self.server_url}...")

        try:
            async with websockets.connect(self.server_url) as websocket:
                self.ws = websocket
                logger.info("Connected to Fleet Backend.")

                # Step 1: Send RegisterRobot
                await self.register_robot()

                # Start listener task
                listener_task = asyncio.create_task(self.listen())

                try:
                    await websocket.wait_closed()
                    logger.info("Connection closed by Fleet Backend.")
                except asyncio.CancelledError:
                    logger.info("Shutdown requested. Closing connection...")
                    await websocket.close()
                    logger.info("Disconnected cleanly.")
                finally:
                    listener_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await listener_task

        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"Connection failed: {e}")
        except ConnectionClosed as e:
            logger.warning(f"Connection closed unexpectedly: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self.ws = None
