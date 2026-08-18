import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Optional
import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger("RobotAgent")


class WebSocketClient:
    """Manages raw WebSocket connection and transport lifecycle."""

    def __init__(self, server_url: str) -> None:
        self.server_url: str = server_url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and not self.ws.closed

    async def connect(self):
        """Returns the websockets connect context manager."""
        return websockets.connect(self.server_url)

    async def send_json(self, message: dict) -> None:
        """Serializes and sends a dictionary as a JSON message."""
        if self.ws is None:
            raise RuntimeError("WebSocket connection is not established.")

        raw_payload = json.dumps(message)
        await self.ws.send(raw_payload)
        logger.info(f"Sent [{message.get('Type')}] (RequestId: {message.get('RequestId')}): {raw_payload}")

    async def receive_messages(self) -> AsyncGenerator[str, None]:
        """Asynchronously yields raw messages from the connection."""
        if not self.ws:
            return

        async for raw_msg in self.ws:
            yield str(raw_msg)
