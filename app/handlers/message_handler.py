import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("RobotAgent")


def extract_robot_id(data: Dict[str, Any]) -> Optional[str]:
    """
    Extracts RobotId from data or payload with case-insensitivity.
    Supports PascalCase (RobotId), camelCase (robotId), uppercase (RobotID), and Id/id.
    """
    # Check in top-level fields
    for key in ("RobotId", "robotId", "RobotID"):
        if data.get(key):
            return str(data[key])

    # Check in payload dictionary
    payload = data.get("Payload") or data.get("payload")
    if isinstance(payload, dict):
        for key in ("RobotId", "robotId", "RobotID", "Id", "id"):
            if payload.get(key):
                return str(payload[key])

    return None


def parse_move_coordinates(payload: Any) -> Optional[Tuple[float, float]]:
    """
    Parses destination coordinates (x, y) from MoveRobot payload.
    Supports:
    - Array/List: [13.29, 20.33]
    - Dict: {"x": 13.29, "y": 20.33} or {"X": 13.29, "Y": 20.33}
    """
    if isinstance(payload, (list, tuple)) and len(payload) >= 2:
        try:
            return float(payload[0]), float(payload[1])
        except (ValueError, TypeError):
            return None

    if isinstance(payload, dict):
        x = payload.get("x") if "x" in payload else payload.get("X")
        y = payload.get("y") if "y" in payload else payload.get("Y")
        if x is not None and y is not None:
            try:
                return float(x), float(y)
            except (ValueError, TypeError):
                return None

    return None
