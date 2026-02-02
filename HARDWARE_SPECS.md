# 🚌 آمن مدرستي - Technical Specifications for Hardware Integration
# School Bus GPS Tracking System - Hardware Requirements

---

## 📋 System Overview

This document explains the technologies, protocols, and methods used in the "آمن مدرستي" school bus tracking system to help hardware engineers select compatible GPS devices and cameras.

---

## 🛰️ GPS Tracking

### Current Implementation
The system receives GPS coordinates via two methods:

#### Method 1: Driver's Smartphone (Current)
- Uses HTML5 Geolocation API (`navigator.geolocation`)
- Broadcasts via WebSocket (Socket.IO)
- Data format: `{ bus_id, lat, lng, speed }`
- Update frequency: Real-time (as fast as phone updates)

#### Method 2: MQTT Protocol (For Dedicated Devices)
- **Protocol:** MQTT 3.1.1 / MQTT 5.0
- **Broker:** HiveMQ Cloud (can use any MQTT broker)
- **Topic:** `school/buses/gps`
- **Port:** 8883 (TLS/SSL) or 1883 (non-TLS)
- **Authentication:** Username/Password

### GPS Device Requirements
| Requirement | Specification |
|-------------|---------------|
| **Protocol** | MQTT (preferred) or HTTP POST |
| **Data Format** | JSON |
| **Minimum Fields** | `bus_id`, `lat`, `lng` |
| **Optional Fields** | `speed`, `heading`, `timestamp`, `accuracy` |
| **Connectivity** | 4G/LTE cellular data |
| **Update Rate** | 1-5 seconds recommended |

### Compatible GPS Trackers
Any GPS tracker that supports MQTT publishing can integrate:
- **Queclink** GL300/GL500 series (with MQTT firmware)
- **Teltonika** FMB series (via MQTT gateway)
- **Custom ESP32/Arduino** with SIM800L/SIM7600 + GPS module
- **Raspberry Pi** with GPS HAT + cellular modem

### Expected JSON Payload
```json
{
    "bus_id": "BUS001",
    "lat": 21.5433,
    "lng": 39.1728,
    "speed": 45,
    "heading": 180,
    "timestamp": 1706814000
}
```

---

## 📹 Camera Streaming

### Current Implementation: Phone Camera via WebSocket
The driver app uses the phone's camera to stream live video.

| Specification | Value |
|---------------|-------|
| **Method** | WebSocket frames (JPEG) |
| **Resolution** | 640x480 pixels |
| **Frame Rate** | 10 FPS (100ms intervals) |
| **Quality** | 60% JPEG compression |
| **Camera** | Front or back (switchable) |
| **Protocol** | Socket.IO (WebSocket) |

### How It Works
1. Driver presses "Start Streaming" button
2. Phone captures frames using `getUserMedia()` API
3. Each frame is converted to Base64 JPEG
4. Frames are sent via WebSocket to server
5. Server broadcasts to admin viewers
6. Viewers receive and display frames as live video

### Alternative: Dedicated IP Cameras (HLS Stream)
The system also supports traditional IP cameras via HLS:

| Specification | Value |
|---------------|-------|
| **Protocol** | HLS (HTTP Live Streaming) |
| **Format** | .m3u8 playlist |
| **Video Codec** | H.264 |
| **Resolution** | 720p or 1080p |
| **Latency** | 5-15 seconds |

### Compatible Camera Options

#### Option A: Phone Camera (Current - No Extra Hardware)
- ✅ Uses driver's smartphone
- ✅ No additional cost
- ✅ Front/back camera switching
- ⚠️ Depends on phone quality
- ⚠️ Uses driver's mobile data

#### Option B: 4G Wireless Cameras
- **Wyze Cam Outdoor** + 4G router
- **Reolink Go** (built-in 4G)
- **Eufy 4G LTE Cam**
- Requires: Static IP or DDNS for HLS access

#### Option C: Vehicle DVR with Live Streaming
- **Blackvue DR900X** (Cloud streaming)
- **Thinkware U1000** (WiFi + mobile hotspot)
- Professional fleet cameras with cellular module

#### Option D: Custom Setup
- Raspberry Pi + Camera Module + 4G dongle
- Stream via RTSP → Convert to HLS
- Requires technical setup

---

## 🔌 Communication Protocols

### WebSocket (Primary - Real-time)
- **Library:** Socket.IO
- **Transport:** WebSocket with HTTP fallback
- **Port:** 443 (HTTPS) or 80 (HTTP)
- **Events:**
  - `driver_gps_update` - GPS coordinates
  - `camera_frame` - Video frames
  - `update_map` - Map updates to viewers

### MQTT (For IoT Devices)
- **Broker:** HiveMQ Cloud
- **Security:** TLS 1.2+
- **QoS:** 0 or 1
- **Topics:**
  - `school/buses/gps` - GPS data
  - `school/buses/status` - Bus status

### HTTP REST API
- **Endpoints:** Various `/api/*` routes
- **Format:** JSON
- **Auth:** Session-based cookies

---

## 📱 Client Requirements

### Driver Device
| Requirement | Minimum |
|-------------|---------|
| **Device** | Android 8+ or iOS 12+ |
| **Browser** | Chrome/Safari (modern) |
| **Internet** | 4G LTE recommended |
| **GPS** | Built-in GPS required |
| **Camera** | For live streaming |

### Parent Device
| Requirement | Minimum |
|-------------|---------|
| **Device** | Any smartphone/tablet/PC |
| **Browser** | Any modern browser |
| **Internet** | 3G minimum |

---

## 🏗️ Server Infrastructure

### Current Deployment
| Component | Technology |
|-----------|------------|
| **Backend** | Python Flask + Flask-SocketIO |
| **Database** | PostgreSQL (with PostGIS extension) |
| **Hosting** | Railway.app (Cloud) |
| **Real-time** | Socket.IO (WebSocket) |
| **MQTT** | HiveMQ Cloud Broker |

### Key Libraries
- `flask` - Web framework
- `flask-socketio` - WebSocket support
- `paho-mqtt` - MQTT client
- `psycopg2` - PostgreSQL driver
- `eventlet` - Async support

---

## 🔧 Integration Options for Hardware Team

### Scenario 1: Simple Setup (Phone Only)
- Driver uses smartphone for GPS + Camera
- No additional hardware needed
- Lowest cost option

### Scenario 2: Dedicated GPS + Phone Camera
- GPS Tracker (MQTT-capable) mounted in bus
- Driver phone for camera only
- More reliable GPS tracking

### Scenario 3: Full Hardware Setup
- Dedicated GPS tracker (MQTT)
- 4G IP camera with HLS streaming
- Driver app for attendance only
- Most reliable, highest cost

---

## 📞 Contact for Integration
For technical integration questions, contact the development team.

---

*Document Version: 1.3*
*Last Updated: 2026-02-01*
