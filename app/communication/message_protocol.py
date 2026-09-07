import enum
from typing import Any, Dict, Optional
import uuid


class SocketMessageType(str, enum.Enum):
    RegisterClient = "RegisterClient"
    ServerResponse = "ServerResponse"
    RegisterRobot = "RegisterRobot"
    RobotState = "RobotState"
    MoveRobot = "MoveRobot"
    StopRobot = "StopRobot"
    RobotArrived = "RobotArrived"
    ChargeRobot = "ChargeRobot"


def format_message(
    message_type: SocketMessageType | str,
    payload: Optional[Any] = None,
    robot_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized JSON message dictionary matching Fleet Backend wire format:
    {
        "Type": "...",
        "RequestId": "...",
        "RobotId": "...",
        "Payload": ...
    }
    """
    mt = message_type.value if isinstance(message_type, enum.Enum) else str(message_type)
    return {
        "Type": mt,
        "RequestId": request_id or str(uuid.uuid4()),
        "RobotId": robot_id,
        "Payload": payload if payload is not None else {},
    }
