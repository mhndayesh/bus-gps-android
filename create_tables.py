import psycopg2
import os

# --- PASTE YOUR RAILWAY CREDENTIALS HERE ---
# (Copy these from the Variables tab in Railway)
DB_HOST = "yamabiko.proxy.rlwy.net"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN"
DB_PORT = "27535"

def create_tables():
    print(f"🔌 Connecting to {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
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
                driver_id TEXT REFERENCES users(id), /* Added for Driver Assignment */
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # MIGRATION: Ensure driver_id exists (for existing DBs)
        try:
            cur.execute("ALTER TABLE buses ADD COLUMN IF NOT EXISTS driver_id TEXT REFERENCES users(id);")
            conn.commit()
        except Exception as e:
            print(f"⚠️ Migration Note: {e}")
            conn.rollback()

        # 4. Students
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                student_code TEXT,
                parent_id TEXT REFERENCES users(id),
                school_id INTEGER REFERENCES schools(id),
                nfc_tag_id TEXT UNIQUE
            );
        """)

        # 4.5 Route Stops (Added for Cloud Compat)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS route_stops (
                id SERIAL PRIMARY KEY,
                stop_name TEXT,
                assigned_student_id TEXT,
                bus_id INTEGER REFERENCES buses(id)
            );
        """)
        
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
                speed FLOAT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
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
