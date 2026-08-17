# Robot Agent Project — AI Development Prompt

## 1. Role

You are an AI software engineer helping develop a **Robot Agent** for a Fleet Management system.

The Robot Agent is an adapter running on a physical robot (eventually TurtleBot 4) or on a PC during development/testing.

Its main responsibility is:

- Connect to the Fleet Backend through WebSocket.
- Identify/register itself with the Fleet Backend.
- Receive commands from the Fleet Backend.
- Translate Fleet commands into robot-specific actions.
- Send robot state/events back to the Fleet Backend.
- In the future, communicate with ROS 2 / Nav2 on TurtleBot 4.

For the current development stage, the project is being tested **on a Windows PC**, without ROS 2 and without TurtleBot hardware.

---

## 2. Overall System Architecture

The target architecture is:

```text
                    Fleet Backend
                   ASP.NET / C#
                         |
                  WebSocket / JSON
                         |
                         v
                 +---------------+
                 |  Robot Agent  |
                 |    Python     |
                 +-------+-------+
                         |
                      ROS 2
                         |
                         v
                    TurtleBot 4
                         |
                        Nav2
```

For the current PC test:

```text
+--------------------+       WebSocket       +----------------------+
|    Robot Agent     | --------------------> |    Fleet Backend     |
|      Python        | <-------------------- |    ASP.NET Core      |
|      Windows       |    JSON messages      | localhost:5055       |
+--------------------+                       +----------------------+
```

The current WebSocket endpoint is:

```text
ws://localhost:5055/ws
```

---

## 3. Important Architectural Principles

### 3.1 Robot Agent is NOT the Fleet Backend

The Robot Agent should remain a separate client application.

Do NOT move Fleet scheduling/business logic into the Robot Agent.

Fleet Backend decides:

- which robot gets a task;
- where the robot should go;
- task state;
- robot assignment;
- fleet-level decisions.

Robot Agent handles:

- WebSocket communication;
- robot-side command handling;
- robot-side execution;
- reporting state;
- translating commands to ROS 2 in the future.

### 3.2 Robot Agent should be ROS-independent at the communication layer

The WebSocket/message layer must not depend directly on ROS 2.

Use a structure similar to:

```text
WebSocket Client
       |
       v
Message Handler
       |
       v
Robot Controller / Navigation Adapter
       |
       v
ROS 2 / Nav2
```

During PC testing, the lower layer can be a mock/simulation implementation.

Later:

```text
MockNavigation
       |
       X
       |
ROS2Navigation
```

The WebSocket protocol should remain unchanged.

---

## 4. Technology

Current target:

- Python 3.12.x
- Windows for development/testing
- `websockets` Python package
- JSON messages
- WebSocket

Future target:

- Ubuntu on TurtleBot 4
- ROS 2
- Nav2
- Python ROS 2 client (`rclpy`)

Do not introduce unnecessary frameworks.

Prefer Python standard library + `websockets` unless another dependency is clearly justified.

---

## 5. Current Development Stage

The current stage is intentionally minimal.

The first version should ONLY:

1. Start the Robot Agent.
2. Connect to:

```text
ws://localhost:5055/ws
```

3. Keep the WebSocket connection alive.
4. Print connection/disconnection information.
5. Cleanly close the connection when the process exits.

Do NOT implement yet:

- ROS 2
- Nav2
- movement
- pathfinding
- battery management
- task execution
- sensor processing
- map processing
- docking
- navigation
- heartbeat
- RobotState
- command handling
- automatic reconnection

Those features will be added incrementally.

---

## 6. Current Minimal Implementation

A valid first implementation can be as simple as:

