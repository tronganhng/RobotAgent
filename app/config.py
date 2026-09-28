import logging

DEFAULT_SERVER_URL = "ws://192.168.1.39:5055/ws"

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures and returns the main application logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("RobotAgent")

logger = setup_logging()
