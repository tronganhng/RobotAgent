#!/usr/bin/env python3

import math
import rclpy

from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import (
    BasicNavigator,
    TaskResult,
)


def main():
    rclpy.init()

    navigator = BasicNavigator()

    print("Waiting for Nav2...")
    navigator.waitUntilNav2Active()

    # Goal position trong map
    x = -3.0
    y = 0.0
    yaw = 0.0

    goal = PoseStamped()

    goal.header.frame_id = "map"
    goal.header.stamp = navigator.get_clock().now().to_msg()

    goal.pose.position.x = x
    goal.pose.position.y = y
    goal.pose.position.z = 0.0

    # yaw -> quaternion
    goal.pose.orientation.z = math.sin(yaw / 2.0)
    goal.pose.orientation.w = math.cos(yaw / 2.0)

    print(f"Going to ({x}, {y}, {yaw})")

    navigator.goToPose(goal)

    while not navigator.isTaskComplete():

        feedback = navigator.getFeedback()

        if feedback is not None:
            print(
                f"Distance remaining: "
                f"{feedback.distance_remaining:.2f} m"
            )

        rclpy.spin_once(
            navigator,
            timeout_sec=0.1
        )

    result = navigator.getResult()

    if result == TaskResult.SUCCEEDED:
        print("Robot arrived!")

    elif result == TaskResult.CANCELED:
        print("Navigation canceled.")

    elif result == TaskResult.FAILED:
        print("Navigation failed.")

    else:
        print("Unknown navigation result.")

    rclpy.shutdown()


if __name__ == "__main__":
    main()