import logging
import math
from typing import Tuple

from nav_msgs.msg import Odometry as OdometryMsg
from sensor_msgs.msg import BatteryState
from rclpy.qos import qos_profile_sensor_data

from app.navigation.ros2.quaternion import quaternion_to_yaw
from app.navigation.ros2.topics import DEFAULT_ROBOT_NAMESPACE, RobotTopics

logger = logging.getLogger("RobotAgent")


class Odometry:
    """
    Subscribes to odometry and battery topics and maintains the robot's current state.

    The robot namespace is configurable and defaults to ``robot3``.
    """

    def __init__(
        self,
        node,
        robot_namespace: str = DEFAULT_ROBOT_NAMESPACE,
    ) -> None:
        if node is None:
            raise ValueError("Odometry requires an rclpy Node.")

        self.node = node
        self.topics = RobotTopics(robot_namespace)
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: float = 0.0
        self.battery: float = 0.0
        self._odom_received: bool = False
        self._battery_received: bool = False

        self._odom_subscription = self.node.create_subscription(
            OdometryMsg,
            self.topics.odometry,
            self._odom_callback,
            qos_profile_sensor_data,
        )
        self._battery_subscription = self.node.create_subscription(
            BatteryState,
            self.topics.battery_state,
            self._battery_callback,
            qos_profile_sensor_data,
        )
        logger.info("[Odometry] Subscribed to %s.", self.topics.odometry)
        logger.info("[Odometry] Subscribed to %s.", self.topics.battery_state)

    def _odom_callback(self, msg: OdometryMsg) -> None:
        pose = msg.pose.pose
        self.x = pose.position.x
        self.y = pose.position.y

        self.rotation = quaternion_to_yaw(
            pose.orientation.x,
            pose.orientation.y,
            pose.orientation.z,
            pose.orientation.w,
        )
        self._odom_received = True

    @property
    def odom_received(self) -> bool:
        return self._odom_received

    def _battery_callback(self, msg: BatteryState) -> None:
        try:
            percentage = float(msg.percentage)
        except (AttributeError, TypeError, ValueError):
            return

        if not math.isfinite(percentage) or not 0.0 <= percentage <= 1.0:
            return

        self.battery = percentage * 100.0
        self._battery_received = True

    @property
    def battery_received(self) -> bool:
        return self._battery_received

    def get_current_pose(self) -> Tuple[float, float, float, float]:
        """Returns (x, y, rotation, battery), with battery in percent."""
        return self.x, self.y, self.rotation, self.battery
