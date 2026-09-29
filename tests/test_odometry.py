import importlib
import math
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch


def load_odometry_class():
    nav_msgs = types.ModuleType("nav_msgs")
    nav_msgs_msg = types.ModuleType("nav_msgs.msg")
    sensor_msgs = types.ModuleType("sensor_msgs")
    sensor_msgs_msg = types.ModuleType("sensor_msgs.msg")
    rclpy = types.ModuleType("rclpy")
    rclpy_qos = types.ModuleType("rclpy.qos")

    class OdometryMsg:
        pass

    class BatteryState:
        pass

    sensor_qos = object()
    nav_msgs.msg = nav_msgs_msg
    nav_msgs_msg.Odometry = OdometryMsg
    sensor_msgs.msg = sensor_msgs_msg
    sensor_msgs_msg.BatteryState = BatteryState
    rclpy.qos = rclpy_qos
    rclpy_qos.qos_profile_sensor_data = sensor_qos

    with patch.dict(
        sys.modules,
        {
            "nav_msgs": nav_msgs,
            "nav_msgs.msg": nav_msgs_msg,
            "sensor_msgs": sensor_msgs,
            "sensor_msgs.msg": sensor_msgs_msg,
            "rclpy": rclpy,
            "rclpy.qos": rclpy_qos,
        },
    ):
        module = importlib.import_module("app.navigation.ros2.odometry")

    return module.Odometry, OdometryMsg, BatteryState, sensor_qos


Odometry, OdometryMsg, BatteryState, SENSOR_QOS = load_odometry_class()


class FakeNode:
    def __init__(self):
        self.subscriptions = []

    def create_subscription(self, message_type, topic, callback, qos):
        subscription = (message_type, topic, callback, qos)
        self.subscriptions.append(subscription)
        return subscription


class TestOdometry(unittest.TestCase):
    def setUp(self):
        self.node = FakeNode()
        self.odometry = Odometry(self.node, robot_namespace="warehouse/robot7")

    def test_creates_sensor_subscriptions_for_configured_namespace(self):
        self.assertEqual(self.node.subscriptions[0][0], OdometryMsg)
        self.assertEqual(self.node.subscriptions[0][1], "/warehouse/robot7/odom")
        self.assertEqual(self.node.subscriptions[1][0], BatteryState)
        self.assertEqual(
            self.node.subscriptions[1][1], "/warehouse/robot7/battery_state"
        )
        self.assertIs(self.node.subscriptions[1][3], SENSOR_QOS)

    def test_battery_fraction_is_converted_to_percentage(self):
        self.odometry._battery_callback(SimpleNamespace(percentage=0.75))

        self.assertEqual(self.odometry.battery, 75.0)
        self.assertTrue(self.odometry.battery_received)

    def test_invalid_battery_values_do_not_replace_last_valid_reading(self):
        self.odometry._battery_callback(SimpleNamespace(percentage=0.42))

        for percentage in (float("nan"), -0.1, 1.1, None, "invalid"):
            self.odometry._battery_callback(SimpleNamespace(percentage=percentage))
            self.assertEqual(self.odometry.battery, 42.0)

    def test_odometry_pose_calculation_is_unchanged(self):
        half_yaw = math.pi / 4.0
        message = SimpleNamespace(
            pose=SimpleNamespace(
                pose=SimpleNamespace(
                    position=SimpleNamespace(x=1.25, y=-2.5),
                    orientation=SimpleNamespace(
                        x=0.0,
                        y=0.0,
                        z=math.sin(half_yaw),
                        w=math.cos(half_yaw),
                    ),
                )
            )
        )

        self.odometry._odom_callback(message)

        self.assertAlmostEqual(self.odometry.x, 1.25)
        self.assertAlmostEqual(self.odometry.y, -2.5)
        self.assertAlmostEqual(self.odometry.rotation, math.pi / 2.0)
        pose = self.odometry.get_current_pose()
        self.assertEqual(pose[:2], (1.25, -2.5))
        self.assertAlmostEqual(pose[2], math.pi / 2.0)
        self.assertEqual(pose[3], 0.0)


if __name__ == "__main__":
    unittest.main()