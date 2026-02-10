# 🚌 آمن مدرستي - Bus GPS System

**Safe School Transport Tracking System**

A comprehensive, real-time school bus tracking system designed to ensure student safety and provide peace of mind for parents and school administrators.

---

## 🌟 Key Features

### 📍 Real-Time Tracking
- **Live Map:** Parents and admins can see buses moving in real-time on a map.
- **Speed Monitoring:** Tracks bus speed and alerts on over-speeding.
- **Geofencing:** (Planned) Alerts when buses enter/exit school zones.

### 📹 Live Streaming
- **In-Bus Cameras:** Authorized parents and admins can view live video feeds from inside the bus.
- **Secure Access:** Video streams are protected and only accessible to relevant users.

### 📝 Smart Attendance (NFC)
- **Tap On/Off:** Students tap their NFC cards when boarding and leaving.
- **Instant Notifications:** Parents receive instant alerts: *"Ahmed has boarded the bus at 7:30 AM"*.
- **Manifest:** Drivers have a live list of who is on board.

### 🔐 Role-Based Access
- **Super Admin:** Full system control options.
- **School Admin:** Manages their specific school, buses, and students.
- **Driver:** Mobile app for navigation and attendance.
- **Parent:** View their children's bus and receive alerts.

---

## 🛠️ Technology Stack

- **Backend:** Python (Flask), Socket.IO (Real-time updates)
- **Database:** PostgreSQL (with PostGIS for location data)
- **IoT/Messaging:** MQTT (HiveMQ) for vehicle telemetry
- **Frontend:** HTML5, CSS3, JavaScript (Leaflet.js for maps)
- **Deployment:** Docker, Railway

---

## 📚 Documentation

Detailed documentation is available in the `docs/` folder:

- [📖 **Database Schema**](docs/database.md) - Tables, relationships, and data models.
- [🔌 **API Reference**](docs/api.md) - Endpoints for developers.
- [🏗️ **System Architecture**](docs/architecture.md) - High-level design and data flow.
- [🚀 **Deployment Guide**](docs/deployment.md) - How to run locally or in the cloud.

---

## 🚀 Quick Start (Local)

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/mhndayesh/bus-gps-system.git
    cd bus-gps-system
    ```

2.  **Start with Docker:**
    ```bash
    docker-compose up --build
    ```

3.  **Access the App:**
    - Web Interface: `http://localhost:5000`
    - Admin Login: `admin` / `admin123` (Default)

---

## 🛡️ Security

This project implements:
- **RBAC:** Strict Role-Based Access Control.
- **Password Hashing:** PBKDF2-SHA256 encryption.
- **Secure Sessions:** HttpOnly, Secure cookies.
- **CORS:** Restricted API access.

---

*Verified by Antigravity AI*
