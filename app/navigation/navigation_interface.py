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
    async def undock(self) -> bool:
        """
        Undocks the robot from the charging station/dock.
        Returns True if undocking completed successfully, False otherwise.
        """
        pass

    @abstractmethod
    async def cancel(self) -> None:
        """Cancels any current navigation or motion goal."""
        pass

    @abstractmethod
    def get_current_pose(self) -> Tuple[float, float, float, float]:
        """Returns the current estimated pose and battery (x, y, rotation, battery)."""
        pass

    async def change_floor(self, elevator_id: str, target_floor: int) -> bool:
        """Load the target floor map and relocalize; return True only when ready.

        Implementations without floor support must fail rather than acknowledge
        readiness on the old navigation map.
        """
        raise NotImplementedError("Floor/map switching is not configured for this navigation backend.")
