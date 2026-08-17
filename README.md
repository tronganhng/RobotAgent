# Robot Agent

Robot Agent is a client adapter for the Fleet Management system. It connects to the Fleet Backend over WebSocket, receives fleet commands, and reports robot states/events.

In the current stage (Phase 1), the agent runs on Windows PC and establishes a minimal, robust WebSocket connection to the Fleet Backend.

---

## 1. Requirements

- Python 3.12+ (or 3.10+)
- `websockets` package

---

## 2. Setup & Installation

### Create virtual environment
```powershell
python -m venv .venv
```

### Activate virtual environment
```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows Command Prompt
.venv\Scripts\activate.bat
```

### Install dependencies
```powershell
pip install -r requirements.txt
```

---

## 3. Usage

Make sure the Fleet Backend is running at `ws://localhost:5055/ws`.

Run the Robot Agent:

```powershell
# Using activated virtualenv
python robot_agent.py

# Or directly using the virtualenv python binary
.venv\Scripts\python.exe robot_agent.py
```

To stop the agent, press `Ctrl + C`.

---

## 4. Architecture & Roadmap

1. **Phase 1 (Current):** WebSocket connection, keepalive, clean shutdown.
2. **Phase 2:** Agent registration (`RegisterClient` & receive `RobotId`).
3. **Phase 3:** Command receiving (`MoveRobot`).
4. **Phase 4:** Mock navigation & arrival reporting (`RobotArrived`).
5. **Phase 5:** Robot state reporting (position, rotation, battery, status).
6. **Phase 6:** Heartbeat & automatic reconnection.
7. **Phase 7 & 8:** ROS 2 / Nav2 integration on TurtleBot 4.
