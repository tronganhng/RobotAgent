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

Set the ROS namespace separately for each robot (defaults to `robot3`):

```bash
# On robot 1
python -m app.main ws://10.11.57.157:5055/ws --robot-namespace robot1

# On robot 2
python -m app.main ws://10.11.57.157:5055/ws --robot-namespace robot2
```

The namespace must match the robot's existing ROS topics and actions. This option
selects the endpoints the agent connects to; it does not rename the robot's ROS
stack. Leading/trailing slashes are removed, and nested namespaces such as
`warehouse/robot1` are supported. The backend assigns `RobotId` independently.
The root wrapper accepts the same arguments.

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

## ChangeRobotFloor protocol

The agent accepts `ChangeRobotFloor` for its assigned `RobotId`, with a nonempty
`RequestId` and payload `{ "ElevatorId": "Elevator_01", "TargetFloor": 2 }`.
PascalCase and camelCase field names are accepted. Invalid or incorrectly
addressed requests are ignored. The agent cancels active motion, calls
`navigation.change_floor(elevator_id, target_floor)`, and sends `RobotFloorReady`
with the original `RequestId` and `RobotId`. Its payload echoes `ElevatorId` and
`TargetFloor`, with `IsReady` and optional `ErrorMessage`.

`Floor` is updated in telemetry only after navigation reports readiness. A
failure or the 100-second local deadline produces `IsReady: false` and sets the
robot status to `Error`. The backend readiness timeout must exceed this local
deadline (the backend default is 120 seconds).

`MockNavigation` simulates floor readiness. ROS2 navigation now uses
`FloorMapChanger` automatically when a ROS node is supplied. The implementation
follows `elevator_manager`'s `switch_map()` and
`initialize_amcl_at_parking_pose()` sequence:

1. Validate the requested elevator/floor in `config/elevator.yaml`.
2. Call `/<namespace>/map_server/load_map` with that floor's `map_file` and
   require a successful response (`result == 0`).
3. Wait one second for the map, then publish `PoseWithCovarianceStamped` to
   `/<namespace>/initialpose` five times, 0.3 seconds apart. The pose uses the
   destination floor's cabin `parking_pose`, in the `map` frame; yaw is radians.
   Initial covariance matches the reference (x/y: 0.04, yaw: 0.03046).
4. Wait for new `/<namespace>/amcl_pose` messages generated after initialization.
   Require position within 0.75 m and yaw within 20 degrees of the cabin pose,
   stable for one second plus a five-second settling period. Samples older than
   two seconds, old ROS timestamps, invalid coordinates and other frames cannot
   establish readiness. When available, `/<namespace>/request_nomotion_update`
   is called every 0.5 seconds so AMCL can update while the robot stays still.
5. Only then return `True`; the existing handler updates `Floor` and sends
   `RobotFloorReady`. Service/load/localization timeouts are 10/20/25 seconds,
   within the handler's overall 100-second deadline (including motion cancel).

The default config copies the map paths and parking coordinates from the local
`elevator_manager` project: floor 1 uses `/home/khai/Map_turtlebot/map4.yaml` and
floor 2 uses `/home/khai/Map_turtlebot/map5.yaml`. Verify these paths on the map
server and calibrate the cabin poses before running on hardware. The robot must
still be stationary at the cabin parking pose when Fleet requests the change.
AMCL must accept replacement maps (`first_map_only: false` on Nav2 versions
that expose this parameter). Nav2 map server, AMCL, scans and TF must be active.
No map files are bundled here; the paths identify maps on the robot.

Install dependencies and select a deployment config:

```bash
python -m pip install -r requirements.txt
python robot_agent.py --robot-namespace robot3 --floor-config config/elevator.yaml
```

The YAML format is:

```yaml
elevator_id: Elevator_01
floor_2:
  map_file: /robot/maps/floor2.yaml
  parking_pose: {x: 3.0, y: 4.0, yaw: 1.0}
```

Only Fleet sends physical elevator commands. The map changer neither subscribes
to elevator MQTT nor commands the doors or robot exit. Failures/cancellation do
not undo a map already loaded; the handler reports failure and Fleet retains its
recovery flow. ROS operations use asynchronous polling alongside the existing
executor thread, so telemetry continues while map preparation runs.

Custom deployments can still inject an async `floor_changer` into
`ROS2Navigation`; it takes precedence over the built-in implementation. A facade
created with injected clients and no ROS node still requires an explicit floor
adapter. The incoming command handler serializes messages during floor changes;
repeated request IDs are not deduplicated by the agent.
