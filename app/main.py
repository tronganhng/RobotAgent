import asyncio
import sys

from app.config import DEFAULT_SERVER_URL, logger
from app.robot.robot_agent import RobotAgent


async def main() -> None:
    server_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER_URL

    try:
        import rclpy
        from rclpy.node import Node
    except ImportError:
        logger.info("ROS2 runtime not available; using mock navigation.")
        agent = RobotAgent(server_url=server_url)
        await agent.run()
        return

    if not rclpy.ok():
        rclpy.init()

    node = Node("robot_agent")
    try:
        agent = RobotAgent(server_url=server_url, node=node)
        await agent.run()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Robot Agent stopped by user.")
        sys.exit(0)
