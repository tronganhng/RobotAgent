import asyncio
import logging
from typing import Optional

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient

from app.navigation.ros2.quaternion import yaw_to_quaternion
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics

logger = logging.getLogger("RobotAgent")


class Nav2Client:
    """
    ActionClient wrapper for Nav2 NavigateToPose action on TurtleBot 4.

    The robot namespace is configurable and defaults to ``robot3``.
    """

    def __init__(
        self,
        node,
        robot_namespace: str = DEFAULT_ROBOT_NAMESPACE,
    ) -> None:
        if node is None:
            raise ValueError("Nav2Client requires an rclpy Node.")

        self.node = node
        self.topics = RobotTopics(robot_namespace)
        self._action_client = ActionClient(
            self.node,
            NavigateToPose,
            self.topics.navigate_to_pose,
        )
        self._goal_handle = None
        logger.info(
            "[Nav2Client] Initialized on %s.", self.topics.navigate_to_pose
        )

    async def navigate_to(
        self,
        x: float,
        y: float,
        rotation: float = 0.0,
    ) -> bool:
        """
        Sends a NavigateToPose goal and waits asynchronously for result.
        Returns True if successful, False otherwise.
        """
        logger.info(
            f"[Nav2Client] Sending Nav2 goal: x={x:.3f}, y={y:.3f}, yaw={rotation:.3f}"
        )

        # Wait for Nav2 action server
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            logger.error("[Nav2Client] Nav2 action server is not available.")
            return False

        # Build goal
        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = "map"
        goal.pose.header.stamp = self.node.get_clock().now().to_msg()

        goal.pose.pose.position.x = x
        goal.pose.pose.position.y = y
        goal.pose.pose.position.z = 0.0

        qx, qy, qz, qw = yaw_to_quaternion(rotation)
        goal.pose.pose.orientation.x = qx
        goal.pose.pose.orientation.y = qy
        goal.pose.pose.orientation.z = qz
        goal.pose.pose.orientation.w = qw

        # Send goal
        future = self._action_client.send_goal_async(
            goal,
            feedback_callback=self._feedback_callback,
        )

        while not future.done():
            await asyncio.sleep(0.05)

        try:
            goal_handle = future.result()
        except Exception as exc:
            logger.exception("[Nav2Client] Failed to send Nav2 goal: %s", exc)
            return False

        if not goal_handle.accepted:
            logger.error("[Nav2Client] Nav2 rejected goal.")
            return False

        self._goal_handle = goal_handle
        logger.info("[Nav2Client] Nav2 goal accepted.")

        # Wait for result
        result_future = goal_handle.get_result_async()
        while not result_future.done():
            await asyncio.sleep(0.05)

        try:
            result = result_future.result()
        except Exception as exc:
            logger.exception("[Nav2Client] Failed to get navigation result: %s", exc)
            self._goal_handle = None
            return False

        status = result.status
        self._goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:
            logger.info("[Nav2Client] Robot reached destination.")
            return True

        if status == GoalStatus.STATUS_CANCELED:
            logger.warning("[Nav2Client] Navigation canceled.")
            return False

        if status == GoalStatus.STATUS_ABORTED:
            logger.error("[Nav2Client] Navigation aborted.")
            return False

        logger.warning(f"[Nav2Client] Navigation finished with status={status}")
        return False

    def _feedback_callback(self, feedback_msg) -> None:
        feedback = feedback_msg.feedback
        logger.debug(
            f"[Nav2Client] Distance remaining: {feedback.distance_remaining:.2f} m"
        )

    async def cancel(self) -> None:
        """Cancels active navigation goal if running."""
        goal_handle = self._goal_handle
        if goal_handle is None:
            logger.info("[Nav2Client] No active navigation goal to cancel.")
            return

        logger.info("[Nav2Client] Cancelling active Nav2 goal...")
        try:
            future = goal_handle.cancel_goal_async()
            while not future.done():
                await asyncio.sleep(0.05)
            logger.info("[Nav2Client] Navigation cancel request sent.")
        except Exception as exc:
            logger.exception(f"[Nav2Client] Failed to cancel navigation: {exc}")
        finally:
            self._goal_handle = None
