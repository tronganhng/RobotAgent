import asyncio
import logging
from typing import Tuple
from app.navigation.navigation_interface import NavigationInterface

logger = logging.getLogger("RobotAgent")


class MockNavigation(NavigationInterface):
    """
    Simulated navigation implementation for testing on PC without ROS 2 or TurtleBot hardware.
    """

    def __init__(self, speed: float = 1.0) -> None:
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: float = 0.0
        self.speed: float = speed
        self._nav_task: asyncio.Task | None = None

    async def navigate_to(self, x: float, y: float, rotation: float = 0.0) -> bool:
        logger.info(f"[MockNavigation] Navigating to ({x}, {y}, rot={rotation})...")
        try:
            # Simulate navigation delay
            await asyncio.sleep(1.0)
            self.x = x
            self.y = y
            self.rotation = rotation
            logger.info(f"[MockNavigation] Successfully arrived at ({x}, {y}, rot={rotation}).")
            return True
        except asyncio.CancelledError:
            logger.info("[MockNavigation] Navigation cancelled.")
    async def go_charge(self) -> bool:
        logger.info("[MockNavigation] Moving to charging dock and starting charge...")
        try:
            # Simulate navigation and docking delay
            await asyncio.sleep(1.0)
            logger.info("[MockNavigation] Successfully docked and charging.")
            return True
        except asyncio.CancelledError:
            logger.info("[MockNavigation] Charging navigation cancelled.")
            return False

    async def cancel(self) -> None:
        if self._nav_task and not self._nav_task.done():
            self._nav_task.cancel()
            logger.info("[MockNavigation] Cancel request sent.")

    def get_current_pose(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.rotation
