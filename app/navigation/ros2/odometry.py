import logging
from typing import Tuple

from nav_msgs.msg import Odometry as OdometryMsg
from rclpy.qos import qos_profile_sensor_data

from app.navigation.ros2.quaternion import quaternion_to_yaw

logger = logging.getLogger("RobotAgent")


class Odometry:
    """
    Subscribes to odometry topic and maintains the robot's current 2D pose (x, y, yaw).

    Topic:
        /robot3/odom
    """

    def __init__(self, node) -> None:
        if node is None:
            raise ValueError("Odometry requires an rclpy Node.")

        self.node = node
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: float = 0.0
        self._odom_received: bool = False

        self._odom_subscription = self.node.create_subscription(
            OdometryMsg,
            "/robot3/odom",
            self._odom_callback,
            qos_profile_sensor_data,
        )
        logger.info("[Odometry] Subscribed to /robot3/odom.")

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

    def get_current_pose(self) -> Tuple[float, float, float]:
        """Returns the current estimated pose (x, y, rotation)."""
        return self.x, self.y, self.rotation
