#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus


class GoToPosition(Node):

    def __init__(self):
        super().__init__('go_to_position')

        # ==========================================
        # Goal configuration
        # ==========================================

        self.x = -3.018
        self.y = -0.2792
        self.yaw = -2.564

        self.get_logger().info(
            f'Goal: x={self.x:.4f}, '
            f'y={self.y:.4f}, '
            f'yaw={self.yaw:.4f}'
        )

        # ==========================================
        # Nav2 Action Client
        # ==========================================

        self.action_client = ActionClient(
            self,
            NavigateToPose,
            '/robot3/navigate_to_pose'
        )

        self.get_logger().info(
            'Đang chờ Nav2 action '
            '/robot3/navigate_to_pose...'
        )

        if not self.action_client.wait_for_server(
            timeout_sec=10.0
        ):
            self.get_logger().error(
                'Không tìm thấy Nav2 action server!'
            )
            raise RuntimeError(
                '/robot3/navigate_to_pose không available'
            )

        self.get_logger().info(
            'Đã kết nối Nav2!'
        )

        self.goal_handle = None

        self.send_goal()

    # ==========================================
    # Send goal
    # ==========================================

    def send_goal(self):

        goal_msg = NavigateToPose.Goal()

        goal_msg.pose = PoseStamped()

        # Quan trọng: giữ nguyên frame_id như file chạy ổn
        goal_msg.pose.header.frame_id = 'map'

        goal_msg.pose.header.stamp = (
            self.get_clock().now().to_msg()
        )

        # Position
        goal_msg.pose.pose.position.x = self.x
        goal_msg.pose.pose.position.y = self.y
        goal_msg.pose.pose.position.z = 0.0

        # Yaw -> Quaternion
        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = math.sin(
            self.yaw / 2.0
        )
        goal_msg.pose.pose.orientation.w = math.cos(
            self.yaw / 2.0
        )

        self.get_logger().info(
            'Đang gửi goal...'
        )

        future = self.action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        future.add_done_callback(
            self.goal_response_callback
        )

    # ==========================================
    # Goal response
    # ==========================================

    def goal_response_callback(self, future):

        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error(
                'Nav2 từ chối goal!'
            )
            rclpy.shutdown()
            return

        self.goal_handle = goal_handle

        self.get_logger().info(
            'Goal đã được Nav2 chấp nhận.'
        )

        result_future = (
            goal_handle.get_result_async()
        )

        result_future.add_done_callback(
            self.result_callback
        )

    # ==========================================
    # Feedback
    # ==========================================

    def feedback_callback(self, feedback_msg):

        feedback = feedback_msg.feedback

        self.get_logger().info(
            f'Distance remaining: '
            f'{feedback.distance_remaining:.2f} m',
            throttle_duration_sec=2.0
        )

    # ==========================================
    # Result
    # ==========================================

    def result_callback(self, future):

        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:

            self.get_logger().info(
                '======================================'
            )
            self.get_logger().info(
                'ROBOT ĐÃ ĐẾN VỊ TRÍ!'
            )
            self.get_logger().info(
                '======================================'
            )

        elif status == GoalStatus.STATUS_CANCELED:

            self.get_logger().warn(
                'Navigation canceled.'
            )

        elif status == GoalStatus.STATUS_ABORTED:

            self.get_logger().error(
                'Navigation failed / aborted.'
            )

        else:

            self.get_logger().warn(
                f'Navigation kết thúc với status = {status}'
            )

        rclpy.shutdown()

    # ==========================================
    # Cancel
    # ==========================================

    def cancel_goal(self):

        if self.goal_handle is None:
            return

        self.get_logger().info(
            'Đang cancel goal...'
        )

        self.goal_handle.cancel_goal_async()


# ==============================================
# Main
# ==============================================

def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = GoToPosition()

        rclpy.spin(node)

    except KeyboardInterrupt:

        if node is not None:
            node.get_logger().info(
                'Ctrl+C -> dừng navigation.'
            )
            node.cancel_goal()

    except Exception as e:

        if node is not None:
            node.get_logger().error(
                f'Lỗi: {e}'
            )

    finally:

        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()