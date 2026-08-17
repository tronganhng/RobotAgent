import asyncio
import websockets

SERVER_URL = "ws://localhost:5055/ws"


async def main():
    print(f"Connecting to {SERVER_URL}...")

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("Connected to Fleet Backend.")

            # Giữ connection
            await websocket.wait_closed()

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())