import eventlet
eventlet.monkey_patch()

from datetime import datetime
from psycogreen.eventlet import patch_psycopg
patch_psycopg()

import json
from flask import Flask, render_template, request, abort, session, redirect, url_for
from flask_socketio import SocketIO
from functools import wraps
import psycopg2

# --- CONFIGURATION ---
import os

# Database: credentials are loaded from the environment (see db_config.py)
from db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

print(f"🔌 DB Config: {DB_HOST}:{DB_PORT}/{DB_NAME} (User: {DB_USER})")

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
            port=DB_PORT,
            connect_timeout=3
        )
        return conn
    except Exception as e:
        # If internal hostname failed, try public proxy
        if not _db_host_override and host != "yamabiko.proxy.rlwy.net":
            print(f"⚠️ Internal DB connection failed ({host}), trying public proxy...")
            _db_host_override = "yamabiko.proxy.rlwy.net"
            try:
                conn = psycopg2.connect(
                    host=_db_host_override,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS,
                    port=DB_PORT,
                    connect_timeout=10
                )
                print(f"✅ Connected via public proxy!")
                return conn
            except Exception as e2:
                print(f"❌ Public Proxy Connect Error: {e2}")
                raise e2
        raise e

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
_secret_key = os.environ.get('FLASK_SECRET_KEY')
if not _secret_key:
    _secret_key = os.urandom(24)
    print("⚠️  WARNING: FLASK_SECRET_KEY not set — using a random key. All sessions will be invalidated on restart.")
app.config['SECRET_KEY'] = _secret_key

# SECURITY: Session cookie settings
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER') is not None  # HTTPS-only in production
app.config['SESSION_COOKIE_HTTPONLY'] = True      # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'     # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600   # 1 hour session expiry

# SECURITY: CORS - restrict to explicitly allowed origins.
# Default (empty list) allows same-origin requests only. Set CORS_ORIGINS to a
# comma-separated list of trusted origins, e.g. CORS_ORIGINS=https://your-app.railway.app
_cors_env = os.environ.get('CORS_ORIGINS', '').strip()
ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(',') if o.strip()]
socketio = SocketIO(app, cors_allowed_origins=ALLOWED_ORIGINS)

# SECURITY: Rate limiting to prevent brute-force attacks
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["2000 per day", "500 per hour"],
    storage_uri="memory://"
)

# Password hashing utilities
from werkzeug.security import generate_password_hash, check_password_hash

# SECURITY: CSRF protection for all state-changing requests
from flask_wtf.csrf import CSRFProtect, generate_csrf
csrf = CSRFProtect(app)

import time


# --- SECURITY HEADERS (applied to every response) ---
@app.after_request
def _set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://unpkg.com https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss: https:; "
        "media-src 'self' blob: https:; "
        "frame-ancestors 'none'"
    )
    return response


def _valid_coords(lat, lng):
    """True if lat/lng are numeric and within Earth's bounds."""
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180


# --- SOCKET EVENT RATE LIMITING (throttles high-frequency events per client) ---
_socket_rate = {}  # sid -> { event_name: last_monotonic_time }

def _socket_allow(event, min_interval):
    """Return False if this client sent `event` again within min_interval seconds."""
    sid = getattr(request, 'sid', None)
    if sid is None:
        return True
    now = time.monotonic()
    bucket = _socket_rate.setdefault(sid, {})
    if now - bucket.get(event, 0.0) < min_interval:
        return False
    bucket[event] = now
    return True


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
        # OLD CHECK REMOVED: It was preventing new migrations (like bus_manifest.status)
        # from running because it only checked for 'students.lat'.
        # We now rely on create_tables() being idempotent.
        
        # Check if tables already exist (migration was run from local)
        # cur.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name='students' AND column_name='lat'")
        # has_lat = cur.fetchone()[0] > 0
        cur.close()
        conn.close()
        
        # Always run create_tables (it handles IF NOT EXISTS)
        # if has_lat:
        #    _migration_done = True
        #    print("✅ [Migration] Tables already up-to-date, skipping.")
        #    return
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

