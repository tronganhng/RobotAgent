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
        self._send_future = None
        self._result_future = None
        self._cancel_lock = asyncio.Lock()
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
        if self._send_future is not None or self._goal_handle is not None:
            raise RuntimeError("Previous Nav2 goal must finish or be canceled first.")
        try:
            return await self._navigate_to(x, y, rotation)
        except asyncio.CancelledError:
            # Task cancellation does not cancel a ROS action. Keep ownership
            # until even a pending goal response has been resolved and stopped.
            await self.cancel()
            raise

    async def _navigate_to(self, x: float, y: float, rotation: float) -> bool:
        logger.info(
            f"[Nav2Client] Sending Nav2 goal: x={x:.3f}, y={y:.3f}, yaw={rotation:.3f}"
        )

        # Wait for Nav2 action server
        if not self._action_client.wait_for_server(timeout_sec=15.0):
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

        self._send_future = future

        while not future.done():
            await asyncio.sleep(0.05)

        try:
            goal_handle = future.result()
        except Exception as exc:
            self._send_future = None
            logger.exception("[Nav2Client] Failed to send Nav2 goal: %s", exc)
            return False

        self._send_future = None
        if goal_handle is None or not goal_handle.accepted:
            logger.error("[Nav2Client] Nav2 rejected goal.")
            return False

        self._goal_handle = goal_handle
        logger.info("[Nav2Client] Nav2 goal accepted.")

        # Wait for result
        result_future = goal_handle.get_result_async()
        self._result_future = result_future
        while not result_future.done():
            await asyncio.sleep(0.05)

        try:
            result = result_future.result()
        except Exception as exc:
            logger.exception("[Nav2Client] Failed to get navigation result: %s", exc)
            # Keep the handle so a subsequent stop can still cancel motion.
            return False

        status = result.status
        self._goal_handle = None
        self._result_future = None

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
        """Resolve pending acceptance, cancel, and confirm the goal has ended.

        On timeout or failure, retain ownership so callers can retry and must
        not start replacement motion under the assumption that it stopped.
        """
        async with self._cancel_lock:
            await asyncio.wait_for(self._cancel_goal(), timeout=15.0)

    async def _cancel_goal(self) -> None:
        if self._send_future is not None:
            while not self._send_future.done():
                await asyncio.sleep(0.05)
            handle = self._send_future.result()
            self._send_future = None
            if handle is not None and handle.accepted:
                self._goal_handle = handle

        handle = self._goal_handle
        if handle is None:
            return

        if self._result_future is None:
            self._result_future = handle.get_result_async()
        result_future = self._result_future

        if not result_future.done():
            logger.info("[Nav2Client] Cancelling active Nav2 goal...")
            cancel_future = handle.cancel_goal_async()
            while not cancel_future.done():
                await asyncio.sleep(0.05)
            response = cancel_future.result()
            # The goal may have finished naturally while cancellation raced it.
            if not response.goals_canceling and not result_future.done():
                raise RuntimeError("Nav2 did not accept the cancellation request.")

        while not result_future.done():
            await asyncio.sleep(0.05)
        result = result_future.result()
        if result is None or result.status not in (
            GoalStatus.STATUS_SUCCEEDED,
            GoalStatus.STATUS_CANCELED,
            GoalStatus.STATUS_ABORTED,
        ):
            raise RuntimeError("Nav2 goal termination could not be confirmed.")

        self._goal_handle = None
        self._result_future = None
        logger.info("[Nav2Client] Previous Nav2 goal has ended.")
