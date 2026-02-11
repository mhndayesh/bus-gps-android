import eventlet
eventlet.monkey_patch()

import json
import paho.mqtt.client as mqtt
from flask import Flask, render_template, request, abort, session, redirect, url_for
from flask_socketio import SocketIO
from functools import wraps
import psycopg2

# --- CONFIGURATION (Universal - Uses ENV VARS with fallbacks) ---
import os
import ssl

# Database: Always use ENV VARS (Railway sets these automatically)
DB_HOST = os.environ.get("DB_HOST", "yamabiko.proxy.rlwy.net")
DB_NAME = os.environ.get("DB_NAME", "railway")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN")
DB_PORT = os.environ.get("DB_PORT", "27535")

# MQTT: Always use ENV VARS
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "8883"))
MQTT_USER = os.environ.get("MQTT_USER")
MQTT_PASS = os.environ.get("MQTT_PASS")
USE_SSL = bool(MQTT_USER)  # Use SSL if credentials are provided

print(f"🔌 DB Config: {DB_HOST}:{DB_PORT}/{DB_NAME} (User: {DB_USER})")

MQTT_TOPIC = "bus/+/telemetry"

# Mock User Session REMOVED - Using Flask Session now

# --- DATABASE HELPERS ---
_db_host_override = None  # Will switch to public proxy if internal fails

def get_db_connection():
    global _db_host_override
    host = _db_host_override or DB_HOST
    try:
        conn = psycopg2.connect(
            host=host,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        # If internal hostname failed, try public proxy
        if not _db_host_override and host != "yamabiko.proxy.rlwy.net":
            print(f"⚠️ Internal DB connection failed ({host}), trying public proxy...")
            _db_host_override = "yamabiko.proxy.rlwy.net"
            conn = psycopg2.connect(
                host=_db_host_override,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT
            )
            print(f"✅ Connected via public proxy!")
            return conn
        raise

def init_db():
    """Initialize the database - delegates to create_tables.py."""
    from create_tables import create_tables
    create_tables()
    print("✅ Database Initialized")

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Check if user is logged in
            if 'user_role' not in session:
                if request.path.startswith('/api/'):
                    return json.dumps({"status": "error", "message": "Unauthorized: Please Login"}), 401
                return redirect(url_for('login'))
            
            # 2. Check Role
            if session['user_role'] not in allowed_roles:
                # Clear wrong session and redirect to correct portal
                current_role = session.get('user_role', 'Unknown')
                session.clear()
                
                # Friendly message
                msg = f"⚠️ Session cleared. You were logged in as '{current_role}' but this page requires {allowed_roles}. Please login again."
                
                if request.path.startswith('/api/'):
                    return json.dumps({"status": "error", "message": msg}), 403
                
                # Redirect to appropriate login
                return f'''
                <html>
                <head><meta http-equiv="refresh" content="3;url=/login"></head>
                <body style="font-family:sans-serif; padding:40px; text-align:center;">
                    <h2>⚠️ Wrong Account Type</h2>
                    <p>You were logged in as <b>{current_role}</b>, but this page is for <b>{', '.join(allowed_roles)}</b>.</p>
                    <p>Your session has been cleared. Redirecting to login...</p>
                    <p><a href="/login">Click here if not redirected</a></p>
                </body>
                </html>
                ''', 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- SETUP FLASK & SOCKETIO ---
app = Flask(__name__)

# SECURITY: Secret key from environment variable (CRITICAL!)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# SECURITY: Session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True        # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True      # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'     # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600   # 1 hour session expiry

# SECURITY: CORS - Restrict to allowed origins
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
# In production, set CORS_ORIGINS=https://your-app.railway.app
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ['*'] else "*")

# SECURITY: Rate limiting to prevent brute-force attacks
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Password hashing utilities
from werkzeug.security import generate_password_hash, check_password_hash

# --- LAZY MIGRATION (Runs on first HTTP request, not during import) ---
_migration_done = False

@app.before_request
def _lazy_migrate():
    global _migration_done
    if _migration_done:
        return  # Already done, skip
    try:
        # Use get_db_connection which has the public proxy fallback
        conn = get_db_connection()
        cur = conn.cursor()
        # Check if tables already exist (migration was run from local)
        cur.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name='students' AND column_name='lat'")
        has_lat = cur.fetchone()[0] > 0
        cur.close()
        conn.close()
        if has_lat:
            _migration_done = True
            print("✅ [Migration] Tables already up-to-date, skipping.")
            return
        # Tables missing columns - run full migration
        print("🔄 [Migration] Running create_tables...")
        from create_tables import create_tables as _ct
        _ct()
        _migration_done = True
        print("✅ [Migration] Complete!")
    except Exception as e:
        print(f"⚠️ [Migration] Will retry next request: {e}")