def _upgrade_password_hash(user_id, plaintext):
    """Re-hash a legacy plain-text password after a successful login."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                    (generate_password_hash(plaintext), user_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Password hash upgrade failed for {user_id}: {e}")


def _verify_and_login(allowed_roles, redirect_endpoint):
    """Shared login handler: verify credentials, enforce role, start a session."""
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, role, school_id, password_hash FROM users WHERE name = %s", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and user[4]:
        user_id, user_name, role, school_id, stored_hash = user
        if stored_hash.startswith('pbkdf2:') or stored_hash.startswith('scrypt:'):
            password_valid = check_password_hash(stored_hash, password)
        else:
            # Legacy plain-text password: verify, then transparently upgrade to a hash.
            password_valid = (stored_hash == password)
            if password_valid:
                _upgrade_password_hash(user_id, password)

        if password_valid:
            if role not in allowed_roles:
                return "❌ Access Denied: Use the correct portal for your role.", 403
            session['user_id'] = user_id
            session['user_name'] = user_name
            session['user_role'] = role
            session['school_id'] = school_id
            return redirect(url_for(redirect_endpoint))

    return "❌ Invalid Login", 401


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute", methods=["POST"])
def login():
    """Admin Login Portal — SUPER_ADMIN and SCHOOL_ADMIN only."""
    if request.method == 'POST':
        return _verify_and_login(['SUPER_ADMIN', 'SCHOOL_ADMIN'], 'admin')
    return render_template('login.html')


@app.route('/driver/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute", methods=["POST"])
def driver_login():
    """Driver Login Portal — DRIVER only."""
    if request.method == 'POST':
        return _verify_and_login(['DRIVER'], 'driver_ui')
    return render_template('driver_login.html')


@app.route('/parent/login', methods=['GET', 'POST'])
@limiter.limit("20 per minute", methods=["POST"])
def parent_login():
    """Parent Login Portal — PARENT only."""
    if request.method == 'POST':
        return _verify_and_login(['PARENT'], 'parent_dashboard')
    return render_template('parent_login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/csrf-token')
@limiter.exempt
def get_csrf_token():
    """Returns a CSRF token for the current session. Must be included as
    X-CSRFToken header on all state-changing fetch() calls.
    Exempt from rate limits — GET-only, no state mutation."""
    return json.dumps({'token': generate_csrf()})

@app.route('/api/me')
def get_me():
    """Returns the current session's user role. Used by the Android app after
    login to detect the actual role (SUPER_ADMIN vs SCHOOL_ADMIN)."""
    role = session.get('user_role')
    if not role:
        return json.dumps({'role': None}), 401
    return json.dumps({'role': role, 'name': session.get('user_name', '')})

# --- API: Add Student (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/add_student', methods=['POST'])
@limiter.limit("30 per minute")
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

    student_name = data.get('name', '').strip()
    parent_id = data.get('parent_id', '').strip()
    nfc_id = data.get('nfc_id', '').strip()

    if not student_name or not parent_id or not nfc_id:
        cur.close(); conn.close()
        return "Missing required fields: name, parent_id, nfc_id", 400

    # VALIDATION: Check if parent_id is a valid UUID
    import uuid
    try:
        uuid.UUID(parent_id)
    except ValueError:
        cur.close(); conn.close()
        return "Invalid parent_id format", 400

    try:
        cur.execute("""
            INSERT INTO students (name, parent_id, school_id, nfc_tag_id, lat, lng, home_address_text, student_code)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (student_name, parent_id, school_target, nfc_id, data.get('lat'), data.get('lng'), data.get('address_text', ''), data.get('student_code')))

        new_student_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_student_id}), 200
    except Exception as e:
        print(f"Error adding student: {e}")
        return "Internal server error", 500

