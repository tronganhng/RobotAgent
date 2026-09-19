from dataclasses import dataclass


DEFAULT_ROBOT_NAMESPACE = "robot3"


@dataclass(frozen=True)
class RobotTopics:
    """ROS 2 action and topic names for one TurtleBot namespace."""

    namespace: str = DEFAULT_ROBOT_NAMESPACE

    def __post_init__(self) -> None:
        normalized = self.namespace.strip("/")
        if not normalized:
            raise ValueError("Robot namespace must not be empty.")
        object.__setattr__(self, "namespace", normalized)

    @property
    def navigate_to_pose(self) -> str:
        return f"/{self.namespace}/navigate_to_pose"

    @property
    def dock(self) -> str:
        return f"/{self.namespace}/dock"

    @property
    def undock(self) -> str:
        return f"/{self.namespace}/undock"

    @property
    def dock_status(self) -> str:
        return f"/{self.namespace}/dock_status"

    @property
    def odometry(self) -> str:
        return f"/{self.namespace}/odom"