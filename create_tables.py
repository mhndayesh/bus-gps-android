import os
import secrets
import psycopg2
from werkzeug.security import generate_password_hash

# --- CONFIGURATION: credentials are loaded from the environment (see db_config.py) ---
from db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT, PUBLIC_PROXY_HOST

def create_tables():
    """Connect to DB and run migrations. No retries - caller handles that."""
    print(f"🔌 Connecting to {DB_HOST} (User: {DB_USER})...")

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=3
        )
    except Exception as e:
        print(f"⚠️ Internal DB connection failed ({DB_HOST}), trying public proxy...")
        # Fallback to public proxy
        try:
            conn = psycopg2.connect(
                host=PUBLIC_PROXY_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                connect_timeout=10
            )
            print(f"✅ Connected via public proxy (yamabiko.proxy.rlwy.net)!")
        except Exception as e2:
            print(f"❌ Failed to connect to DB (Both Internal & Proxy): {e2}")
            return
        
    print("✅ Connected to Database!")
    cur = conn.cursor()

    print("🛠️ Creating Tables...")

    # 1. School
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
    """)

    # 2. Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            school_id INTEGER REFERENCES schools(id),
            password_hash TEXT
        );
    """)
    # MIGRATION: add UNIQUE constraint if it doesn't already exist
    try:
        cur.execute("""
            ALTER TABLE users ADD CONSTRAINT users_name_unique UNIQUE (name)
        """)
        conn.commit()
    except Exception:
        conn.rollback()

    # 3. Buses
    cur.execute("""
        CREATE TABLE IF NOT EXISTS buses (
            id SERIAL PRIMARY KEY,
            plate_number TEXT NOT NULL,
            iot_device_id TEXT UNIQUE,
            school_id INTEGER REFERENCES schools(id),
            driver_id TEXT REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # MIGRATION: Ensure driver_id exists
    try:
        cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS driver_id TEXT REFERENCES users(id);")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration step skipped: {e}")

    # 4. Students (Lat/Lng instead of PostGIS)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            student_code TEXT,
            parent_id TEXT REFERENCES users(id),
            school_id INTEGER REFERENCES schools(id),
            nfc_tag_id TEXT UNIQUE,
            home_address_text TEXT,
            lat FLOAT,
            lng FLOAT
        );
    """)

    # MIGRATIONS for Students
    try:
        cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS home_address_text TEXT;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration step skipped: {e}")

    try:
        print("🔄 Migrating students table...")
        cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lat FLOAT;")
        cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lng FLOAT;")
        conn.commit()
        print("✅ students table migrated (lat/lng added).")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration failed for students table: {e}")

    # MIGRATION for Buses (Live Tracking)
    try:
        cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_lat FLOAT;")
        cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_lng FLOAT;")
        cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS current_speed FLOAT;")
        cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP;")
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration step skipped: {e}")

    # 4.5 Route Stops
    cur.execute("""
        CREATE TABLE IF NOT EXISTS route_stops (
            id SERIAL PRIMARY KEY,
            stop_name TEXT,
            assigned_student_id TEXT,
            bus_id INTEGER REFERENCES buses(id),
            lat FLOAT,
            lng FLOAT
        );
    """)

    # MIGRATION for Route Stops
    try:
        print("🔄 Migrating route_stops table...")
        cur.execute("ALTER TABLE route_stops ADD COLUMN IF NOT EXISTS lat FLOAT;")
        cur.execute("ALTER TABLE route_stops ADD COLUMN IF NOT EXISTS lng FLOAT;")
        conn.commit()
        print("✅ route_stops table migrated (lat/lng added).")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration failed for route_stops table: {e}")

    # 5. Manifest (Denormalized for Performance)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bus_manifest (
            bus_id INTEGER REFERENCES buses(id),
            student_id TEXT,
            student_name TEXT,
            lat FLOAT,
            lng FLOAT,
            status TEXT DEFAULT 'BOARDED',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bus_id, student_id)
        );
    """)

    # MIGRATION for Bus Manifest (Add lat/lng/name)
    try:
        print("🔄 Migrating bus_manifest table...")
        cur.execute("ALTER TABLE bus_manifest ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'BOARDED';")
        cur.execute("ALTER TABLE bus_manifest ADD COLUMN IF NOT EXISTS student_name TEXT;")
        cur.execute("ALTER TABLE bus_manifest ADD COLUMN IF NOT EXISTS lat FLOAT;")
        cur.execute("ALTER TABLE bus_manifest ADD COLUMN IF NOT EXISTS lng FLOAT;")
        conn.commit()
        print("✅ bus_manifest table migrated (denormalized columns added).")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration failed for bus_manifest table: {e}")

    # 6. Trip Logs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trip_logs (
            id SERIAL PRIMARY KEY,
            bus_id INTEGER REFERENCES buses(id),
            lat FLOAT,
            lng FLOAT,
            speed FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # MIGRATION: Ensure trip_logs lat/lng exist
    try:
        print("🔄 Migrating trip_logs table...")
        cur.execute("ALTER TABLE trip_logs ADD COLUMN IF NOT EXISTS lat FLOAT;")
        cur.execute("ALTER TABLE trip_logs ADD COLUMN IF NOT EXISTS lng FLOAT;")
        conn.commit()
        print("✅ trip_logs table migrated (lat/lng added).")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration failed for trip_logs table: {e}")

    # 7. Seed Data
    print("🌱 Seeding Data...")
    cur.execute("INSERT INTO schools (name) VALUES ('Happy Valley School') ON CONFLICT DO NOTHING;")

    # Seed the super-admin with a HASHED password. The password comes from
    # INITIAL_ADMIN_PASSWORD; if unset, a random one is generated and printed once.
    admin_password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    generated = False
    if not admin_password:
        admin_password = secrets.token_urlsafe(12)
        generated = True

    cur.execute(
        "INSERT INTO users (id, name, role, school_id, password_hash) "
        "VALUES ('admin', 'Super Admin', 'SUPER_ADMIN', 1, %s) ON CONFLICT DO NOTHING;",
        (generate_password_hash(admin_password),),
    )
    if generated and cur.rowcount:
        print("=" * 60)
        print("🔑 INITIAL SUPER ADMIN CREATED")
        print("   Username: Super Admin")
        print(f"   Password: {admin_password}")
        print("   ^ Save this now — it will not be shown again.")
        print("=" * 60)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ SUCCESS! Tables Created & Admin Added.")

if __name__ == "__main__":
    create_tables()

# Alias for web_app.py import
init_db = create_tables