# --- MANUAL MIGRATION API (Safety Net) ---
@app.route('/api/force_migrate')
@role_required(['SUPER_ADMIN'])
def force_migrate():
    try:
        from create_tables import init_db
        init_db()
        return "✅ Database Migration Forced Successfully!", 200
    except Exception as e:
        return f"❌ Migration Failed: {e}", 500

# --- TOUR PAGES (Public Landing Pages) ---
@app.route('/tour')
def tour_select():
    return render_template('tour-select.html')

@app.route('/tour/parent')
def tour_parent():
    return render_template('parent-tour.html')

@app.route('/tour/school')
def tour_school():
    return render_template('school-tour.html')

@app.route('/tour/investor')
def tour_investor():
    return render_template('investor-tour.html')

# --- DASHBOARD STATISTICS API ---
@app.route('/api/dashboard/stats')
@role_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def dashboard_stats():
    """Return dashboard statistics based on user role"""
    role = session.get('user_role')
    school_id = session.get('school_id')  # For SCHOOL_ADMIN
    
    # Super Admin can filter by school using query param
    filter_school_id = request.args.get('school_id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if role == 'SUPER_ADMIN':
            if filter_school_id and filter_school_id != 'all':
                # Filter by specific school
                cur.execute("SELECT COUNT(*) FROM buses WHERE school_id = %s", (filter_school_id,))
                total_buses = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM students WHERE school_id = %s", (filter_school_id,))
                total_students = cur.fetchone()[0]
                
                cur.execute("""
                    SELECT COUNT(DISTINCT bm.student_id) 
                    FROM bus_manifest bm
                    JOIN students s ON bm.student_id::text = s.id::text
                    WHERE s.school_id = %s
                """, (filter_school_id,))
                present_students = cur.fetchone()[0]
            else:
                # All schools
                cur.execute("SELECT COUNT(*) FROM buses")
                total_buses = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM students")
                total_students = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(DISTINCT student_id) FROM bus_manifest")
                present_students = cur.fetchone()[0]
            
        else:  # SCHOOL_ADMIN
            # School Admin sees only their school
            cur.execute("SELECT COUNT(*) FROM buses WHERE school_id = %s", (school_id,))
            total_buses = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM students WHERE school_id = %s", (school_id,))
            total_students = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(DISTINCT bm.student_id) 
                FROM bus_manifest bm
                JOIN students s ON bm.student_id::text = s.id::text
                WHERE s.school_id = %s
            """, (school_id,))
            present_students = cur.fetchone()[0]
        
        # Calculate absent and active buses
        absent_students = total_students - present_students
        active_buses = len(active_streams)  # From global active_streams dict
        
        cur.close()
        conn.close()
        
        return json.dumps({
            "total_buses": total_buses,
            "active_buses": active_buses,
            "total_students": total_students,
            "present_students": present_students,
            "absent_students": absent_students
        }), 200
        
    except Exception as e:
        print(f"❌ Dashboard stats error: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)}), 500


# --- MQTT LISTENER (Background Task) ---
# This runs separately so it doesn't block the website
# --- SOCKET EVENTS (The Bridge) ---

@socketio.on('driver_gps_update')
def handle_driver_gps(data):
    # 1. Receive Data from Driver Phone
    print(f"📍 Bus {data.get('bus_id')} moved to {data.get('lat')}, {data.get('lng')}")
    
    # 2. Broadcast Data to Parent Phones
    socketio.emit('update_map', data)

@socketio.on('manual_attendance')
def handle_attendance(data):
    sid = data['student_id']
    status = data['status'] # BOARDED or DROPPED
    bus_id = data['bus_id']
    
    print(f"📝 Attendance: Student {sid} is {status}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if status == "BOARDED":
            # Add to Manifest
            cur.execute("""
                INSERT INTO bus_manifest (bus_id, student_id) 
                VALUES (%s, %s) 
                ON CONFLICT DO NOTHING
            """, (bus_id, sid))
        else:
            # Remove from Manifest
            cur.execute("DELETE FROM bus_manifest WHERE bus_id = %s AND student_id = %s", (bus_id, sid))
            
        conn.commit()
        cur.close()
        conn.close()
        
        # Notify Parents Live
        socketio.emit('student_status_update', {
            "student_id": sid,
            "status": status,
            "bus_id": bus_id if status == "BOARDED" else None
        })
        
    except Exception as e:
        print(f"❌ Attendance Error: {e}")

# --- CAMERA STREAMING EVENTS ---
# Track which buses are currently streaming
active_streams = {}

@socketio.on('camera_stream_start')
def handle_camera_start(data):
    bus_id = data.get('bus_id')
    active_streams[bus_id] = True
    print(f"📹 Camera stream STARTED for bus {bus_id}")
    # Notify all clients that this bus is now streaming
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': True})

@socketio.on('camera_stream_stop')
def handle_camera_stop(data):
    bus_id = data.get('bus_id')
    if bus_id in active_streams:
        del active_streams[bus_id]
    print(f"📹 Camera stream STOPPED for bus {bus_id}")
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': False})

@socketio.on('camera_frame')
def handle_camera_frame(data):
    bus_id = data.get('bus_id')
    frame = data.get('frame')  # Base64 JPEG
    timestamp = data.get('timestamp')
    
    # Broadcast frame to all connected clients watching this bus
    socketio.emit('bus_camera_frame', {
        'bus_id': bus_id,
        'frame': frame,
        'timestamp': timestamp
    })

@socketio.on('join_bus_stream')
def handle_join_stream(data):
    """Parent joins a specific bus's stream room"""
    bus_id = data.get('bus_id')
    print(f"👁️ Parent joined stream for bus {bus_id}")
    # Check if bus is currently streaming
    is_streaming = bus_id in active_streams
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': is_streaming})

def mqtt_listener():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    def on_connect(c, u, f, rc, properties=None):
        c.subscribe(MQTT_TOPIC)
        print("✅ Connected to MQTT Broker. Listening for buses...")

    def on_message(c, u, msg):
        try:
            # 1. Receive GPS from Bus
            payload = json.loads(msg.payload.decode())
            bus_id = payload.get("bus_id")
            
            print(f"📡 Data received from Bus {bus_id}")
            
            # 2. Push to Web Browser immediately (Real-time!)
            socketio.emit('update_map', payload)
        except Exception as e:
            print(f"Error forwarding message: {e}")

    client.on_connect = on_connect
    client.on_message = on_message
    
    # Auth and SSL
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    
    if USE_SSL:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)

    try:
        client.connect(MQTT_BROKER, int(MQTT_PORT), 60)
        client.loop_forever()
    except Exception as e:
        print(f"MQTT Connection Error: {e}")

