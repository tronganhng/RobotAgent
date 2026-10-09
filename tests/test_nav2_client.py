import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch


class _ImmediateFuture:
    def __init__(self, value):
        self._value = value

    def done(self):
        return True

    def result(self):
        return self._value


class _PoseStamped:
    def __init__(self):
        self.header = SimpleNamespace(frame_id=None, stamp=None)
        self.pose = SimpleNamespace(
            position=SimpleNamespace(x=None, y=None, z=None),
            orientation=SimpleNamespace(x=None, y=None, z=None, w=None),
        )


class _NavigateToPose:
    class Goal:
        pass


class _GoalStatus:
    STATUS_SUCCEEDED = 4
    STATUS_CANCELED = 5
    STATUS_ABORTED = 6


def _ros_import_stubs():
    action_msgs = ModuleType("action_msgs")
    action_msgs.__path__ = []
    action_msgs_msg = ModuleType("action_msgs.msg")
    action_msgs_msg.GoalStatus = _GoalStatus
    action_msgs.msg = action_msgs_msg

    geometry_msgs = ModuleType("geometry_msgs")
    geometry_msgs.__path__ = []
    geometry_msgs_msg = ModuleType("geometry_msgs.msg")
    geometry_msgs_msg.PoseStamped = _PoseStamped
    geometry_msgs.msg = geometry_msgs_msg

    nav2_msgs = ModuleType("nav2_msgs")
    nav2_msgs.__path__ = []
    nav2_msgs_action = ModuleType("nav2_msgs.action")
    nav2_msgs_action.NavigateToPose = _NavigateToPose
    nav2_msgs.action = nav2_msgs_action

    rclpy = ModuleType("rclpy")
    rclpy.__path__ = []
    rclpy_action = ModuleType("rclpy.action")
    rclpy_action.ActionClient = MagicMock()
    rclpy.action = rclpy_action

    return {
        "action_msgs": action_msgs,
        "action_msgs.msg": action_msgs_msg,
        "geometry_msgs": geometry_msgs,
        "geometry_msgs.msg": geometry_msgs_msg,
        "nav2_msgs": nav2_msgs,
        "nav2_msgs.action": nav2_msgs_action,
        "rclpy": rclpy,
        "rclpy.action": rclpy_action,
    }


with patch.dict(sys.modules, _ros_import_stubs()):
    from app.navigation.ros2.nav2_client import Nav2Client


class TestNav2Client(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.node = MagicMock()
        self.node.get_clock.return_value.now.return_value.to_msg.return_value = "stamp"
        self.action_client = MagicMock()
        self.nav2_client = Nav2Client(self.node)
        self.nav2_client._action_client = self.action_client

    async def test_navigate_to_sends_goal_and_returns_success(self):
        goal_handle = MagicMock(accepted=True)
        goal_handle.get_result_async.return_value = _ImmediateFuture(
            SimpleNamespace(status=_GoalStatus.STATUS_SUCCEEDED)
        )
        self.action_client.wait_for_server.return_value = True
        self.action_client.send_goal_async.return_value = _ImmediateFuture(goal_handle)

        result = await self.nav2_client.navigate_to(1.25, -2.5, 0.0)

        self.assertTrue(result)
        self.assertIsNone(self.nav2_client._goal_handle)
        self.action_client.wait_for_server.assert_called_once_with(timeout_sec=15.0)
        sent_goal = self.action_client.send_goal_async.call_args.args[0]
        self.assertEqual(sent_goal.pose.header.frame_id, "map")
        self.assertEqual(sent_goal.pose.header.stamp, "stamp")
        self.assertEqual(sent_goal.pose.pose.position.x, 1.25)
        self.assertEqual(sent_goal.pose.pose.position.y, -2.5)
        self.assertEqual(sent_goal.pose.pose.position.z, 0.0)
        self.assertEqual(sent_goal.pose.pose.orientation.z, 0.0)
        self.assertEqual(sent_goal.pose.pose.orientation.w, 1.0)

    async def test_navigate_to_returns_false_when_server_unavailable(self):
        self.action_client.wait_for_server.return_value = False

        result = await self.nav2_client.navigate_to(1.0, 2.0)

        self.assertFalse(result)
        self.action_client.send_goal_async.assert_not_called()


if __name__ == "__main__":
    unittest.main()