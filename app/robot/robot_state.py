import datetime
import enum
from typing import Any, Dict


class RobotStatus(str, enum.Enum):
    """Represents the possible statuses of the robot."""
    Idle = "Idle"
    DoingTask = "DoingTask"
    Charging = "Charging"
    Error = "Error"
    Offline = "Offline"


def build_initial_robot_state(robot_id: str = "") -> Dict[str, Any]:
    """Generates the initial state payload for the robot."""
    return {
        "RobotId": robot_id,
        "X": 0.0,
        "Y": 0.0,
        "Rotation": 0.0,
        "Battery": 100.0,
        "Status": RobotStatus.Idle.value,
        "CurrentTaskId": None,
        "LastHeartbeat": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