# --- WEB ROUTES ---
@app.route('/driver')
@role_required(['DRIVER'])
def driver_ui():
    # Find assigned bus
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, plate_number FROM buses WHERE driver_id = %s", (session['user_id'],))
    bus = cur.fetchone()
    cur.close()
    conn.close()
    
    if not bus:
        return "<h1>❌ You are not assigned to a bus yet. Ask your Admin.</h1>"
        
    return render_template('driver_app.html', bus_id=str(bus[0]), plate_number=bus[1])



@app.route('/')
def index():
    return render_template('index.html')

# --- PARENT DASHBOARD ---
@app.route('/parent')
@role_required(['PARENT'])
def parent_dashboard():
    user = session.get('user_name', 'Parent')
    return render_template('parent_dashboard.html', user=user)

# --- API: Get My Kids (Parent Only) ---
@app.route('/api/get_my_kids')
@role_required(['PARENT'])
def get_my_kids():
    try:
        parent_id = session['user_id']
        print(f"🔍 get_my_kids called for parent_id: {parent_id}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get children linked to this parent
        cur.execute("""
            SELECT s.id, s.name, s.student_code 
            FROM students s 
            WHERE s.parent_id = %s
        """, (parent_id,))
        rows = cur.fetchall()
        
        print(f"📋 Found {len(rows)} children for parent {parent_id}")
        
        kids = []
        for r in rows:
            student_id = str(r[0])
            
            # Check if student is on a bus (in bus_manifest)
            cur.execute("""
                SELECT bm.bus_id, b.plate_number 
                FROM bus_manifest bm
                JOIN buses b ON bm.bus_id = b.id
                WHERE bm.student_id = %s
            """, (student_id,))
            bus_row = cur.fetchone()
            
            on_bus = bus_row is not None
            bus_id = bus_row[0] if bus_row else None
            bus_plate = bus_row[1] if bus_row else None
            
            kids.append({
                "id": student_id, 
                "name": r[1], 
                "code": r[2], 
                "on_bus": on_bus,
                "bus_id": bus_id,
                "bus_plate": bus_plate
            })
        
        cur.close()
        conn.close()
        return json.dumps(kids), 200
    except Exception as e:
        print(f"❌ Error getting kids: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"status": "error", "message": str(e)}), 500

# --- DEBUG: Check Parent Session ---
@app.route('/api/debug/parent_session')
@role_required(['PARENT'])
def debug_parent_session():
    """Debug endpoint to see parent session and their linked children"""
    try:
        parent_id = session.get('user_id')
        parent_name = session.get('user_name')
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all students linked to this parent
        cur.execute("SELECT id, name, parent_id FROM students WHERE parent_id = %s", (parent_id,))
        linked_students = cur.fetchall()
        
        # Get all parents in system to compare
        cur.execute("SELECT id, name FROM users WHERE role = 'PARENT' LIMIT 10")
        all_parents = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return json.dumps({
            "your_session": {
                "user_id": parent_id,
                "user_name": parent_name
            },
            "linked_students": [{"id": str(s[0]), "name": s[1], "parent_id": str(s[2])} for s in linked_students],
            "sample_parents": [{"id": str(p[0]), "name": p[1]} for p in all_parents]
        }, indent=2), 200
    except Exception as e:
        return json.dumps({"error": str(e)}), 500

@app.route('/admin')
@role_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def admin():
    role = session.get('user_role')
    user = session.get('user_name', 'User')
    
    if role == 'SUPER_ADMIN':
        return render_template('super_admin.html', user=user, role=role)
    elif role == 'SCHOOL_ADMIN':
        return render_template('school_admin.html', user=user, role=role)
    else:
        return "Unknown Role", 403

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    """Admin Login Portal - Only for SUPER_ADMIN and SCHOOL_ADMIN"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        # Get user with password hash for verification
        cur.execute("SELECT id, name, role, school_id, password_hash FROM users WHERE name = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and user[4]:  # user[4] is password_hash
            # SECURITY: Verify password using hash
            # Support both old plain-text (temporary) and new hashed passwords
            stored_hash = user[4]
            password_valid = False
            
            if stored_hash.startswith('pbkdf2:') or stored_hash.startswith('scrypt:'):
                # New hashed password
                password_valid = check_password_hash(stored_hash, password)
            else:
                # Legacy plain-text (will be migrated)
                password_valid = (stored_hash == password)
            
            if password_valid:
                role = user[2]
                # Validate: Only Admins allowed here
                if role not in ['SUPER_ADMIN', 'SCHOOL_ADMIN']:
                    return "❌ Access Denied: Use the correct portal for your role.", 403
                
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['user_role'] = role
                session['school_id'] = user[3]
                return redirect(url_for('admin'))
        
        return "❌ Invalid Login", 401
    
    return render_template('login.html')


@app.route('/driver/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def driver_login():
    """Driver Login Portal - Only for DRIVER"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, role, school_id, password_hash FROM users WHERE name = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and user[4]:
            stored_hash = user[4]
            password_valid = False
            
            if stored_hash.startswith('pbkdf2:') or stored_hash.startswith('scrypt:'):
                password_valid = check_password_hash(stored_hash, password)
            else:
                password_valid = (stored_hash == password)
            
            if password_valid:
                role = user[2]
                if role != 'DRIVER':
                    return "❌ Access Denied: This portal is for Drivers only.", 403
                
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['user_role'] = role
                session['school_id'] = user[3]
                return redirect(url_for('driver_ui'))
        
        return "❌ Invalid Login", 401
    
    return render_template('driver_login.html')


@app.route('/parent/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=["POST"])
def parent_login():
    """Parent Login Portal - Only for PARENT"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, role, school_id, password_hash FROM users WHERE name = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if user and user[4]:
            stored_hash = user[4]
            password_valid = False
            
            if stored_hash.startswith('pbkdf2:') or stored_hash.startswith('scrypt:'):
                password_valid = check_password_hash(stored_hash, password)
            else:
                password_valid = (stored_hash == password)
            
            if password_valid:
                role = user[2]
                if role != 'PARENT':
                    return "❌ Access Denied: This portal is for Parents only.", 403
                
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['user_role'] = role
                session['school_id'] = user[3]
                return redirect(url_for('parent_dashboard'))
        
        return "❌ Invalid Login", 401
    
    return render_template('parent_login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- API: Add Student (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/add_student', methods=['POST'])
@role_required(['SUPER_ADMIN', 'SCHOOL_ADMIN'])
def add_student():
    data = request.json
    
    # SECURITY: Force the student into the Admin's school
    # (Prevents School A adding students to School B)
    # SECURITY: Force the student into the Admin's school
    # (Prevents School A adding students to School B)
    conn = get_db_connection()
    cur = conn.cursor()

    if session['user_role'] == 'SCHOOL_ADMIN':
        school_target = session['school_id']
    else:
        # SUPER_ADMIN: Use school_id from request, or fallback to parent's school
        school_target = data.get('school_id')
        if not school_target:
            # Fallback: Get from parent
            p_id = data.get('parent_id')
            if p_id:
                cur.execute("SELECT school_id FROM users WHERE id = %s", (p_id,))
                row = cur.fetchone()
                if row:
                    school_target = row[0]
            if not school_target:
                return json.dumps({"status": "error", "message": "School required"}), 400

    # VALIDATION: Check if parent_id is a valid UUID
    import uuid
    try:
        uuid.UUID(str(data['parent_id']))
    except ValueError:
        return f"❌ Error: Parent ID '{data['parent_id']}' is not a valid UUID. Please use the pre-filled value.", 400

    try:
        # Insert into DB
        # conn = get_db_connection() # Moved up
        # cur = conn.cursor() # Moved up
        
        # We need a parent_id (User ID). For now, assume provided or create dummy.
        # Ensure parent exists or handle error. 
        # For this demo, let's assume the user passes a valid parent_id or we insert NULL if allowed (it's FK though).
        # We will wrap in try/catch.
        
        # Universal Mode: Use Lat/Lng Columns (No PostGIS)
        cur.execute("""
            INSERT INTO students (name, parent_id, school_id, nfc_tag_id, lat, lng, home_address_text, student_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (data['name'], data['parent_id'], school_target, data['nfc_id'], data.get('lat'), data.get('lng'), data.get('address_text', ''), data.get('student_code')))
            
        new_student_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_student_id}), 200
    except Exception as e:
        print(f"Error adding student: {e}")
        return str(e), 500

# --- API: Create Parent (SCHOOL_ADMIN ONLY) ---
@app.route('/api/create_parent', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def create_parent():
    data = request.json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Generator for ID (Simple UUID for prototype)
        import uuid
        new_id = str(uuid.uuid4())
        
        # Get username/password from request (or use defaults)
        username = data.get('username', data['name'])  # Default to name if no username
        password = data.get('password', 'parent123')   # Default password
        
        # SECURITY: Hash the password before storing
        hashed_password = generate_password_hash(password)
        
        # School ID Logic
        if session['user_role'] == 'SCHOOL_ADMIN':
             school_id = session['school_id']
        else:
             # SUPER_ADMIN: Must provide school_id
             school_id = data.get('school_id')
             if not school_id:
                 return json.dumps({"status": "error", "message": "Missing School ID"}), 400

        cur.execute("""
            INSERT INTO users (id, name, role, school_id, password_hash)
            VALUES (%s, %s, 'PARENT', %s, %s)
        """, (new_id, username, school_id, hashed_password))
        
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_id}), 200
    except Exception as e:
        print(f"Error creating parent: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500

# --- API: Get Driver Manifest ---
@app.route('/api/driver/manifest')
@role_required(['DRIVER'])
def get_driver_manifest():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Bus ID for this driver
        cur.execute("SELECT id FROM buses WHERE driver_id = %s", (session['user_id'],))
        row = cur.fetchone()
        if not row: return "[]", 200
        bus_id = row[0]
        
        # Get Assigned Students (via Route Stops)
        # Assuming simplified model where stops link student to bus
        cur.execute("""
            SELECT s.id, s.name, 
                   CASE WHEN m.student_id IS NOT NULL THEN 1 ELSE 0 END as on_board
            FROM route_stops rs
            JOIN students s ON rs.assigned_student_id = s.id::text
            LEFT JOIN bus_manifest m ON m.student_id = s.id::text AND m.bus_id = %s
            WHERE rs.bus_id = %s
        """, (bus_id, bus_id))
        
        rows = cur.fetchall()
        
        students = [{
            "id": r[0], 
            "name": r[1], 
            "status": "BOARDED" if r[2] else "DROPPED"
        } for r in rows]
        
        # If no route stops assigned, maybe show ALL students (for testing)?
        # For now, let's stick to route assignment. 
        if not students:
             # Fallback: Get all students in school? No, too messy.
             pass
             
        cur.close()
        conn.close()
        return json.dumps(students), 200
    except Exception as e:
        print(f"Manifest Error: {e}")
        return json.dumps([]), 500

# --- API: Get Parents (Helper for Dropdown) ---
@app.route('/api/get_parents', methods=['GET'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def get_parents():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Filter by school if School Admin
        if session['user_role'] == 'SCHOOL_ADMIN':
             cur.execute("SELECT id, name FROM users WHERE role = 'PARENT' AND school_id = %s", (session['school_id'],))
        else:
             # SUPER_ADMIN: Check if specific school requested via Query Param
             target_school = request.args.get('school_id')
             if target_school:
                 cur.execute("SELECT id, name FROM users WHERE role = 'PARENT' AND school_id = %s", (target_school,))
             else:
                 cur.execute("SELECT id, name FROM users WHERE role = 'PARENT'")
             
        rows = cur.fetchall()
        parents = [{"id": r[0], "name": r[1]} for r in rows]
        
        cur.close()
        conn.close()
        return json.dumps(parents), 200
    except Exception as e:
        print(f"Error fetching parents: {e}")
        return str(e), 500

# --- API: Get Students (Helper for Dropdown) ---
@app.route('/api/get_students', methods=['GET'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def get_students():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Filter by school if School Admin
        if session['user_role'] == 'SCHOOL_ADMIN':
             cur.execute("SELECT id, name, student_code, parent_id FROM students WHERE school_id = %s", (session['school_id'],))
        else:
             cur.execute("SELECT id, name, student_code, parent_id FROM students")
             
        rows = cur.fetchall()
        # Handle cases where student_code might be None
        students = [{"id": str(r[0]), "name": r[1], "code": r[2] if r[2] else "", "parent_id": str(r[3])} for r in rows]
        
        cur.close()
        conn.close()
        return json.dumps(students), 200
    except Exception as e:
        print(f"Error fetching students: {e}")
        return str(e), 500

# --- API: Delete Student (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/delete_student', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def delete_student():
    data = request.json
    student_id = data.get('student_id')
    
    if not student_id: return "Student ID Required", 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Security: School Admin can only delete their own students
        if session['user_role'] == 'SCHOOL_ADMIN':
            cur.execute("DELETE FROM students WHERE id = %s AND school_id = %s", (student_id, session['school_id']))
        else:
            cur.execute("DELETE FROM students WHERE id = %s", (student_id,))
            
        conn.commit()
        cur.close()
        conn.close()
        return "Student Deleted", 200
    except Exception as e:
        print(f"Error deleting student: {e}")
        return str(e), 500

# --- API: Update Student Location (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/update_student_location', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def update_student_location():
    data = request.json
    student_id = data.get('student_id')
    lat = data.get('lat')
    lng = data.get('lng')
    address_text = data.get('address_text', '') # Optional

    if not student_id or not lat or not lng:
        return "Missing ID, Lat, or Lng", 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Security Check
        # Universal Update (No PostGIS check needed)
        # We update lat, lng, and address_text directly
        if session['user_role'] == 'SCHOOL_ADMIN':
            cur.execute("""
                UPDATE students 
                SET lat = %s, lng = %s, home_address_text = %s
                WHERE id = %s AND school_id = %s
            """, (lat, lng, address_text, student_id, session['school_id']))
        else:
             cur.execute("""
                UPDATE students 
                SET lat = %s, lng = %s, home_address_text = %s
                WHERE id = %s
            """, (lat, lng, address_text, student_id))
            
        if cur.rowcount == 0:
             # Just in case
             pass
            
        conn.commit()
        cur.close()
        conn.close()
        return "Location Updated", 200
    except Exception as e:
        print(f"Error updating location: {e}")
        return str(e), 500

# --- API: Assign Bus / Create Stop (SCHOOL_ADMIN ONLY) ---
@app.route('/api/assign_bus', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def assign_bus():
    data = request.json
    student_id = data.get('student_id')
    bus_id = data.get('bus_id') # We don't strictly use this in the simple logic yet, but good for record
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Universal Mode: Use Lat/Lng Columns (No PostGIS)
        cur.execute("SELECT name FROM students WHERE id = %s", (student_id,))
        student = cur.fetchone()
        if not student:
            return "Student not found", 404
        
        student_name = student[0]
        
        # Create Stop in route_stops (Copy lat/lng from student)
        cur.execute("""
            INSERT INTO route_stops (stop_name, assigned_student_id, bus_id, lat, lng)
            SELECT %s, id, %s, lat, lng FROM students WHERE id = %s
        """, (f"{student_name}'s Home", bus_id, student_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return "Bus Assigned (Stop Created)", 200
    except Exception as e:
        print(f"Error assigning bus: {e}")
        return str(e), 500

# --- API: Get Buses (Helper for Dropdown) ---
@app.route('/api/get_buses', methods=['GET'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def get_buses():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # SCHOOL ADMIN: Only see OWN buses
        if session['user_role'] == 'SCHOOL_ADMIN':
            cur.execute("SELECT id, plate_number FROM buses WHERE school_id = %s", (session['school_id'],))
        
        # SUPER ADMIN: Sees ALL (or could filter if we add UI for it)
        else:
            cur.execute("SELECT id, plate_number, school_id FROM buses")
            
        rows = cur.fetchall()
        
        if session['user_role'] == 'SCHOOL_ADMIN':
            buses = [{"id": str(r[0]), "plate": r[1]} for r in rows]
        else:
            # For Super Admin, include school_id for filtering
            buses = [{"id": str(r[0]), "plate": r[1] + f" (School {r[2]})", "school_id": r[2]} for r in rows]

        cur.close()
        conn.close()
        return json.dumps(buses), 200
    except Exception as e:
        print(f"Error fetching buses: {e}")
        return str(e), 500

# --- API: Delete Bus (SUPER_ADMIN ONLY) ---
@app.route('/api/delete_bus', methods=['POST'])
@role_required(['SUPER_ADMIN'])
def delete_bus():
    data = request.json
    bus_id = data.get('bus_id')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if bus_id:
        cur.execute("DELETE FROM buses WHERE id = %s", (bus_id,))
    else:
        cur.execute("DELETE FROM buses WHERE id = (SELECT id FROM buses ORDER BY created_at DESC LIMIT 1)")
        
    conn.commit()
    cur.close()
    conn.close()
    return "Bus Deleted", 200

# --- API: Add Bus (SUPER_ADMIN ONLY) ---
@app.route('/api/add_bus', methods=['POST'])
@role_required(['SUPER_ADMIN'])
def add_bus():
    data = request.json
    plate = data.get('plate')
    school_id = data.get('school_id', 1) # Default to School 1 if not specified

    if not plate: 
        return "Plate Number Required", 400
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        import uuid
        iot_id = str(uuid.uuid4())
        
        cur.execute("INSERT INTO buses (plate_number, iot_device_id, school_id) VALUES (%s, %s, %s) RETURNING id", (plate, iot_id, school_id))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_id}), 200
    except Exception as e:
        print(f"Error adding bus: {e}")
        return str(e), 500

# --- API: Get Schools (Helper) ---
@app.route('/api/get_schools', methods=['GET'])
@role_required(['SUPER_ADMIN'])
def get_schools():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM schools")
        rows = cur.fetchall()
        schools = [{"id": r[0], "name": r[1]} for r in rows]
        cur.close()
        conn.close()
        return json.dumps(schools), 200
    except Exception as e:
        print(f"Error fetching schools: {e}")
        return str(e), 500

# --- NEW: Create School Admin (SUPER_ADMIN ONLY) ---
@app.route('/api/create_school_admin', methods=['POST'])
@role_required(['SUPER_ADMIN'])
def create_school_admin():
    data = request.json
    school_name = data.get('school_name')
    username = data.get('username')
    password = data.get('password')

    if not school_name or not username or not password:
        return "Missing Fields (School Name, Username, Password)", 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Create School
        cur.execute("INSERT INTO schools (name) VALUES (%s) RETURNING id", (school_name,))
        new_school_id = cur.fetchone()[0]
        
        # 2. Create School Admin User linked to this School
        import uuid
        new_user_id = str(uuid.uuid4())
        
        # SECURITY: Hash the password before storing
        hashed_password = generate_password_hash(password)
        
        cur.execute("""
            INSERT INTO users (id, name, role, school_id, password_hash)
            VALUES (%s, %s, 'SCHOOL_ADMIN', %s, %s)
        """, (new_user_id, username, new_school_id, hashed_password))
        
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "school_id": new_school_id, "admin_id": new_user_id}), 200
    except Exception as e:
        print(f"Error creating school admin: {e}")
        return str(e), 500

# --- NEW: Update Parent Credentials (SUPER_ADMIN ONLY) ---
@app.route('/api/update_parent_credentials', methods=['POST'])
@role_required(['SUPER_ADMIN'])
def update_parent_credentials():
    data = request.json
    parent_id = data.get('parent_id')
    new_username = data.get('username')
    new_password = data.get('password')

    if not parent_id or not new_username or not new_password:
        return "Missing Fields", 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # SECURITY: Hash the password before storing
        hashed_password = generate_password_hash(new_password)
        
        # Update entry
        cur.execute("""
            UPDATE users 
            SET name = %s, password_hash = %s 
            WHERE id = %s AND role = 'PARENT'
        """, (new_username, hashed_password, parent_id))
        
        if cur.rowcount == 0:
            return "Parent not found", 404
            
        conn.commit()
        cur.close()
        conn.close()
        return "Parent Credentials Updated", 200
    except Exception as e:
        print(f"Error updating credentials: {e}")
        return str(e), 500

# --- NEW: Camera "Switchboard" ---
@app.route('/get_camera/<bus_id>')
def get_camera_url(bus_id):
    # IN THE FUTURE: Query DB for 'camera_stream_url'
    
    # FOR NOW: Public Test Stream
    fake_camera_feed = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
    
    return json.dumps({
        "bus_id": bus_id, 
        "stream_url": fake_camera_feed,
        "status": "live"
    })



@app.route('/api/my_children/<parent_id>')
def get_my_children(parent_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 3. Get Children & Their Status
    query = """
        SELECT s.id, s.name, s.nfc_tag_id, 
               bm.bus_id, 
               b.plate_number
        FROM students s
        LEFT JOIN bus_manifest bm ON s.nfc_tag_id = bm.student_id
        LEFT JOIN buses b ON bm.bus_id = b.id
        WHERE s.parent_id = %s
    """
    cur.execute(query, (parent_id,))
    children = cur.fetchall()
    
    cur.close()
    conn.close()

    # Format for JSON
    result = []
    for child in children:
        result.append({
            "name": child[1],
            "status": "ON BUS" if child[3] else "AT SCHOOL / HOME",
            "bus_id": child[3],  # None if not on bus
            "bus_plate": child[4]
        })
        
    return json.dumps(result)

# --- API: Create Driver ---
@app.route('/api/create_driver', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def create_driver():
    data = request.json
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        import uuid
        new_id = str(uuid.uuid4())
        
        # Determine School ID
        if session['user_role'] == 'SCHOOL_ADMIN':
            school_id = session['school_id']
        else:
            school_id = data.get('school_id')
            if not school_id: return json.dumps({"status": "error", "message": "School ID required"}), 400

        # SECURITY: Hash the password before storing
        hashed_password = generate_password_hash(data['password'])

        cur.execute("""
            INSERT INTO users (id, name, role, school_id, password_hash)
            VALUES (%s, %s, 'DRIVER', %s, %s)
        """, (new_id, data['username'], school_id, hashed_password))
        
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_id}), 200
    except Exception as e:
        print(f"Error creating driver: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500

# --- API: Get Drivers ---
@app.route('/api/get_drivers', methods=['GET'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def get_drivers():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if session['user_role'] == 'SCHOOL_ADMIN':
            cur.execute("SELECT id, name FROM users WHERE role = 'DRIVER' AND school_id = %s", (session['school_id'],))
        else:
            # Super Admin can filter by school if passed
            target_school = request.args.get('school_id') # Not currently used by UI but good to have
            if target_school:
                cur.execute("SELECT id, name FROM users WHERE role = 'DRIVER' AND school_id = %s", (target_school,))
            else:
                cur.execute("SELECT id, name, school_id FROM users WHERE role = 'DRIVER'")
        
        rows = cur.fetchall()
        drivers = [{"id": r[0], "name": r[1], "school_id": r[2] if len(r)>2 else ""} for r in rows]
        
        cur.close()
        conn.close()
        return json.dumps(drivers), 200
    except Exception as e:
        return str(e), 500

# --- API: Assign Driver to Bus ---
@app.route('/api/assign_driver', methods=['POST'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def assign_driver():
    data = request.json
    driver_id = data.get('driver_id')
    bus_id = data.get('bus_id')
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Clear previous assignment for this bus
        cur.execute("UPDATE buses SET driver_id = NULL WHERE id = %s", (bus_id,))
        
        # 2. Assign new driver
        cur.execute("UPDATE buses SET driver_id = %s WHERE id = %s", (driver_id, bus_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return "Driver Assigned", 200
    except Exception as e:
        return str(e), 500

@app.route('/api/optimize_route/<int:bus_id>', methods=['GET'])
@role_required(['DRIVER', 'SCHOOL_ADMIN', 'SUPER_ADMIN'])
def optimize_route(bus_id):
    """
    Calculate optimized route for a bus using OSRM.
    Uses driver's current location as start point.
    Only includes students currently BOARDED (in bus_manifest).
    Query params: ?lat=X&lng=Y (driver's current position)
    """
    try:
        # Get driver's current location from query params
        driver_lat = request.args.get('lat', type=float)
        driver_lng = request.args.get('lng', type=float)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get only students currently ON BOARD (in bus_manifest)
        cur.execute("""
            SELECT s.name, s.lng, s.lat
            FROM bus_manifest bm
            JOIN students s ON bm.student_id = s.id::text
            WHERE bm.bus_id = %s AND s.lat IS NOT NULL AND s.lng IS NOT NULL
        """, (bus_id,))
        
        students = cur.fetchall()
        cur.close()
        conn.close()
        
        if not students:
            return json.dumps({"status": "empty", "message": "لا يوجد طلاب على متن الحافلة"}), 200

        # Build coordinates: driver location first, then student homes
        coords = []
        if driver_lat and driver_lng:
            coords.append(f"{driver_lng},{driver_lat}")  # OSRM uses lng,lat
        
        for s in students:
            coords.append(f"{s[1]},{s[2]}")
        
        # If only 1 coord (1 student, no GPS), return direct location
        if len(coords) < 2:
            return json.dumps({
                "status": "success",
                "geometry": None,
                "stops": [{"name": students[0][0], "lat": students[0][2], "lng": students[0][1], "order": 1}],
                "distance": 0,
                "duration": 0
            }), 200
             
        coordinates_string = ";".join(coords)
        # Use route API (trip API is broken on public OSRM server)
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{coordinates_string}?geometries=geojson&overview=full"
        
        # 3. Call OSRM
        import requests
        response = requests.get(osrm_url, timeout=10)
        data = response.json()
        
        if response.status_code != 200 or data.get('code') != 'Ok':
             error_msg = data.get('message', 'Routing Engine Error')
             print(f"❌ OSRM Error: {error_msg}")
             return json.dumps({"status": "error", "message": error_msg}), 500
        
        # 4. Process Result
        routes = data.get('routes', [])
        if not routes:
            return json.dumps({"status": "error", "message": "No route found"}), 404
            
        best_route = routes[0]
        geometry = best_route['geometry']  # GeoJSON LineString
        
        # Build ordered stops from the waypoints
        waypoints = data.get('waypoints', [])
        sorted_students = []
        for i, wp in enumerate(waypoints):
            if i < len(students):
                sorted_students.append({
                    "name": students[i][0],
                    "lat": students[i][2],
                    "lng": students[i][1],
                    "order": i + 1
                })
            
        return json.dumps({
            "status": "success",
            "geometry": geometry,
            "stops": sorted_students,
            "distance": best_route['distance'],
            "duration": best_route['duration']
        }), 200
        
    except Exception as e:
        print(f"❌ Optimization Error: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500

@app.route('/parent/dashboard')
def parent_dashboard_view():
    return render_template('parent_dashboard.html')

# --- START ---
if __name__ == '__main__':
    # Initialize DB (Create tables if missing)
    try:
        init_db()
    except Exception as e:
        print(f"DB Init Failed: {e}")

    # Start the MQTT listener in the background
    eventlet.spawn(mqtt_listener)
    # Start the Web Server
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Web App running at http://localhost:{port}")
    socketio.run(app, host='0.0.0.0', port=port)