# --- API: Create Parent (SCHOOL_ADMIN ONLY) ---
@app.route('/api/create_parent', methods=['POST'])
@limiter.limit("30 per minute")
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def create_parent():
    data = request.json or {}
    parent_name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not parent_name or not username or not password:
        return json.dumps({"status": "error", "message": "Missing required fields: name, username, password"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        import uuid
        new_id = str(uuid.uuid4())

        hashed_password = generate_password_hash(password)

        if session['user_role'] == 'SCHOOL_ADMIN':
            school_id = session['school_id']
        else:
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
        return json.dumps({"status": "error", "message": "Internal server error"}), 500

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
            SELECT s.id, s.name, s.lat, s.lng,
                   COALESCE(m.status, 'DROPPED') as status
            FROM route_stops rs
            JOIN students s ON rs.assigned_student_id = s.id::text
            LEFT JOIN bus_manifest m ON m.student_id = s.id::text AND m.bus_id = %s
            WHERE rs.bus_id = %s
        """, (bus_id, bus_id))
        
        rows = cur.fetchall()
        
        students = [{
            "id": str(r[0]),
            "name": r[1],
            "lat": r[2],
            "lng": r[3],
            "status": r[4]  # Use the actual status from DB (defaults to DROPPED if null)
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

# --- API: Driver Info (bus_id + plate for mobile app) ---
@app.route('/api/driver/info')
@role_required(['DRIVER'])
def driver_info():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, plate_number FROM buses WHERE driver_id = %s", (session['user_id'],))
        bus = cur.fetchone()
        cur.close()
        conn.close()
        if not bus:
            return json.dumps({'bus_id': None, 'plate': None}), 200
        return json.dumps({'bus_id': bus[0], 'plate': bus[1]}), 200
    except Exception as e:
        print(f"Error driver_info: {e}")
        return json.dumps({'error': 'Internal server error'}), 500

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
        return "Internal server error", 500

# --- API: Get Students (Helper for Dropdown) ---
@app.route('/api/get_students', methods=['GET'])
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def get_students():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Filter by school if School Admin
        if session['user_role'] == 'SCHOOL_ADMIN':
             cur.execute("SELECT id, name, student_code, parent_id, lat, lng, home_address_text FROM students WHERE school_id = %s", (session['school_id'],))
        else:
             cur.execute("SELECT id, name, student_code, parent_id, lat, lng, home_address_text FROM students")
             
        rows = cur.fetchall()
        students = [{"id": str(r[0]), "name": r[1], "code": r[2] if r[2] else "", "parent_id": str(r[3]),
                     "lat": r[4], "lng": r[5], "address_text": r[6] if r[6] else ""} for r in rows]
        
        cur.close()
        conn.close()
        return json.dumps(students), 200
    except Exception as e:
        print(f"Error fetching students: {e}")
        return "Internal server error", 500

# --- API: Delete Student (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/delete_student', methods=['POST'])
@limiter.limit("30 per minute")
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
        return "Internal server error", 500

# --- API: Update Student Location (SCHOOL_ADMIN & SUPER_ADMIN) ---
@app.route('/api/update_student_location', methods=['POST'])
@limiter.limit("30 per minute")
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def update_student_location():
    data = request.json
    student_id = data.get('student_id')
    lat = data.get('lat')
    lng = data.get('lng')
    address_text = data.get('address_text', '') # Optional

    if not student_id or lat is None or lng is None:
        return "Missing ID, Lat, or Lng", 400
    if not _valid_coords(lat, lng):
        return "Invalid coordinates", 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Security Check
        # Universal Update (No PostGIS check needed)
        # We update lat, lng, and address_text directly
        if session.get('user_role') == 'SCHOOL_ADMIN':
            school_id = session.get('school_id')
            cur.execute("""
                UPDATE students 
                SET lat = %s, lng = %s, home_address_text = %s
                WHERE id = %s AND school_id = %s
            """, (lat, lng, address_text, student_id, school_id))
        else:
             cur.execute("""
                UPDATE students 
                SET lat = %s, lng = %s, home_address_text = %s
                WHERE id = %s
            """, (lat, lng, address_text, student_id))
            
        # SYNC TO MANIFEST (If student is currently boarded/listed)
        cur.execute("""
            UPDATE bus_manifest
            SET lat = %s, lng = %s
            WHERE student_id = %s
        """, (lat, lng, student_id))
            
        conn.commit()
        cur.close()
        conn.close()
        return "Location Updated", 200
    except Exception as e:
        print(f"Error updating location: {e}")
        return "Internal server error", 500

# --- API: Assign Bus / Create Stop (SCHOOL_ADMIN ONLY) ---
@app.route('/api/assign_bus', methods=['POST'])
@limiter.limit("30 per minute")
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def assign_bus():
    data = request.json
    student_id = data.get('student_id')
    bus_id = int(data.get('bus_id')) # We don't strictly use this in the simple logic yet, but good for record
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Universal Mode: Use Lat/Lng Columns (No PostGIS)
        cur.execute("SELECT name FROM students WHERE id = %s", (student_id,))
        student = cur.fetchone()
        if not student:
            return "Student not found", 404
        
        student_name = student[0]
        
        # Remove any existing stop for this student on this bus, then insert fresh
        cur.execute("DELETE FROM route_stops WHERE bus_id = %s AND assigned_student_id = %s::text", (bus_id, student_id))
        cur.execute("""
            INSERT INTO route_stops (stop_name, assigned_student_id, bus_id, lat, lng)
            SELECT %s, id::text, %s, lat, lng FROM students WHERE id = %s
        """, (f"{student_name}'s Home", bus_id, student_id))
        
        conn.commit()
        cur.close()
        conn.close()
        return "Bus Assigned (Stop Created)", 200
    except Exception as e:
        print(f"Error assigning bus: {e}")
        return "Internal server error", 500

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
        return "Internal server error", 500

# --- API: Delete Bus (SUPER_ADMIN ONLY) ---
@app.route('/api/delete_bus', methods=['POST'])
@limiter.limit("30 per minute")
@role_required(['SUPER_ADMIN'])
def delete_bus():
    data = request.json
    bus_id = int(data.get('bus_id'))
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    if not bus_id:
        cur.close()
        conn.close()
        return "Bus ID required", 400

    cur.execute("DELETE FROM buses WHERE id = %s", (bus_id,))
    conn.commit()
    cur.close()
    conn.close()
    return "Bus Deleted", 200

# --- API: Add Bus (SUPER_ADMIN ONLY) ---
@app.route('/api/add_bus', methods=['POST'])
@limiter.limit("30 per minute")
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
        return "Internal server error", 500

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
        return "Internal server error", 500

# --- NEW: Create School Admin (SUPER_ADMIN ONLY) ---
@app.route('/api/create_school_admin', methods=['POST'])
@limiter.limit("30 per minute")
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
        return "Internal server error", 500

# --- NEW: Update Parent Credentials (SUPER_ADMIN ONLY) ---
@app.route('/api/update_parent_credentials', methods=['POST'])
@limiter.limit("30 per minute")
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
        return "Internal server error", 500

# --- NEW: Camera "Switchboard" ---
@app.route('/get_camera/<bus_id>')
@role_required(['PARENT', 'SCHOOL_ADMIN', 'SUPER_ADMIN'])
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
@role_required(['PARENT'])
def get_my_children(parent_id):
    # SECURITY: a parent may only view their own children.
    if parent_id != session.get('user_id'):
        abort(403)
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 3. Get Children & Their Status
    # Join by student UUID — bus_manifest.student_id is always a student UUID,
    # set by both manual attendance and NFC tap (listener.py resolves NFC→UUID).
    query = """
        SELECT s.id, s.name, s.nfc_tag_id,
               bm.bus_id,
               b.plate_number
        FROM students s
        LEFT JOIN bus_manifest bm ON bm.student_id = s.id::text AND bm.status = 'BOARDED'
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
@limiter.limit("30 per minute")
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def create_driver():
    data = request.json or {}
    driver_username = data.get('username', '').strip()
    driver_password = data.get('password', '')

    if not driver_username or not driver_password:
        return json.dumps({"status": "error", "message": "Missing required fields: username, password"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        import uuid
        new_id = str(uuid.uuid4())

        if session['user_role'] == 'SCHOOL_ADMIN':
            school_id = session['school_id']
        else:
            school_id = data.get('school_id')
            if not school_id:
                return json.dumps({"status": "error", "message": "School ID required"}), 400

        hashed_password = generate_password_hash(driver_password)

        cur.execute("""
            INSERT INTO users (id, name, role, school_id, password_hash)
            VALUES (%s, %s, 'DRIVER', %s, %s)
        """, (new_id, driver_username, school_id, hashed_password))

        conn.commit()
        cur.close()
        conn.close()
        return json.dumps({"status": "success", "id": new_id}), 200
    except Exception as e:
        print(f"Error creating driver: {e}")
        return json.dumps({"status": "error", "message": "Internal server error"}), 500

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
        drivers = [{"id": str(r[0]), "name": r[1], "school_id": r[2] if len(r) > 2 else None} for r in rows]
        
        cur.close()
        conn.close()
        return json.dumps(drivers), 200
    except Exception as e:
        print(f"Error fetching drivers: {e}")
        return "Internal server error", 500

# --- API: Assign Driver to Bus ---
@app.route('/api/assign_driver', methods=['POST'])
@limiter.limit("30 per minute")
@role_required(['SCHOOL_ADMIN', 'SUPER_ADMIN'])
def assign_driver():
    data = request.json
    driver_id = data.get('driver_id')
    bus_id = int(data.get('bus_id'))
    
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
        print(f"Error assigning driver: {e}")
        return "Internal server error", 500

# --- SOCKET.IO HANDLERS ---

@socketio.on('connect')
def handle_connect():
    print(f"✅ Client Connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client Disconnected: {request.sid}")
    _socket_rate.pop(request.sid, None)

@socketio.on('join')
def on_join(data):
    room = data.get('room', '') if isinstance(data, dict) else ''
    # Only allow joining bus rooms (numeric IDs) or known named rooms
    if not room or not str(room).isdigit():
        return
    from flask_socketio import join_room
    join_room(str(room))
    print(f"📢 Client {request.sid} joined room: {room}")

@socketio.on('driver_gps_update')
def handle_driver_gps(data):
    """
    Received GPS data from Driver App.
    Data: { 'bus_id': 1, 'lat': ..., 'lng': ..., 'speed': ... }
    """
    if session.get('user_role') != 'DRIVER':
        return
    if not _socket_allow('driver_gps_update', 0.5):
        return

    bus_id = data.get('bus_id')
    lat = data.get('lat')
    lng = data.get('lng')
    speed = data.get('speed', 0)

    if not bus_id or lat is None or lng is None:
        return
    if not _valid_coords(lat, lng):
        return

    # Broadcast to parent/admin maps — clients filter by bus_id client-side.
    socketio.emit('update_map', data)

    # 2. Update DB (Asynchronously via eventlet/psycogreen)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE buses 
            SET current_lat = %s, current_lng = %s, current_speed = %s, last_updated = NOW()
            WHERE id = %s
        """, (lat, lng, speed, bus_id))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"GPS Update DB Error: {e}")

@socketio.on('manual_attendance')
def handle_manual_attendance(data):
    """
    Driver manually toggles student status.
    Data: { 'student_id': 123, 'status': 'BOARDED'|'DROPPED', 'bus_id': 1 }
    """
    if session.get('user_role') != 'DRIVER':
        return
    student_id = data.get('student_id')
    status = data.get('status')
    bus_id = data.get('bus_id')

    if not student_id or not bus_id or status not in ('BOARDED', 'DROPPED'):
        return

    print(f"🚌 Manual Attendance: Student {student_id} -> {status} (Bus {bus_id})")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # UPSERT into bus_manifest
        # We store denormalized data (name, lat, lng) for faster route calculation.
        
        if status == 'BOARDED':
            # Need to fetch student details first
            cur.execute("SELECT name, lat, lng FROM students WHERE id = %s", (student_id,))
            s_row = cur.fetchone()
            
            s_name = s_row[0] if s_row else "Unknown"
            s_lat = s_row[1] if s_row else None
            s_lng = s_row[2] if s_row else None

            cur.execute("""
                INSERT INTO bus_manifest (bus_id, student_id, student_name, lat, lng, status, timestamp)
                VALUES (%s, %s, %s, %s, %s, 'BOARDED', NOW())
                ON CONFLICT (bus_id, student_id) 
                DO UPDATE SET status = 'BOARDED', timestamp = NOW(), 
                              student_name = EXCLUDED.student_name, lat = EXCLUDED.lat, lng = EXCLUDED.lng
            """, (bus_id, student_id, s_name, s_lat, s_lng))
        else:
            # DROPPED
            # Update status to DROPPED.
            cur.execute("""
                UPDATE bus_manifest 
                SET status = 'DROPPED', timestamp = NOW()
                WHERE bus_id = %s AND student_id = %s
            """, (bus_id, student_id))
            
        conn.commit()
        
        # Notify parents/admins — clients filter by bus_id or reload on receipt.
        socketio.emit('student_status_update', {
            'student_id': student_id,
            'status': status,
            'bus_id': bus_id if status == 'BOARDED' else None,
            'timestamp': str(datetime.now())
        })
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Attendance Update Error: {e}")

# --- CAMERA STREAMING HANDLERS ---
# Tracks which buses currently have an active camera stream (bus_id -> True).
active_streams = {}

@socketio.on('camera_stream_start')
def handle_stream_start(data):
    if session.get('user_role') != 'DRIVER':
        return
    bus_id = data.get('bus_id')
    active_streams[bus_id] = True
    print(f"📹 Stream Started for Bus {bus_id}")
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': True})

@socketio.on('camera_stream_stop')
def handle_stream_stop(data):
    if session.get('user_role') != 'DRIVER':
        return
    bus_id = data.get('bus_id')
    active_streams.pop(bus_id, None)
    print(f"🛑 Stream Stopped for Bus {bus_id}")
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': False})

@socketio.on('camera_frame')
def handle_camera_frame(data):
    if session.get('user_role') != 'DRIVER':
        return
    # Throttle to ~12 fps per client to limit bandwidth and DoS exposure.
    if not _socket_allow('camera_frame', 0.08):
        return
    socketio.emit('bus_camera_frame', data)

@socketio.on('join_bus_stream')
def handle_join_stream(data):
    """A viewer subscribes to a bus's camera stream and gets its current state."""
    if session.get('user_role') not in ('PARENT', 'SCHOOL_ADMIN', 'SUPER_ADMIN'):
        return
    bus_id = data.get('bus_id')
    socketio.emit('bus_stream_status', {'bus_id': bus_id, 'streaming': bus_id in active_streams})

@app.route('/api/optimize_route/<int:bus_id>', methods=['GET'])
@role_required(['DRIVER', 'SCHOOL_ADMIN', 'SUPER_ADMIN'])
def optimize_route(bus_id):
    """
    Simpler Route Optimization (Nearest Neighbor) v2
    Returns sorted list of students for Google Maps integration.
    """
    conn = None
    cur = None
    try:
        # 1. Get Driver Location (Optional, defaults to first student)
        driver_lat = request.args.get('lat', type=float)
        driver_lng = request.args.get('lng', type=float)
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 2. Get Boarded Students (OPTIMIZED: Read directly from Manifest)
        print(f"🔍 OptRoute: Reading manifest for Bus {bus_id}...")
        cur.execute("""
            SELECT student_name, lng, lat, student_id 
            FROM bus_manifest 
            WHERE bus_id = %s AND status = 'BOARDED'
        """, (bus_id,))
        
        rows = cur.fetchall()
        print(f"📋 OptRoute: Found {len(rows)} boarded records.")
        
        students = []
        missing_data_ids = []
        
        for r in rows:
            s_name = r[0]
            s_lng = r[1]
            s_lat = r[2]
            s_id = r[3]
            
            # fast-path: data exists in manifest
            if s_lat is not None and s_lng is not None:
                students.append((s_name, s_lng, s_lat))
            else:
                # slow-path: data missing in manifest (old record), need fetch
                missing_data_ids.append(s_id)

        # Fallback for old records (Migration Safety)
        if missing_data_ids:
            print(f"⚠️ OptRoute: {len(missing_data_ids)} records missing denormalized data. Fetching from students table...")
            ids_tuple = tuple(str(x) for x in missing_data_ids)
            placeholders = ','.join(['%s'] * len(ids_tuple))
            query = f"SELECT name, lng, lat FROM students WHERE id::text IN ({placeholders})"
            cur.execute(query, ids_tuple)
            details = cur.fetchall()
            for d in details:
                if d[1] is not None and d[2] is not None:
                    students.append((d[0], d[1], d[2]))
                    print(f"   Re-fetched {d[0]}")

        if not students:
             print("❌ OptRoute: No valid GPS data found for boarded students.")
             return json.dumps({"status": "empty", "message": "No valid GPS data for boarded students"}), 200

        print(f"✅ OptRoute: Final List Size: {len(students)}")
            
        # 3. Nearest Neighbor Sort
            
        # 3. Nearest Neighbor Sort
        # Prepare list
        unvisited = []
        for s in students:
            unvisited.append({"name": s[0], "lng": s[1], "lat": s[2]})
            
        # Start point: Driver OR First Student
        current_lat = driver_lat
        current_lng = driver_lng
        
        if current_lat is None or current_lng is None:
            # Fallback: Start at first student
            # Check if list is not empty (already checked above)
            current_lat = unvisited[0]['lat']
            current_lng = unvisited[0]['lng']
            
        sorted_stops = []
        
        while unvisited:
            nearest_idx = -1
            min_dist = float('inf')
            
            for i, stop in enumerate(unvisited):
                # Euclidan Distance Squared
                d_lat = stop['lat'] - current_lat
                d_lng = stop['lng'] - current_lng
                dist = (d_lat**2) + (d_lng**2)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_idx = i
            
            # Add nearest to path
            if nearest_idx != -1:
                next_stop = unvisited.pop(nearest_idx)
                sorted_stops.append(next_stop)
                # Update current pos to this stop
                current_lat = next_stop['lat']
                current_lng = next_stop['lng']
            else:
                break
                
        # 4. Return Result
        return json.dumps({
            "status": "success",
            "stops": sorted_stops,
            "count": len(sorted_stops)
        }), 200

    except Exception as e:
        print(f"❌ Route Calc Error: {e}")
        return json.dumps({"status": "error", "message": str(e)}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()



@app.route('/api/fix_gps')
@role_required(['SUPER_ADMIN'])
def api_fix_gps():
    try:
        from fix_student_gps import fix_gps
        fix_gps() # Run the fix
        return "✅ Success! All students now have GPS locations. You can now use the Route Calculator.", 200
    except Exception as e:
        return f"❌ Error: {e}", 500

# --- START ---
if __name__ == '__main__':
    # Initialize DB (Create tables if missing)
    try:
        init_db()
    except Exception as e:
        print(f"DB Init Failed: {e}")

    # Start the Web Server
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Web App running at http://localhost:{port}")
    socketio.run(app, host='0.0.0.0', port=port)
