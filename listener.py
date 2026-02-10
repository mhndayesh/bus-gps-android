import json
import paho.mqtt.client as mqtt
import psycopg2
import time
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2) 
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

# --- CONFIGURATION (CLOUD vs LOCAL) ---
import os
import ssl

if os.environ.get('RENDER'):
    # Cloud (Render + HiveMQ)
    print("☁️ Listener: Cloud Mode")
    DB_HOST = os.environ.get("DB_HOST")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASS = os.environ.get("DB_PASS")
    DB_PORT = "5432"
    
    MQTT_BROKER = os.environ.get("MQTT_BROKER")
    MQTT_PORT = 8883
    MQTT_USER = os.environ.get("MQTT_USER")
    MQTT_PASS = os.environ.get("MQTT_PASS")
    USE_SSL = True
else:
    # Local
    print("💻 Listener: Local Mode")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_NAME = os.environ.get("DB_NAME", "bus_tracker_db")
    DB_USER = os.environ.get("DB_USER", "postgres") 
    DB_PASS = os.environ.get("DB_PASS", "password") 
    DB_PORT = "5432"
    
    MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
    MQTT_PORT = 1883
    MQTT_USER = None
    MQTT_PASS = None
    USE_SSL = False

# --- DATABASE HELPERS ---
def get_db():
    return psycopg2.connect(
        host=DB_HOST, 
        database=DB_NAME, 
        user=DB_USER, 
        password=DB_PASS,
        port=DB_PORT
    )

# 1. NEW: Handle NFC Taps (Boarding/Exiting)
def handle_nfc_event(client, bus_id, nfc_id, event_type):
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Map NFC Tag ID to Student ID (Simple lookup for now)
        student_id = nfc_id 

        if event_type == "BOARDING":
            print(f"🔵 Student {student_id} BOARDED Bus {bus_id}")
            # Add to Manifest
            cur.execute("INSERT INTO bus_manifest (bus_id, student_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (bus_id, student_id))
        
        elif event_type == "DROPOFF":
            print(f"🟢 Student {student_id} LEFT Bus {bus_id}")
            # Remove from Manifest
            cur.execute("DELETE FROM bus_manifest WHERE bus_id = %s AND student_id = %s", (bus_id, student_id))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error handling NFC event: {e}")

# 2. NEW: The "No-Skip" Safety Check
def check_safety_logic(client, bus_id, lat, lng):
    try:
        conn = get_db()
        cur = conn.cursor()

        # LOGIC: Find any stops within 50 meters of this bus location (Python Haversine)
        cur.execute("SELECT stop_name, assigned_student_id, lat, lng FROM route_stops WHERE bus_id = %s", (bus_id,))
        stops = cur.fetchall()
        
        nearby_stop = None
        for s in stops:
            s_name, s_student, s_lat, s_lng = s
            if s_lat is None or s_lng is None: continue
            
            dist = haversine(lat, lng, s_lat, s_lng)
            if dist <= 50: # 50 meters
                nearby_stop = (s_name, s_student)
                break

        if nearby_stop:
            stop_name, student_target = nearby_stop
            
            # Check if that specific student is currently ON the bus
            cur.execute("SELECT 1 FROM bus_manifest WHERE bus_id = %s AND student_id = %s", (bus_id, student_target))
            is_student_onboard = cur.fetchone()

            if is_student_onboard:
                # DANGER: Bus is at the stop, but student is still logged as "ON BOARD"
                message = f"⚠️  ALERT: Bus is at {stop_name}. Ensure Student {student_target} gets off!"
                print(message)
                
                # Action: Publish alert back to Driver Tablet
                alert_payload = json.dumps({"type": "ALERT", "msg": f"DROP OFF {student_target} NOW!"})
                client.publish(f"bus/{bus_id}/alerts", alert_payload)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error in safety logic: {e}")

# --- MQTT HANDLERS ---
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe("bus/+/+") # Listen to EVERYTHING (telemetry and nfc)

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode()
        payload = json.loads(payload_str)
        topic_parts = msg.topic.split("/")
        
        # Topic format: bus/{bus_id}/{type}
        if len(topic_parts) < 3:
            return

        bus_id = topic_parts[1]
        msg_type = topic_parts[2] # 'telemetry' or 'nfc'

        if msg_type == "nfc":
            # Handle Student Tap
            if 'nfc_id' in payload and 'event' in payload:
                handle_nfc_event(client, bus_id, payload['nfc_id'], payload['event'])

        elif msg_type == "telemetry":
            # Handle GPS
            lat = payload.get('lat')
            lng = payload.get('lng')
            speed = payload.get('speed')
            
            if lat is not None and lng is not None:
                # 1. Save to DB
                conn = get_db()
                cur = conn.cursor()
                try:
                    cur.execute("""
                        INSERT INTO trip_logs (bus_id, lat, lng, speed, timestamp) 
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (bus_id, lat, lng, speed))
                    conn.commit()
                except Exception as db_err:
                    print(f"DB Error: {db_err}")
                finally:
                    cur.close()
                    conn.close()

                # 2. Run Safety Checks
                check_safety_logic(client, bus_id, lat, lng)
                
    except Exception as e:
        print(f"Error processing message: {e}")

# --- START ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print("Starting Listening Service (Intelligence Mode)...")
try:
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)

    if USE_SSL:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)

    client.connect(MQTT_BROKER, int(MQTT_PORT), 60)
    client.loop_forever()
except Exception as e:
    print(f"Connection failed: {e}")
