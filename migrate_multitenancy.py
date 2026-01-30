import psycopg2

DB_HOST = "localhost"
DB_NAME = "bus_tracking"
DB_USER = "admin"
DB_PASS = "password"
DB_PORT = "5432"

def migrate():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        print("🔌 Connected to Database...")

        # 1. Create SCHOOLS table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Table 'schools' checked/created.")

        # 2. Insert Default School (if not exists)
        cur.execute("SELECT id FROM schools WHERE id = 1")
        if not cur.fetchone():
            cur.execute("INSERT INTO schools (name) VALUES ('Default Base School')")
            print("✅ Default School (ID 1) created.")
        
        # 3. Add school_id to USERS
        try:
            cur.execute("ALTER TABLE users ADD COLUMN school_id INTEGER REFERENCES schools(id) DEFAULT 1")
            print("✅ Column 'school_id' added to 'users'.")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️ Column 'school_id' already exists in 'users'.")
        
        # 4. Add school_id to STUDENTS
        try:
            cur.execute("ALTER TABLE students ADD COLUMN school_id INTEGER REFERENCES schools(id) DEFAULT 1")
            print("✅ Column 'school_id' added to 'students'.")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️ Column 'school_id' already exists in 'students'.")

        conn.commit()
        cur.close()
        conn.close()
        print("🚀 Migration Complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    migrate()
