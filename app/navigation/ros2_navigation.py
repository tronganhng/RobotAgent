import logging
from typing import Tuple
from app.navigation.navigation_interface import NavigationInterface

logger = logging.getLogger("RobotAgent")


class ROS2Navigation(NavigationInterface):
    """
    ROS 2 / Nav2 implementation for deployment on TurtleBot 4 (Ubuntu / ROS 2 Jazzy/Humble).
    
    Note: To be implemented when deploying to TurtleBot 4 hardware with rclpy and nav2_simple_commander.
    """

    def __init__(self, node=None) -> None:
        self.node = node
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: float = 0.0

    async def navigate_to(self, x: float, y: float, rotation: float = 0.0) -> bool:
        logger.info(f"[ROS2Navigation] Sending goal to Nav2: ({x}, {y}, {rotation})")
        # TODO (TurtleBot 4 deployment):
        # 1. Use BasicNavigator from nav2_simple_commander
        # 2. Set goal pose
        # 3. Monitor navigation status asynchronously
        raise NotImplementedError("ROS 2 Nav2 navigation will be enabled on TurtleBot 4.")

    async def go_charge(self) -> bool:
        logger.info("[ROS2Navigation] Initiating docking/charging sequence...")
        # TODO (TurtleBot 4 deployment):
        # 1. Use dock action from turtlebot4_navigation / Nav2 dock action
        # 2. Monitor docking status asynchronously
        raise NotImplementedError("ROS 2 docking/charging will be enabled on TurtleBot 4.")

    async def cancel(self) -> None:
        logger.info("[ROS2Navigation] Cancelling active Nav2 goal...")
        # TODO: navigator.cancelTask()

    def get_current_pose(self) -> Tuple[float, float, float]:
        # TODO: Read from /tf or /odom
        return self.x, self.y, self.rotation
