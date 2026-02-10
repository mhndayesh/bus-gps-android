# 🏗️ System Architecture

## High-Level Overview

```mermaid
graph TD
    User[Users<br>(Parent, Admin)] -->|HTTPS/WSS| WebApp[Flask Web App]
    Driver[Driver App] -->|GPS Data| MQTT[MQTT Broker<br>(HiveMQ)]
    Driver -->|REST API| WebApp

    MQTT -->|Subscribe| WebApp
    WebApp -->|Store Data| DB[(PostgreSQL + PostGIS)]
    WebApp -->|Real-time Updates| User
```

---

## 🧩 Components

### 1. Web Application (Flask)
- **Role:** Central hub for data processing, API, and UI delivery.
- **Tech:** Python, Flask, Flask-SocketIO.
- **Functions:**
    - Serves HTML Dashboard.
    - Manages User Sessions (RBAC).
    - Processes API requests.
    - Bridges MQTT data to WebSocket clients.

### 2. Database (PostgreSQL + PostGIS)
- **Role:** Persistent storage for all system data.
- **Tech:** PostgreSQL 14, PostGIS extension.
- **Functions:**
    - Stores Users, Schools, Students, Buses.
    - Stores Geospatial data (Location points).
    - Logs historical trip data.

### 3. Messaging Broker (HiveMQ / Mosquitto)
- **Role:** High-speed telemetry ingestion.
- **Tech:** MQTT Protocol.
- **Functions:**
    - Receives GPS coordinates from buses (every 1-5 seconds).
    - Decouples ingestion from processing (Scalability).

### 4. Frontend (Client-Side)
- **Role:** User Interface.
- **Tech:** HTML5, CSS3, Vanilla JS, Leaflet.js.
- **Functions:**
    - **Map:** Renders bus locations on OpenStreetMap tiles.
    - **Socket.IO Client:** Receives live updates without refreshing.

---

## 🔄 Data Flow

### Scenario: Bus Moves
1.  **Bus (Driver App)** gets GPS coordinates.
2.  **Driver App** publishes to MQTT topic `bus/{id}/telemetry`.
3.  **Flask App** (MQTT Listener) receives the message.
4.  **Flask App** emits `update_map` event via **Socket.IO**.
5.  **Parent's Browser** receives event and moves the bus icon on map.

### Scenario: Student Boards
1.  **Student** taps NFC card on Driver App.
2.  **Driver App** sends POST request to `/api/attendance`.
3.  **Flask App** validates NFC ID and updates `bus_manifest` table.
4.  **Flask App** emits `student_status_update` event via **Socket.IO**.
5.  **Parent's Phone** receives notification: "Ahmed Boarded".
