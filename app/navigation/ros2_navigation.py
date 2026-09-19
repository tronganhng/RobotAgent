import logging
from typing import Optional, Tuple

from app.navigation.navigation_interface import NavigationInterface
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE

logger = logging.getLogger("RobotAgent")


class ROS2Navigation(NavigationInterface):
    """
    ROS 2 / Nav2 navigation facade for TurtleBot 4.
    Acts as a thin orchestrator delegating to specialized ROS2 sub-components:
    - Nav2Client: NavigateToPose ActionClient
    - DockingClient: Dock and Undock ActionClients
    - Odometry: Odometry subscriber

    The ROS node lifecycle remains owned by the application layer.
    """

    def __init__(
        self,
        node=None,
        nav2_client=None,
        docking_client=None,
        odometry=None,
        robot_namespace: str = DEFAULT_ROBOT_NAMESPACE,
    ) -> None:
        self.node = node
        self.robot_namespace = robot_namespace

        if nav2_client is not None and docking_client is not None and odometry is not None:
            self._nav2_client = nav2_client
            self._docking_client = docking_client
            self._odometry = odometry
        elif self.node is not None:
            from app.navigation.ros2.docking_client import DockingClient
            from app.navigation.ros2.nav2_client import Nav2Client
            from app.navigation.ros2.odometry import Odometry

            self._nav2_client = nav2_client or Nav2Client(
                self.node, robot_namespace
            )
            self._docking_client = docking_client or DockingClient(
                self.node, robot_namespace
            )
            self._odometry = odometry or Odometry(self.node, robot_namespace)
        else:
            raise ValueError(
                "ROS2Navigation requires an rclpy Node or injected sub-components."
            )

        logger.info("[ROS2Navigation] Initialized facade.")

    async def navigate_to(
        self,
        x: float,
        y: float,
        rotation: float = 0.0,
    ) -> bool:
        """Navigates to the specified coordinates via Nav2."""
        return await self._nav2_client.navigate_to(x, y, rotation)

    async def go_charge(self) -> bool:
        """Docks the robot onto the charging station."""
        return await self._docking_client.dock()

    async def undock(self) -> bool:
        """Undocks the robot from the charging station."""
        return await self._docking_client.undock()

    async def cancel(self) -> None:
        """Cancels active navigation or motion goals."""
        await self._nav2_client.cancel()
        if hasattr(self._docking_client, "cancel"):
            await self._docking_client.cancel()

    def get_current_pose(self) -> Tuple[float, float, float]:
        """Returns the current estimated pose (x, y, rotation)."""
        return self._odometry.get_current_pose()