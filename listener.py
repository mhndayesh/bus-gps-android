import json
import os
import ssl
import time
import math

import paho.mqtt.client as mqtt
import psycopg2

# Database credentials come from the single source of truth (db_config), which
# requires DB_PASS and targets the Railway proxy by default. This keeps the
# listener pointed at the SAME database as the web app (no divergent host/port
# and no insecure "password" fallback).
from db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# --- CONFIGURATION (CLOUD vs LOCAL) ---
# Production is detected via common platform signals (Railway/Render) or an
# explicit PRODUCTION flag — not a single Render-only var — so TLS isn't
# silently disabled on Railway. Individual MQTT settings can still be overridden.
_IS_PRODUCTION = any(os.environ.get(v) for v in
                     ('RENDER', 'RAILWAY_ENVIRONMENT', 'RAILWAY_PROJECT_ID', 'PRODUCTION'))

if _IS_PRODUCTION:
    print("☁️ Listener: Cloud Mode")
    MQTT_BROKER = os.environ.get("MQTT_BROKER")
    MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASS = os.environ.get("MQTT_PASS")
    USE_SSL = os.environ.get("MQTT_TLS", "true").lower() != "false"
else:
    print("💻 Listener: Local Mode")
    MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
    MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASS = os.environ.get("MQTT_PASS")
    USE_SSL = os.environ.get("MQTT_TLS", "false").lower() == "true"


# --- DATABASE HELPERS ---
def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
    )


def _resolve_bus_id(raw):
    """Map an MQTT topic segment to the numeric buses.id.

    Devices may publish either the numeric bus id or their iot_device_id. A
    numeric segment is used directly; otherwise we look it up by iot_device_id.
    Returns an int bus id, or None if it can't be resolved.
    """
    if raw is None:
        return None
    s = str(raw)
    if s.isdigit():
        return int(s)
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM buses WHERE iot_device_id = %s", (s,))
        row = cur.fetchone()
        return int(row[0]) if row else None
    except Exception as e:
        print(f"bus id resolve error: {e}")
        return None
    finally:
        if cur: cur.close()
        if conn: conn.close()


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# 1. Handle NFC Taps (Boarding/Exiting)
def handle_nfc_event(client, bus_id, nfc_id, event_type):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()

        # Resolve NFC tag to the student's primary key so bus_manifest.student_id
        # is always a student UUID, consistent with manual attendance entries.
        cur.execute("SELECT id, name FROM students WHERE nfc_tag_id = %s", (nfc_id,))
        student_row = cur.fetchone()
        if not student_row:
            print(f"⚠️ NFC tag {nfc_id} not linked to any student — ignoring")
            return
        student_id = str(student_row[0])
        student_name = student_row[1]

        if event_type == "BOARDING":
            print(f"🔵 Student {student_name} ({student_id}) BOARDED Bus {bus_id}")
            cur.execute("""
                INSERT INTO bus_manifest (bus_id, student_id, student_name, status)
                VALUES (%s, %s, %s, 'BOARDED')
                ON CONFLICT (bus_id, student_id)
                DO UPDATE SET status = 'BOARDED', timestamp = NOW()
            """, (bus_id, student_id, student_name))
        elif event_type == "DROPOFF":
            print(f"🟢 Student {student_name} ({student_id}) LEFT Bus {bus_id}")
            cur.execute("""
                UPDATE bus_manifest SET status = 'DROPPED', timestamp = NOW()
                WHERE bus_id = %s AND student_id = %s
            """, (bus_id, student_id))
        else:
            print(f"⚠️ Unknown NFC event type: {event_type!r} — ignoring")
            return

        conn.commit()
    except Exception as e:
        print(f"Error handling NFC event: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()


# 2. The "No-Skip" Safety Check
def check_safety_logic(client, bus_id, lat, lng):
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT stop_name, assigned_student_id, lat, lng FROM route_stops WHERE bus_id = %s", (bus_id,))
        stops = cur.fetchall()

        nearby_stop = None
        for s in stops:
            s_name, s_student, s_lat, s_lng = s
            if s_lat is None or s_lng is None:
                continue
            if haversine(lat, lng, s_lat, s_lng) <= 50:  # 50 meters
                nearby_stop = (s_name, s_student)
                break

        if nearby_stop:
            stop_name, student_target = nearby_stop
            cur.execute("SELECT 1 FROM bus_manifest WHERE bus_id = %s AND student_id = %s AND status = 'BOARDED'",
                        (bus_id, student_target))
            if cur.fetchone():
                message = f"⚠️  ALERT: Bus is at {stop_name}. Ensure Student {student_target} gets off!"
                print(message)
                alert_payload = json.dumps({"type": "ALERT", "msg": f"DROP OFF {student_target} NOW!"})
                client.publish(f"bus/{bus_id}/alerts", alert_payload)
    except Exception as e:
        print(f"Error in safety logic: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- MQTT HANDLERS ---
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe("bus/+/+")  # Listen to EVERYTHING (telemetry and nfc)


def on_disconnect(client, userdata, *args):
    # paho passes different arg counts across versions; accept them all.
    print("⚠️ MQTT disconnected — paho will attempt to reconnect…")


def on_message(client, userdata, msg):
    conn = None
    cur = None
    try:
        payload = json.loads(msg.payload.decode())
        if not isinstance(payload, dict):
            print("⚠️ Ignoring non-object MQTT payload")
            return

        topic_parts = msg.topic.split("/")
        if len(topic_parts) < 3:
            return

        bus_id = _resolve_bus_id(topic_parts[1])
        if bus_id is None:
            print(f"⚠️ Unknown bus in topic {msg.topic} — ignoring")
            return
        msg_type = topic_parts[2]  # 'telemetry' or 'nfc'

        if msg_type == "nfc":
            if 'nfc_id' in payload and 'event' in payload:
                handle_nfc_event(client, bus_id, payload['nfc_id'], payload['event'])

        elif msg_type == "telemetry":
            lat = _to_float(payload.get('lat'))
            lng = _to_float(payload.get('lng'))
            speed = _to_float(payload.get('speed'))
            if lat is None or lng is None:
                return

            conn = get_db()
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO trip_logs (bus_id, lat, lng, speed, timestamp)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (bus_id, lat, lng, speed))
                conn.commit()
            finally:
                cur.close()
                conn.close()
                conn = None
                cur = None

            check_safety_logic(client, bus_id, lat, lng)
    except Exception as e:
        print(f"Error processing message: {e}")
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- START ---
def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    # Auto-reconnect with exponential backoff on transient broker drops.
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    if USE_SSL:
        # Verify the broker's TLS certificate against system CAs (prevents MITM).
        client.tls_set()

    print("Starting Listening Service (Intelligence Mode)...")
    # Retry the initial connection forever so a broker/DB outage at boot doesn't
    # permanently kill the listener (the supervising start.sh also restarts us).
    while True:
        try:
            if not MQTT_BROKER:
                print("⚠️ MQTT_BROKER not configured — retrying in 15s")
                time.sleep(15)
                continue
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except Exception as e:
            print(f"Connection failed: {e} — retrying in 5s")
            time.sleep(5)


if __name__ == '__main__':
    main()
