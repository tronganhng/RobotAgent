import math
from typing import Tuple


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """
    Convert a quaternion (x, y, z, w) to a yaw angle (in radians) around the Z-axis.

    Formula:
        sin_yaw = 2.0 * (w * z + x * y)
        cos_yaw = 1.0 - 2.0 * (y * y + z * z)
        yaw = atan2(sin_yaw, cos_yaw)
    """
    sin_yaw = 2.0 * (w * z + x * y)
    cos_yaw = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(sin_yaw, cos_yaw)


def yaw_to_quaternion(yaw: float) -> Tuple[float, float, float, float]:
    """
    Convert a 2D planar yaw angle (in radians) to a quaternion tuple (x, y, z, w).

    For pure yaw rotation around the Z-axis:
        x = 0.0
        y = 0.0
        z = sin(yaw / 2.0)
        w = cos(yaw / 2.0)
    """
    return (
        0.0,
        0.0,
        math.sin(yaw / 2.0),
        math.cos(yaw / 2.0),
    )
