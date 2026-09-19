import asyncio
import logging
from typing import Optional

from action_msgs.msg import GoalStatus
from irobot_create_msgs.action import Dock, Undock
from irobot_create_msgs.msg import DockStatus
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data

from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics

logger = logging.getLogger("RobotAgent")


class DockingClient:
    """
    ActionClient wrapper for TurtleBot 4 / iRobot Create 3 Dock and Undock actions.

    The robot namespace is configurable and defaults to ``robot3``.
    """

    def __init__(
        self,
        node,
        robot_namespace: str = DEFAULT_ROBOT_NAMESPACE,
    ) -> None:
        if node is None:
            raise ValueError("DockingClient requires an rclpy Node.")

        self.node = node
        self.topics = RobotTopics(robot_namespace)

        self._dock_client = ActionClient(
            self.node,
            Dock,
            self.topics.dock,
        )

        self._undock_client = ActionClient(
            self.node,
            Undock,
            self.topics.undock,
        )

        self._is_docked: Optional[bool] = None
        self._dock_status_subscription = self.node.create_subscription(
            DockStatus,
            self.topics.dock_status,
            self._dock_status_callback,
            qos_profile_sensor_data,
        )

        self._dock_goal_handle = None
        self._undock_goal_handle = None

        logger.info(
            "[DockingClient] Initialized on %s and %s.",
            self.topics.dock,
            self.topics.undock,
        )

    async def dock(self) -> bool:
        """
        Sends a Dock goal and waits asynchronously for result.
        Returns True if docked successfully, False otherwise.
        """
        logger.info("[DockingClient] Starting docking sequence...")

        if not self._dock_client.wait_for_server(timeout_sec=5.0):
            logger.error("[DockingClient] Dock action server is not available.")
            return False

        goal = Dock.Goal()
        future = self._dock_client.send_goal_async(goal)

        while not future.done():
            await asyncio.sleep(0.05)

        try:
            goal_handle = future.result()
        except Exception as exc:
            logger.exception(f"[DockingClient] Failed to send dock goal: {exc}")
            return False

        if not goal_handle.accepted:
            logger.error("[DockingClient] Dock goal rejected.")
            return False

        self._dock_goal_handle = goal_handle
        logger.info("[DockingClient] Dock goal accepted.")

        result_future = goal_handle.get_result_async()
        while not result_future.done():
            await asyncio.sleep(0.05)

        try:
            result = result_future.result()
        except Exception as exc:
            logger.exception(f"[DockingClient] Failed to get dock result: {exc}")
            self._dock_goal_handle = None
            return False

        status = result.status
        self._dock_goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:
            logger.info("[DockingClient] Robot docked successfully.")
            return True

        logger.error(f"[DockingClient] Docking failed with status={status}")
        return False

    async def undock(self) -> bool:
        """
        Sends an Undock goal and waits asynchronously for result.
        Returns True if undocked successfully, False otherwise.
        """
        logger.info("[DockingClient] Starting undocking sequence...")

        if not self._undock_client.wait_for_server(timeout_sec=5.0):
            logger.error("[DockingClient] Undock action server is not available.")
            return False

        goal = Undock.Goal()
        future = self._undock_client.send_goal_async(goal)

        while not future.done():
            await asyncio.sleep(0.05)

        try:
            goal_handle = future.result()
        except Exception as exc:
            logger.exception(f"[DockingClient] Failed to send undock goal: {exc}")
            return False

        if not goal_handle.accepted:
            logger.error("[DockingClient] Undock goal rejected.")
            return False

        self._undock_goal_handle = goal_handle
        logger.info("[DockingClient] Undock goal accepted.")

        result_future = goal_handle.get_result_async()
        while not result_future.done():
            await asyncio.sleep(0.05)

        try:
            result = result_future.result()
        except Exception as exc:
            logger.exception(f"[DockingClient] Failed to get undock result: {exc}")
            self._undock_goal_handle = None
            return False

        status = result.status
        self._undock_goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:
            logger.info("[DockingClient] Robot undocked successfully.")
            return True

        logger.error(f"[DockingClient] Undocking failed with status={status}")
        return False

    async def cancel(self) -> None:
        """Cancels any active dock or undock goal."""
        for name, handle in (("dock", self._dock_goal_handle), ("undock", self._undock_goal_handle)):
            if handle is not None:
                logger.info(f"[DockingClient] Cancelling active {name} goal...")
                try:
                    future = handle.cancel_goal_async()
                    while not future.done():
                        await asyncio.sleep(0.05)
                except Exception as exc:
                    logger.exception(f"[DockingClient] Failed to cancel {name} goal: {exc}")

        self._dock_goal_handle = None
        self._undock_goal_handle = None

    def _dock_status_callback(self, msg: DockStatus) -> None:
        logger.debug(f"[DockingClient] Dock status updated: {msg}")
