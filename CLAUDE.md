# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

**Local (Docker):**
```bash
cp .env.example .env   # fill in DB_PASS and FLASK_SECRET_KEY
docker-compose up --build
```
App available at `http://localhost:5000`. The compose stack starts: PostgreSQL, Mosquitto MQTT, the Flask web process, and the MQTT listener.

**Without Docker (direct):**
```bash
pip install -r requirements.txt
# Set env vars from .env.example, then:
python create_tables.py    # seed DB once
python listener.py &       # MQTT background worker
python web_app.py          # dev server on :5000
```

**Production (Railway):** push to `main` on GitHub — Railway auto-builds via `Dockerfile` and runs `start.sh`, which starts `listener.py` in the background and then `gunicorn --worker-class eventlet -w 1`.

**DB migrations:** `create_tables.py` is idempotent (`IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS`). It runs automatically on the first HTTP request via the `_lazy_migrate` hook in `web_app.py`. Force a re-run as SUPER_ADMIN via `GET /api/force_migrate`.

There is no test suite.

## Architecture

### Two processes, one container

`start.sh` launches both Python processes:
- **`web_app.py`** — Flask + Flask-SocketIO (eventlet), serves all HTTP routes and real-time Socket.IO events. Must run with exactly 1 gunicorn worker (eventlet limitation).
- **`listener.py`** — standalone paho-mqtt loop. Subscribes to `bus/+/+`, handles IoT telemetry (saves to `trip_logs`) and NFC tap events (updates `bus_manifest`). Has no HTTP server and no access to Flask sessions.

### Database

All credentials flow through `db_config.py` → environment variables. `get_db_connection()` in `web_app.py` automatically falls back to the Railway public proxy (`yamabiko.proxy.rlwy.net`) if the internal hostname fails. `listener.py` has its own simpler `get_db()` with no fallback.

Key tables and their purpose:
- `schools` — multi-tenant root; every other entity has a `school_id`
- `users` — all roles share this table; `role` ∈ `{SUPER_ADMIN, SCHOOL_ADMIN, DRIVER, PARENT}`
- `buses` — has `current_lat/lng/speed/last_updated` for live tracking; `driver_id` FK to users
- `students` — `parent_id` FK to users; `nfc_tag_id` maps NFC hardware to student; `lat/lng` is home address
- `route_stops` — one row per student-bus assignment; `lat/lng` copied from `students` at assignment time
- `bus_manifest` — live boarding state; PK is `(bus_id, student_id)`; `status` ∈ `{BOARDED, DROPPED}`
- `trip_logs` — raw GPS history from listener.py

**Critical invariant:** `bus_manifest.student_id` is always the student's UUID primary key (TEXT, cast from SERIAL). `listener.py` resolves NFC tag IDs to student UUIDs via a `SELECT id FROM students WHERE nfc_tag_id = ?` lookup before any `bus_manifest` write. Never write the raw NFC tag string into `bus_manifest.student_id`.

### RBAC

The `@role_required(allowed_roles)` decorator in `web_app.py` guards every route and API. Session keys: `user_id`, `user_role`, `school_id`. SCHOOL_ADMINs can only see and modify data belonging to their own `school_id`. SUPER_ADMIN has global access. Login portals are split: `/login` (admin/school admin), `/driver/login`, `/parent/login`.

### Real-time data flow

```
Driver App  →  socket "driver_gps_update"  →  web_app.py  →  socket "update_map"  → Parent/Admin map
IoT Device  →  MQTT bus/{id}/telemetry    →  listener.py  →  trip_logs DB
IoT NFC     →  MQTT bus/{id}/nfc          →  listener.py  →  bus_manifest DB
Driver App  →  socket "manual_attendance" →  web_app.py  →  bus_manifest DB  →  socket "student_status_update"
Driver App  →  socket "camera_frame"      →  web_app.py  →  socket "bus_camera_frame" → Parent viewer
```

### Templates

| Template | Role | Notes |
|---|---|---|
| `login.html` | SUPER_ADMIN / SCHOOL_ADMIN | |
| `driver_login.html` | DRIVER | |
| `parent_login.html` | PARENT | |
| `school_admin.html` | SCHOOL_ADMIN | Main admin UI, Arabic+English, many API calls |
| `super_admin.html` | SUPER_ADMIN | Multi-school management |
| `driver_app.html` | DRIVER | GPS tracking + NFC attendance + camera stream |
| `parent_dashboard.html` | PARENT | Arabic RTL, child boarding status + live bus map |
| `parent_app.html` | PARENT | Simpler map-only view |
| `tour-select.html` / `*-tour.html` | Public | Marketing/demo pages |

All templates use Leaflet.js for maps, Socket.IO 4.x for real-time, and the Tajawal font for Arabic text.

## Security conventions

**CSRF:** `flask-wtf` `CSRFProtect` is active globally. All `fetch()` POST calls must include the `X-CSRFToken` header — fetch the token once via `GET /api/csrf-token` and store it in `_csrfToken`. HTML form POSTs use a `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` field. Any new JS POST that omits this header will get a 400.

**Rate limits:** Login routes are limited to 5/minute. All write POST API endpoints are limited to 30/minute via `@limiter.limit("30 per minute")` placed between `@app.route` and `@role_required`.

**Error responses:** Never return `str(e)` or exception detail to the client. Use `"Internal server error"` for 500s; log detail server-side with `print(f"Error ...: {e}")`.

**Socket auth:** All socket event handlers that mutate state check `session.get('user_role')` at the top and return early if the role is wrong. Do not rely on connection-time auth alone.

**Input validation:** Use `data.get('key', '')` (never `data['key']`) on `request.json`. Return 400 for missing required fields before touching the DB.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `DB_PASS` | Yes | App refuses to start without it |
| `FLASK_SECRET_KEY` | Yes (prod) | Random fallback invalidates sessions on restart |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PORT` | No | Have Railway-targeting defaults in `db_config.py` |
| `MQTT_BROKER`, `MQTT_USER`, `MQTT_PASS` | No | Listener only; defaults to `localhost:1883` |
| `CORS_ORIGINS` | No | Comma-separated; empty = same-origin only |
| `RENDER` | No | Set to any value to enable `SESSION_COOKIE_SECURE` and MQTT TLS |
