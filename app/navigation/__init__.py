"""Navigation subsystem supporting both Mock (PC testing) and ROS 2 / Nav2 (TurtleBot 4)."""

from app.navigation.navigation_interface import NavigationInterface
from app.navigation.mock_navigation import MockNavigation

__all__ = ["NavigationInterface", "MockNavigation"]

try:
    from app.navigation.ros2_navigation import ROS2Navigation
    __all__.append("ROS2Navigation")
except (ImportError, ModuleNotFoundError):
    pass
