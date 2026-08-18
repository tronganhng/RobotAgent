"""
Robot Agent - Backward compatibility wrapper & root entrypoint.
All modular components are organized within the `app` package.
"""

import asyncio
import sys
from app.config import DEFAULT_SERVER_URL, logger
from app.communication.message_protocol import SocketMessageType
from app.robot.robot_state import RobotStatus, build_initial_robot_state
from app.robot.robot_agent import RobotAgent
from app.main import main

__all__ = [
    "DEFAULT_SERVER_URL",
    "SocketMessageType",
    "RobotStatus",
    "build_initial_robot_state",
    "RobotAgent",
    "logger",
    "main",
]

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Robot Agent stopped by user.")
        sys.exit(0)