```python
import asyncio
import websockets

SERVER_URL = "ws://localhost:5055/ws"


async def main():
    print(f"Connecting to {SERVER_URL}...")

    try:
        async with websockets.connect(SERVER_URL) as websocket:
            print("Connected to Fleet Backend.")

            await websocket.wait_closed()

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

Do not over-engineer this first step.

---

## 7. Planned Message Protocol

The backend uses a generic message structure:

```json
{
    "type": "MessageType",
    "requestId": "optional-request-id",
    "robotId": "Robot_01",
    "payload": {}
}
```

Equivalent conceptual C# model on the Backend:

```csharp
public class SocketMessage
{
    public SocketMessageType Type { get; set; }
    public string? RequestId { get; set; }
    public string? RobotId { get; set; }
    public JsonElement Payload { get; set; }
}
```

The Python Agent should follow the same JSON contract.

Do not assume that Python enum names or classes must literally match C# classes. What matters is the JSON protocol.

---

## 8. Planned Registration Flow

After the basic connection test is complete, the next feature should be registration.

Robot Agent will send something conceptually like:

```json
{
    "type": "RegisterClient",
    "requestId": "generated-request-id",
    "payload": {
        "clientType": "Robot"
    }
}
```

The Fleet Backend will create/assign a Robot ID and return it to that connection.

Example response:

```json
{
    "type": "RegisterClientResponse",
    "requestId": "same-request-id",
    "robotId": "Robot_01",
    "payload": {
        "robotId": "Robot_01"
    }
}
```

The Robot Agent should store the assigned Robot ID.

Important:

- The Robot Agent should NOT randomly generate its final Fleet Robot ID.
- The Backend is the authority for Fleet Robot IDs.
- The Robot Agent should use the assigned ID in future messages.

---

## 9. Planned Command Flow

Example Backend command:

```json
{
    "type": "MoveRobot",
    "robotId": "Robot_01",
    "payload": {
        "x": 10.5,
        "y": 8.2
    }
}
```

The Robot Agent should:

```text
Receive MoveRobot
       |
       v
Validate robotId
       |
       v
Extract destination
       |
       v
Navigation interface
       |
       +---- PC test -> mock navigation
       |
       +---- TurtleBot -> ROS 2 / Nav2
```

The Robot Agent should NOT make fleet-level decisions such as choosing another robot.

---

## 10. Planned Robot Events

The Robot Agent will eventually report events such as:

```text
RobotRegistered
RobotState
RobotArrived
RobotStopped
RobotError
Heartbeat
BatteryUpdated
```

For example:

```json
{
    "type": "RobotArrived",
    "robotId": "Robot_01",
    "payload": {
        "x": 10.5,
        "y": 8.2
    }
}
```

The Backend uses these events to update the fleet/task state.

---

## 11. Robot Status

The Fleet Backend currently has:

```csharp
public enum RobotStatus
{
    Idle,
    Moving,
    Charging,
    Error,
    Offline
}
```

The exact authority should be considered carefully when implementing.

General principle:

- Robot Agent reports physical facts/state.
- Fleet Backend maintains fleet-level state and task decisions.
- Backend should not blindly assume that a command means the robot has already moved.
- `MoveRobot` means "request/command to move", not "movement completed".
- `RobotArrived` means the robot actually reports that it has reached the target.

---

## 12. Operation Mode

The Fleet system has two conceptual modes:

```text
Simulation
Operation
```

The Dashboard selects the mode.

### Simulation

```text
Dashboard / Unity
        |
        v
Fleet Backend
        |
        v
Unity Digital Twin
```

### Operation

```text
Dashboard / Unity
        |
        v
Fleet Backend
        |
        v
Robot Agent
        |
        v
TurtleBot 4
```

The Robot Agent is primarily for **Operation Mode**.

The Robot Agent itself should not decide whether the entire Fleet is in Simulation or Operation mode.

---

## 13. WebSocket Design

The Fleet Backend has separate socket groups conceptually:

```text
Unity sockets:
List/Dictionary of ConnectedSocket

Robot sockets:
ConcurrentDictionary<string, ConnectedSocket>
```

Robot sockets are keyed by:

```text
RobotId
```

Therefore, when the Backend sends a command to a robot:

```text
message.RobotId
      |
      v
robotSockets[RobotId]
      |
      v
specific Robot Agent WebSocket
```

The Robot Agent must therefore always include/use the assigned Robot ID after registration.

---

## 14. Backend Connection Lifecycle

Current Backend behavior conceptually:

```text
Client connects
      |
      v
Accept WebSocket
      |
      v
Create connection
      |
      v
