import asyncio
import sys
import websockets
from websockets.exceptions import ConnectionClosed

SERVER_URL = "ws://localhost:5055/ws"


async def main():
    print(f"Connecting to {SERVER_URL}...")

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("Connected to Fleet Backend.")
            try:
                # Keep connection open until closed by backend or interrupted
                await websocket.wait_closed()
                print("Connection closed by Fleet Backend.")
            except asyncio.CancelledError:
                print("\nDisconnecting from Fleet Backend...")
                await websocket.close()
                print("Disconnected cleanly.")
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