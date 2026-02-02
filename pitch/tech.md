# 🚌 Amen Madrasati (Safe School Bus) - Technical Architecture Report

## 1. Executive Summary
**Amen Madrasati** is a cloud-based, multi-tenant IoT platform designed to ensure the safety of school transportation. The system provides real-time GPS tracking, live video surveillance, and automated student attendance logging using RFID technology. It connects Drivers, Parents, and School Administrators through a unified web interface, ensuring total transparency and safety compliance.

---

## 2. High-Level Architecture

The system follows a **Microservices-ready** architecture using Docker containers, orchestrated to handle real-time data streams from mobile devices and IoT sensors.

### 🏗️ The Stack (Technology Choices)
| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend Core** | **Python Flask** | REST API & Logic Handler. |
| **Real-Time Engine** | **Socket.IO / Eventlet** | Bi-directional communication (Phone <-> Server). |
| **IoT Protocol** | **MQTT (Mosquitto/HiveMQ)** | Lightweight messaging for GPS/Sensor hardware. |
| **Database** | **PostgreSQL + PostGIS** | Relational data + Geospatial (Map) queries. |
| **Frontend** | **HTML5 PWA + Leaflet.js** | Responsive Mobile/Web Apps (No App Store needed). |
| **Streaming** | **HLS / WebRTC** | Low-latency video transmission. |
| **Deployment** | **Docker Compose** | Containerized environment for instant portability. |

---

## 3. Hardware Implementation (The "Smart Bus")

We utilize an **"All-in-One" Android Console** approach to minimize wiring and battery risks, integrated with plug-and-play USB peripherals.

### A. The Command Center (Driver Unit)
* **Device:** **Android Dashboard Console (e.g., Phisung K18)** or Android Head Unit.
* **OS:** Android 8.1 / 10.
* **Connectivity:** Built-in **4G LTE SIM Slot** + Wi-Fi.
* **Function:** Runs the *Driver Web App*, acts as the GPS gateway, and displays the route.

### B. Student Attendance (Hands-Free)
* **Device:** **UHF RFID Desktop Reader (USB)**.
* **Mode:** **Keyboard Emulation (HID)**.
* **Integration:** Plugs directly into the Android Console's USB port.
* **Workflow:**
    1.  Student walks onto the bus with a UHF Tag in their bag.
    2.  Reader detects tag (Range: ~1 meter).
    3.  Reader "types" the ID into the hidden input field of the Driver App.
    4.  App sends `BOARDED` status to the server automatically.

### C. Surveillance (Video)
* **Primary:** Built-in **Dual Cameras** on the Android Console (Front Road + Interior Cabin).
* **Protocol:** Apps stream via Android Camera API -> WebRTC/RTMP -> Server.

---

## 4. Data Flow & Communication

### 📡 1. GPS Tracking Loop
1.  **Source:** Driver App accesses `navigator.geolocation` on the Android Console.
2.  **Transport:** Sends `{lat, lng, speed, bus_id}` via **Socket.IO** (WebSocket) every 3 seconds.
3.  **Server:** Python Flask receives data, updates the `buses` database table (PostGIS).
4.  **Broadcast:** Server filters active Parents and emits `update_map` event.
5.  **Destination:** Parent App receives coordinates and animates the bus marker on Leaflet Map.

### 📝 2. Attendance Loop
1.  **Source:** UHF Reader injects Tag ID into Driver App.
2.  **Logic:** App checks previous state (Boarded vs. Dropped).
3.  **Transport:** Emits `student_scan` event via Socket.IO.
4.  **Server:**
    * Logs timestamp in `trip_logs`.
    * Updates `bus_manifest` (Who is on board?).
    * Triggers **Push Notification** to the specific Parent ("Ahmed has boarded Bus 101").

---

## 5. Software Modules (User Interfaces)

### 👨‍💼 Super Admin & School Admin Panel
* **Technology:** Web Dashboard (Jinja2 Templates).
* **Features:**
    * **Fleet Management:** Add/Remove Buses and assign Drivers.
    * **NFC/RFID Management:** Link Tag IDs to Student Profiles.
    * **Live Map:** "God View" of all buses moving simultaneously.

### 🚌 Driver App (PWA)
* **Platform:** Android Web View (Chrome).
* **Features:**
    * **Big Button Interface:** "Start Trip" / "End Trip".
    * **Live Manifest:** Shows list of students currently on board.
    * **Manual Override:** Driver can manually tap a student if they forgot their tag.

### 👨‍👩‍👧‍👦 Parent App (Mobile Web)
* **Platform:** Mobile Browser.
* **Features:**
    * **My Kids Only:** Security filter shows only the logged-in user's children.
    * **Live Tracking:** See bus location *only* when the child is on board.
    * **Status Indicators:** "At School", "On Bus", "Home".

---

## 6. Security & Scalability

1.  **Containerization (Docker):**
    * The entire system (DB, App, Broker) runs in isolated containers.
    * *Benefit:* Can be deployed on AWS, DigitalOcean, or a local server in 1 click.
2.  **Environment Variables:**
    * Credentials (DB passwords, API keys) are never hardcoded; they are injected at runtime.
3.  **SSL/TLS:**
    * All web traffic serves over HTTPS (required for Camera/GPS permissions).
    * MQTT traffic is encrypted (Port 8883) for hardware security.

---

## 7. Future Expansion Roadmap

* **AI Fatigue Detection:** Use the Android Console's front camera to detect if the driver is falling asleep.
* **Route Optimization:** Integrate Google Maps API to suggest faster routes based on traffic.
* **Offline Mode:** Cache GPS data locally if 4G is lost, and sync when reconnected.