import unittest
from unittest.mock import AsyncMock, MagicMock

from app.navigation.navigation_interface import NavigationInterface
from app.navigation.ros2_navigation import ROS2Navigation


class TestROS2NavigationFacade(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_nav2 = MagicMock()
        self.mock_nav2.navigate_to = AsyncMock(return_value=True)
        self.mock_nav2.cancel = AsyncMock()

        self.mock_docking = MagicMock()
        self.mock_docking.dock = AsyncMock(return_value=True)
        self.mock_docking.undock = AsyncMock(return_value=True)
        self.mock_docking.cancel = AsyncMock()

        self.mock_odometry = MagicMock()
        self.mock_odometry.get_current_pose = MagicMock(return_value=(1.5, 2.5, 0.78))

        self.facade = ROS2Navigation(
            nav2_client=self.mock_nav2,
            docking_client=self.mock_docking,
            odometry=self.mock_odometry,
        )

    def test_implements_interface(self):
        self.assertIsInstance(self.facade, NavigationInterface)

    def test_init_raises_without_node_or_clients(self):
        with self.assertRaises(ValueError):
            ROS2Navigation()

    async def test_navigate_to_delegation(self):
        result = await self.facade.navigate_to(10.0, 20.0, 1.57)
        self.assertTrue(result)
        self.mock_nav2.navigate_to.assert_awaited_once_with(10.0, 20.0, 1.57)

    async def test_go_charge_delegation(self):
        result = await self.facade.go_charge()
        self.assertTrue(result)
        self.mock_docking.dock.assert_awaited_once()

    async def test_undock_delegation(self):
        result = await self.facade.undock()
        self.assertTrue(result)
        self.mock_docking.undock.assert_awaited_once()

    async def test_cancel_delegation(self):
        await self.facade.cancel()
        self.mock_nav2.cancel.assert_awaited_once()
        self.mock_docking.cancel.assert_awaited_once()

    def test_get_current_pose_delegation(self):
        pose = self.facade.get_current_pose()
        self.assertEqual(pose, (1.5, 2.5, 0.78))
        self.mock_odometry.get_current_pose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