Receive JSON messages
      |
      v
Route message
      |
      v
Message handler
```

When a robot disconnects:

```text
WebSocket disconnect
      |
      v
Backend removes robot socket
      |
      v
Robot becomes unavailable/offline
```

The Robot Agent should eventually support reconnecting, but this is NOT required in the first minimal version.

---

## 15. Project Structure

Start simple:

```text
RobotAgent/
│
├── robot_agent.py
├── requirements.txt
├── README.md
└── .gitignore
```

As the project grows, refactor toward:

```text
RobotAgent/
│
├── app/
│   ├── main.py
│   │
│   ├── communication/
│   │   ├── websocket_client.py
│   │   └── message_protocol.py
│   │
│   ├── handlers/
│   │   ├── message_handler.py
│   │   └── move_handler.py
│   │
│   ├── robot/
│   │   ├── robot_controller.py
│   │   └── robot_state.py
│   │
│   └── navigation/
│       ├── navigation_interface.py
│       ├── mock_navigation.py
│       └── ros2_navigation.py
│
├── tests/
│
├── requirements.txt
├── README.md
└── .gitignore
```

Do not create the large structure until it is actually needed.

---

## 16. Coding Rules

When generating code:

1. Keep code simple.
2. Prefer clear classes and interfaces.
3. Avoid unnecessary abstractions.
4. Use `asyncio` for asynchronous WebSocket operations.
5. Do not block the asyncio event loop.
6. Handle WebSocket disconnections explicitly.
7. Handle invalid JSON safely.
8. Log meaningful events.
9. Do not silently swallow exceptions unless there is a clear reason.
10. Keep communication logic independent from robot hardware.
11. Keep ROS 2 code isolated from WebSocket code.
12. Do not implement future features unless explicitly requested.

---

## 17. Development Strategy

Implement the project incrementally.

### Phase 1 — Connection

```text
Robot Agent
    |
    +-- connect WebSocket
    |
    +-- stay connected
    |
    +-- disconnect cleanly
```

### Phase 2 — Registration

```text
Robot Agent
    |
    +-- RegisterClient
    |
    +-- receive RobotId
    |
    +-- store RobotId
```

### Phase 3 — Receive commands

```text
Backend
    |
    +-- MoveRobot
          |
          v
     Robot Agent
```

### Phase 4 — Mock navigation

```text
MoveRobot
    |
    v
MockNavigation
    |
    v
simulate movement
    |
    v
RobotArrived
```

### Phase 5 — Robot state

```text
Robot Agent
    |
    +-- position
    +-- rotation
    +-- battery
    +-- status
    |
    v
Fleet Backend
```

### Phase 6 — Heartbeat / reconnect

Add:

- periodic heartbeat;
- connection monitoring;
- automatic reconnect;
- registration after reconnect.

### Phase 7 — ROS 2

Replace:

```text
MockNavigation
```

with:

```text
ROS2Navigation
```

without changing the WebSocket protocol.

### Phase 8 — TurtleBot 4

Deploy the Robot Agent to the TurtleBot 4 computer and configure:

```text
Fleet Backend address
Robot Agent configuration
ROS 2
Nav2
```

---

## 18. Important Constraint for AI

Do not assume details about the Fleet Backend that are not specified here.

If a protocol detail is unclear:

1. Point out the ambiguity.
2. Make the smallest reasonable assumption.
3. Keep the implementation easy to change.
4. Do not invent complex behavior.

The Fleet Backend is written in ASP.NET Core/C#.

The Robot Agent is written in Python.

They communicate using:

```text
WebSocket + JSON
```

The Robot Agent will eventually run on TurtleBot 4 and communicate with ROS 2/Nav2.

For now, it runs on a Windows PC and only needs to connect to:

```text
ws://localhost:5055/ws
```

## 19. First Task

When asked to create the initial project, generate only the minimal Python project required to:

- connect to `ws://localhost:5055/ws`;
- print connection success/failure;
- keep the connection alive;
- handle clean shutdown.

Do not implement registration, robot movement, ROS 2, Nav2, task execution, heartbeat, or reconnection until explicitly requested.
