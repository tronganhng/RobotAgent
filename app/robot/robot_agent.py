import asyncio
import contextlib
import enum
import datetime
import json
import logging
from typing import Any, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from app.config import DEFAULT_SERVER_URL, logger
from app.communication.message_protocol import SocketMessageType, format_message
from app.robot.robot_state import build_initial_robot_state, RobotStatus
from app.handlers.message_handler import extract_robot_id, parse_move_coordinates
from app.navigation.navigation_interface import NavigationInterface
from app.navigation.mock_navigation import MockNavigation


class RobotAgent:
    """
    Robot Agent client that interfaces between Fleet Backend and robot hardware/simulation.

    Registration flow:
    1. Connect to Fleet Backend WebSocket endpoint.
    2. Send 'RegisterRobot' request with initial robot state.
    3. Receive assigned 'RobotId' from server.
    4. Send 'RegisterClient' message with ClientType = 'Robot' and assigned RobotId.
    """

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        navigation: Optional[NavigationInterface] = None,
    ) -> None:
        self.server_url: str = server_url
        self.navigation: NavigationInterface = navigation or MockNavigation()
        self.robot_id: Optional[str] = None
        self.is_client_registered: bool = False
        self.ws: Optional[Any] = None
        self._registration_event: asyncio.Event = asyncio.Event()
        self._current_move_task: Optional[asyncio.Task] = None
        self._state_publisher_task: Optional[asyncio.Task] = None
        self.robot_state: Dict[str, Any] = build_initial_robot_state()

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
        # logger.info(f"Sent [{message_type}] (RequestId: {message['RequestId']}): {raw_payload}")

    async def register_robot(self) -> None:
        logger.info("RegisterRobot request")
        self.robot_state["RobotId"] = self.robot_id or ""
        await self.send_message(
            message_type=SocketMessageType.RegisterRobot,
            payload=self.robot_state,
        )

    async def register_client(self) -> None:
        logger.info(f"RegisterClient")
        await self.send_message(
            message_type=SocketMessageType.RegisterClient,
            payload="Robot",
        )
        self.is_client_registered = True

    def _extract_robot_id(self, data: Dict[str, Any]) -> Optional[str]:
        """Extracts RobotId from data or payload with case-insensitivity."""
        return extract_robot_id(data)

    async def stop(self) -> None:
        """Stops any active navigation task and commands navigation interface to cancel."""
        logger.info("Stopping robot navigation...")
        if self._current_move_task and not self._current_move_task.done():
            self._current_move_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._current_move_task
            self._current_move_task = None
        await self.navigation.cancel()
        self.robot_state["Status"] = RobotStatus.Idle.value
        logger.info("Robot stopped successfully.")

    async def _execute_move(self, x: float, y: float) -> None:
        """Executes navigation to (x, y) asynchronously."""
        try:
            self.robot_state["Status"] = RobotStatus.DoingTask.value
            success = await self.navigation.navigate_to(x, y)
            if success:
                logger.info(f"Robot successfully arrived at ({x}, {y}).")
                self.robot_state["Status"] = RobotStatus.Idle.value
                # Send arrival notification to Backend if connected
                if self.ws:
                    with contextlib.suppress(Exception):
                        await self.send_message(
                            message_type=SocketMessageType.RobotArrived,
                            payload=True,
                        )
        except asyncio.CancelledError:
            logger.info(f"Navigation to ({x}, {y}) was cancelled.")
        except Exception as e:
            logger.error(f"Error during navigation to ({x}, {y}): {e}", exc_info=True)
        finally:
            if self.robot_state["Status"] == RobotStatus.DoingTask.value:
                self.robot_state["Status"] = RobotStatus.Idle.value

    async def _execute_charge(self) -> None:
        """Executes charging sequence asynchronously."""
        try:
            self.robot_state["Status"] = RobotStatus.DoingTask.value
            success = await self.navigation.go_charge()
            if success:
                logger.info("Robot successfully docked and started charging.")
                self.robot_state["Status"] = RobotStatus.Charging.value
            else:
                self.robot_state["Status"] = RobotStatus.Idle.value
        except asyncio.CancelledError:
            logger.info("Charging sequence was cancelled.")
        except Exception as e:
            logger.error(f"Error during charging sequence: {e}", exc_info=True)
            self.robot_state["Status"] = RobotStatus.Error.value
        finally:
            if self.robot_state["Status"] == RobotStatus.DoingTask.value:
                self.robot_state["Status"] = RobotStatus.Idle.value

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

        # Check for RobotId assignment if not yet received (during registration flow)
        if msg_type in (SocketMessageType.ServerResponse.value, "ServerResponse"):
            extracted_id = self._extract_robot_id(data)
            if extracted_id:
                self.robot_id = extracted_id
                self.robot_state["RobotId"] = self.robot_id
                self._registration_event.set()
                logger.info(f"Received assigned RobotId: '{self.robot_id}'")

                # Automatically trigger Step 3: RegisterClient with ClientType = Robot
                # if self.ws:
                #     await self.register_client(self.robot_id)

        # Handle MoveRobot command
        if msg_type in (SocketMessageType.MoveRobot.value, "MoveRobot"):
            payload = data.get("Payload") if "Payload" in data else data.get("payload")
            coords = parse_move_coordinates(payload)
            if coords is not None:
                x, y = coords
                logger.info(f"Received MoveRobot command -> target: ({x}, {y}). Starting navigation...")
                # Cancel existing movement task if running
                if self._current_move_task and not self._current_move_task.done():
                    self._current_move_task.cancel()
                self._current_move_task = asyncio.create_task(self._execute_move(x, y))
            else:
                logger.warning(f"Unable to parse MoveRobot coordinates from payload: {payload}")

        # Handle ChargeRobot command
        elif msg_type in (SocketMessageType.ChargeRobot.value, "ChargeRobot"):
            logger.info("Received ChargeRobot command from backend. Starting charging sequence...")
            # Cancel existing task if running
            if self._current_move_task and not self._current_move_task.done():
                self._current_move_task.cancel()
            self._current_move_task = asyncio.create_task(self._execute_charge())

        # Handle StopRobot command
        elif msg_type in (SocketMessageType.StopRobot.value, "StopRobot"):
            logger.info("StopRobot")
            await self.stop()
            
        elif msg_type in (SocketMessageType.SetSystemMode.value, "SetSystemMode"):
            await self.register_robot()

    async def publish_state(self) -> None:
        """Continuously publishes the robot state to the backend."""
        while True:
            await self._registration_event.wait()
            
            if self.ws and self.is_client_registered:
                try:
                    # Update pose from navigation
                    x, y, rotation = self.navigation.get_current_pose()
                    self.robot_state["X"] = x
                    self.robot_state["Y"] = y
                    self.robot_state["Rotation"] = rotation
                    self.robot_state["LastHeartbeat"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    
                    await self.send_message(
                        message_type=SocketMessageType.RobotState,
                        payload=self.robot_state,
                    )
                except Exception as e:
                    logger.error(f"Error publishing robot state: {e}")
            
            await asyncio.sleep(0.5)

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

                await self.register_client()

                # Start listener task and state publisher task
                listener_task = asyncio.create_task(self.listen())
                self._state_publisher_task = asyncio.create_task(self.publish_state())

                try:
                    await websocket.wait_closed()
                    logger.info("Connection closed by Fleet Backend.")
                except asyncio.CancelledError:
                    logger.info("Shutdown requested. Closing connection...")
                    await websocket.close()
                    logger.info("Disconnected cleanly.")
                finally:
                    listener_task.cancel()
                    if self._state_publisher_task:
                        self._state_publisher_task.cancel()
                    if self._current_move_task and not self._current_move_task.done():
                        self._current_move_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await listener_task
                    if self._state_publisher_task:
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._state_publisher_task

        except (ConnectionRefusedError, OSError) as e:
            logger.error(f"Connection failed: {e}")
        except ConnectionClosed as e:
            logger.warning(f"Connection closed unexpectedly: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self.ws = None
