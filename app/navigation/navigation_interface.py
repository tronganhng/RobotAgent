from abc import ABC, abstractmethod
from typing import Tuple


class NavigationInterface(ABC):
    """
    Abstract interface for robot navigation.
    Isolates the Fleet WebSocket layer from specific navigation implementations (Mock vs ROS 2/Nav2).
    """

    @abstractmethod
    async def navigate_to(self, x: float, y: float, rotation: float = 0.0) -> bool:
        """
        Navigates the robot to the specified coordinates.
        Returns True if arrival was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def go_charge(self) -> bool:
        """
        Navigates the robot to the charging station/dock and initiates charging.
        Returns True if arrival and docking/charging started successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def cancel(self) -> None:
        """Cancels any current navigation goal."""
        pass

    @abstractmethod
    def get_current_pose(self) -> Tuple[float, float, float]:
        """Returns the current estimated pose (x, y, rotation)."""
        pass

