import asyncio
import sys
from app.config import DEFAULT_SERVER_URL, logger
from app.robot.robot_agent import RobotAgent


async def main() -> None:
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL
    agent = RobotAgent(server_url=server_url)
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Robot Agent stopped by user.")
        sys.exit(0)
