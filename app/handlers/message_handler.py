import json
import logging
from typing import Any, Dict, Optional

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
