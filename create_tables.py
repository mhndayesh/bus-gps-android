import psycopg2
import os

# --- PASTE YOUR RAILWAY CREDENTIALS HERE ---
# (Copy these from the Variables tab in Railway)
# --- CONFIGURATION: ENV VARS > HARDCODED ---
DB_HOST = os.environ.get("DB_HOST", "yamabiko.proxy.rlwy.net")
DB_NAME = os.environ.get("DB_NAME", "railway")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN")
DB_PORT = os.environ.get("DB_PORT", "27535")

import time

def create_tables():
    try:
        retries = 5
        conn = None
        while retries > 0:
            print(f"🔌 Connecting to {DB_HOST} (User: {DB_USER})... (Attempt {6 - retries}/5)")
            try:
                conn = psycopg2.connect(
                    host=DB_HOST,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASS,
                    port=DB_PORT
                )
                print("✅ Connected to Database!")
                break
            except Exception as e:
                print(f"❌ Connection failed: {e}")
                retries -= 1
                if retries == 0:
                    print("❌ Could not connect to database after 5 attempts. Exiting.")
                    raise e
                print("⏳ Waiting 5 seconds before retrying...")
                time.sleep(5)

        cur = conn.cursor()
        
        print("🛠️ Creating Tables...")
        
        # 0. Enable PostGIS (SKIPPED - Not available on some Railway plans)
        # try:
        #     cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        # except Exception as e:
        #     print(f"⚠️ PostGIS Warning: {e}")
        #     conn.rollback()
        
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

        # 4. Students
        # REFACTOR: Removed PostGIS dependency. Using simple Lat/Lng.
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
            cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lat FLOAT;")
            cur.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS lng FLOAT;")
            conn.commit()
        except:
            conn.rollback()

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
            cur.execute("ALTER TABLE route_stops ADD COLUMN IF NOT EXISTS lat FLOAT;")
            cur.execute("ALTER TABLE route_stops ADD COLUMN IF NOT EXISTS lng FLOAT;")
            conn.commit()
        except:
            conn.rollback()
        
        # 5. Manifest
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bus_manifest (
                bus_id INTEGER REFERENCES buses(id),
                student_id TEXT, 
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bus_id, student_id)
            );
        """)

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
            cur.execute("ALTER TABLE trip_logs ADD COLUMN IF NOT EXISTS lat FLOAT;")
            cur.execute("ALTER TABLE trip_logs ADD COLUMN IF NOT EXISTS lng FLOAT;")
            conn.commit()
        except:
            conn.rollback()
        
        # 7. Seed Data
        print("🌱 Seeding Data...")
        cur.execute("INSERT INTO schools (name) VALUES ('Happy Valley School') ON CONFLICT DO NOTHING;")
        cur.execute("INSERT INTO users (id, name, role, school_id, password_hash) VALUES ('admin', 'Super Admin', 'SUPER_ADMIN', 1, 'admin') ON CONFLICT DO NOTHING;")
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ SUCCESS! Tables Created & Admin Added.")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_tables()

# Alias for web_app.py import
init_db = create_tables
