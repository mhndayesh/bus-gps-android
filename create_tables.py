import psycopg2
import os

# --- CONFIGURATION: ENV VARS > HARDCODED ---
DB_HOST = os.environ.get("DB_HOST", "yamabiko.proxy.rlwy.net")
DB_NAME = os.environ.get("DB_NAME", "railway")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN")
DB_PORT = os.environ.get("DB_PORT", "27535")

def create_tables():
    """Connect to DB and run migrations. No retries - caller handles that."""
    print(f"🔌 Connecting to {DB_HOST} (User: {DB_USER})...")
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
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
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            school_id INTEGER REFERENCES schools(id),
            password_hash TEXT
        );
    """)

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
    except:
        conn.rollback()

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
    except:
        conn.rollback()

    try:
        print("🔄 Migrating students table...")
        cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lat FLOAT;")
        cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lng FLOAT;")
        conn.commit()
        print("✅ students table migrated (lat/lng added).")
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Migration failed for students table: {e}")

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

    # 5. Manifest
        CREATE TABLE IF NOT EXISTS bus_manifest (
            bus_id INTEGER REFERENCES buses(id),
            student_id TEXT,
            status TEXT DEFAULT 'BOARDED',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (bus_id, student_id)
        );
    """)

    # MIGRATION for Bus Manifest
    try:
        cur.execute("ALTER TABLE bus_manifest ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'BOARDED';")
        conn.commit()
    except:
        conn.rollback()

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
    cur.execute("INSERT INTO users (id, name, role, school_id, password_hash) VALUES ('admin', 'Super Admin', 'SUPER_ADMIN', 1, 'admin') ON CONFLICT DO NOTHING;")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ SUCCESS! Tables Created & Admin Added.")

if __name__ == "__main__":
    create_tables()

# Alias for web_app.py import
init_db = create_tables
