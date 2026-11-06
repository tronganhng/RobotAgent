import argparse
import asyncio
import sys
import threading

from app.config import DEFAULT_SERVER_URL, logger
from app.robot.robot_agent import RobotAgent
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Connect a robot to the Fleet Backend.")
    parser.add_argument("server_url", nargs="?", default=DEFAULT_SERVER_URL)
    parser.add_argument("--robot-namespace", default=DEFAULT_ROBOT_NAMESPACE,
                        help="ROS robot namespace (default: %(default)s)")
    args = parser.parse_args(argv)
    try:
        args.robot_namespace = RobotTopics(args.robot_namespace).namespace
    except ValueError as exc:
        parser.error(str(exc))
    return args


async def main() -> None:
    args = parse_args()
    server_url = args.server_url
    logger.info("Robot namespace: %s", args.robot_namespace)

    try:
        import rclpy
        from rclpy.executors import SingleThreadedExecutor
        from rclpy.node import Node
    except ImportError:
        logger.info("ROS2 runtime not available; using mock navigation.")
        agent = RobotAgent(server_url=server_url, robot_namespace=args.robot_namespace)
        await agent.run()
        return

    if not rclpy.ok():
        rclpy.init(args=[])

    node = Node("robot_agent")
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    executor_thread = threading.Thread(target=executor.spin, daemon=True)
    try:
        executor_thread.start()
        agent = RobotAgent(server_url=server_url, node=node,
                           robot_namespace=args.robot_namespace)
        await agent.run()
    finally:
        executor.shutdown()
        executor_thread.join()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Robot Agent stopped by user.")
        sys.exit(0)
