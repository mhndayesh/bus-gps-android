import psycopg2

def migrate_buses():
    try:
        conn = psycopg2.connect("dbname=bus_tracking user=admin password=password host=localhost")
        cur = conn.cursor()
        
        print("🔌 Connected...")
        
        # Add school_id to BUSES
        try:
            cur.execute("ALTER TABLE buses ADD COLUMN school_id INTEGER REFERENCES schools(id) DEFAULT 1")
            print("✅ Column 'school_id' added to 'buses'.")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️ Column 'school_id' already exists in 'buses'.")
            
        conn.commit()
        cur.close()
        conn.close()
        print("🚀 Bus Migration Complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    migrate_buses()
