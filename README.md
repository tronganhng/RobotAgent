# Robot Agent

Robot Agent is a client adapter for the Fleet Management system. It connects to the Fleet Backend over WebSocket, handles registration, receives fleet commands, and reports robot states/events.

The project is structured modularly to run in **PC testing mode (Mock)** during development and deploy seamlessly to **TurtleBot 4 (ROS 2 / Nav2)** in production.

---

## 1. Project Structure

```text
RobotAgent/
│
├── app/
│   ├── __init__.py                  # App package initialization
│   ├── config.py                    # Server URL defaults & logging configuration
│   ├── main.py                      # Application CLI entrypoint
│   │
│   ├── communication/               # WebSocket communication & wire protocol
│   │   ├── __init__.py
│   │   ├── message_protocol.py      # SocketMessageType enum & message formatters
│   │   └── websocket_client.py      # Low-level WebSocket client & connection lifecycle
│   │
│   ├── handlers/                    # Message routing and ID extraction
│   │   ├── __init__.py
│   │   └── message_handler.py       # JSON parsing & robot ID extractors
│   │
│   ├── robot/                       # Robot agent core & state management
│   │   ├── __init__.py
│   │   ├── robot_state.py           # RobotStatus enum & state snapshot builders
│   │   └── robot_agent.py           # RobotAgent coordination & lifecycle
│   │
│   └── navigation/                  # Navigation layer (Mock vs TurtleBot 4 ROS 2)
│       ├── __init__.py
│       ├── navigation_interface.py  # Abstract navigation base class
│       ├── mock_navigation.py       # Simulated navigation for PC testing
│       └── ros2_navigation.py       # ROS 2 / Nav2 navigation for TurtleBot 4
│
├── tests/
│   ├── __init__.py
│   ├── test_modules.py              # Unit tests for protocol & state models
│   └── test_registration_flow.py   # Integration tests for 3-step registration flow
│
├── robot_agent.py                   # Backward compatibility wrapper & root runner
├── requirements.txt
└── README.md
```

---

## 2. Requirements & Setup

### Requirements
- Python 3.10+ (tested with Python 3.12)
- `websockets` package

### Installation

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Running the Agent

Make sure the Fleet Backend is running at `ws://localhost:5055/ws`.

```powershell
# Run using the modular package entrypoint
.venv\Scripts\python.exe -m app.main

# Or specify a custom server URL
.venv\Scripts\python.exe -m app.main ws://192.168.1.100:5055/ws

# Or using the root wrapper
.venv\Scripts\python.exe robot_agent.py
```

---

## 4. Running Unit & Integration Tests

```powershell
# Run all tests
.venv\Scripts\python.exe -m unittest discover tests

# Or run specific test files
.venv\Scripts\python.exe -m unittest tests/test_registration_flow.py
.venv\Scripts\python.exe -m unittest tests/test_modules.py
```

---

## 5. TurtleBot 4 & ROS 2 Integration Roadmap

- **Phase 1 (Completed):** WebSocket transport, keepalive, graceful shutdown.
- **Phase 2 (Completed):** 3-Step Registration (`RegisterRobot` -> receive `RobotId` -> `RegisterClient` as `Robot`).
- **Phase 3:** Command dispatching (`MoveRobot`).
- **Phase 4:** Navigation execution (`MockNavigation` for PC, `ROS2Navigation` using Nav2 for TurtleBot 4) and arrival reporting (`RobotArrived`).
- **Phase 5:** Live telemetry & state synchronization (`RobotState`: X, Y, Rotation, Battery, Status).
- **Phase 6:** Heartbeat monitoring & automatic reconnect.
- **Phase 7 & 8:** Deploy on Ubuntu / TurtleBot 4 hardware via ROS 2 (`rclpy` & `nav2_simple_commander`).
