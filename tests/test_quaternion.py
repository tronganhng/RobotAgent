import math
import unittest

from app.navigation.ros2.quaternion import quaternion_to_yaw, yaw_to_quaternion


class TestQuaternionHelpers(unittest.TestCase):
    def test_yaw_to_quaternion_zero(self):
        qx, qy, qz, qw = yaw_to_quaternion(0.0)
        self.assertAlmostEqual(qx, 0.0)
        self.assertAlmostEqual(qy, 0.0)
        self.assertAlmostEqual(qz, 0.0)
        self.assertAlmostEqual(qw, 1.0)

    def test_quaternion_to_yaw_zero(self):
        yaw = quaternion_to_yaw(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(yaw, 0.0)

    def test_yaw_to_quaternion_and_back_cardinal_angles(self):
        test_angles = [
            0.0,
            math.pi / 4.0,
            math.pi / 2.0,
            math.pi * 3.0 / 4.0,
            -math.pi / 4.0,
            -math.pi / 2.0,
            -math.pi * 3.0 / 4.0,
            -2.564,
            1.57,
        ]
        for expected_yaw in test_angles:
            qx, qy, qz, qw = yaw_to_quaternion(expected_yaw)
            actual_yaw = quaternion_to_yaw(qx, qy, qz, qw)
            self.assertAlmostEqual(
                actual_yaw,
                expected_yaw,
                places=6,
                msg=f"Failed for angle {expected_yaw}",
            )

    def test_quaternion_normalization_handling(self):
        # 90 degrees around Z axis: z = sin(45 deg) = sqrt(2)/2, w = cos(45 deg) = sqrt(2)/2
        val = math.sqrt(2.0) / 2.0
        yaw = quaternion_to_yaw(0.0, 0.0, val, val)
        self.assertAlmostEqual(yaw, math.pi / 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
