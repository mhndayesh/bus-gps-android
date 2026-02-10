# 🔌 API Reference

## Base URL
- Local: `http://localhost:5000`
- Production: `https://your-app.railway.app`

---

## 🔐 Authentication

### Admin Login
**POST** `/login`
- **Body:** `{ "username": "admin", "password": "..." }`
- **Response:** 200 OK (Redirects to Dashboard)

### Driver Login
**POST** `/driver/login`
- **Body:** `{ "username": "driver", "password": "..." }`
- **Response:** 200 OK (Redirects to Driver App)

### Parent Login
**POST** `/parent/login`
- **Body:** `{ "username": "parent", "password": "..." }`
- **Response:** 200 OK (Redirects to Parent Dashboard)

---

## 👥 User Management (Admin Only)

### Add Student
**POST** `/api/add_student`
- **Role Required:** `SUPER_ADMIN`, `SCHOOL_ADMIN`
- **Body:**
  ```json
  {
    "name": "Ahmed Ali",
    "student_code": "STU-001", 
    "latitude": 24.7136,
    "longitude": 46.6753,
    "parent_name": "Ali Hassan",
    "nfc_tag_id": "TAG-12345",
    "school_id": 1  // Required for Super Admin
  }
  ```

### Create Driver
**POST** `/api/create_driver`
- **Role Required:** `SUPER_ADMIN`, `SCHOOL_ADMIN`
- **Body:**
  ```json
  {
    "username": "driver_ahmed",
    "password": "securePass123",
    "school_id": 1
  }
  ```

### Create Parent
**POST** `/api/create_parent`
- **Role Required:** `SUPER_ADMIN`, `SCHOOL_ADMIN`
- **Body:**
  ```json
  {
    "name": "Parent Name",
    "username": "parent_user",
    "password": "securePass123",
    "school_id": 1
  }
  ```

### Update Student Location
**POST** `/api/update_student_location`
- **Role Required:** `SUPER_ADMIN`, `SCHOOL_ADMIN`
- **Body:**
  ```json
  {
    "student_id": "123",
    "lat": 24.7136,
    "lng": 46.6753
  }
  ```

---

## 🚌 Fleet Management

### Add Bus
**POST** `/api/add_bus`
- **Body:** `{ "plate_number": "ABC-123", "school_id": 1 }`

### Assign Bus to Student (Stop)
**POST** `/api/assign_bus`
- **Body:** `{ "student_id": "123", "bus_id": "5" }`

### Assign Driver to Bus
**POST** `/api/assign_driver`
- **Body:** `{ "driver_id": "uuid-...", "bus_id": "5" }`

---

## 📡 Live Tracking (Socket.IO)

### Events Emitted (Server → Client)

1.  **`update_map`**
    - Payload: `{ "bus_id": 5, "lat": 24.7..., "lng": 46.6..., "speed": 45 }`
    - Trigger: Whenever a bus moves.

2.  **`student_status_update`**
    - Payload: `{ "student_id": "123", "status": "BOARDED" }`
    - Trigger: NFC Tap.

3.  **`bus_stream_status`**
    - Payload: `{ "bus_id": 5, "streaming": true }`
    - Trigger: Driver starts camera.

### Events Received (Client → Server)

1.  **`driver_gps_update`**
    - Source: Driver App
    - Payload: `{ "bus_id": 5, "lat": ..., "lng": ... }`

2.  **`manual_attendance`**
    - Source: Driver App (Manual Tap)
    - Payload: `{ "student_id": "123", "status": "BOARDED", "bus_id": 5 }`
