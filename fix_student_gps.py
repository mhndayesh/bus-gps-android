import psycopg2
import os
import random

# DB configuration is loaded from the environment (see db_config.py)
from db_config import DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

def fix_gps():
    print(f"🔌 Connecting to {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            port=DB_PORT,
            connect_timeout=10
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        # Try proxy hardcoded if env var fails
        try:
             print("⚠️ Trying fallback proxy...")
             conn = psycopg2.connect(
                host="yamabiko.proxy.rlwy.net",
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT,
                connect_timeout=10
            )
        except Exception as e2:
             print(f"❌ Fallback failed: {e2}")
             return

    cur = conn.cursor()
    
    # Jeddah Center
    base_lat = 21.543333
    base_lng = 39.172778
    
    print("🔍 Finding students with missing GPS...")
    cur.execute("SELECT id, name FROM students WHERE lat IS NULL OR lng IS NULL")
    rows = cur.fetchall()
    
    if not rows:
        print("✅ All students already have GPS data. No changes needed.")
        return

    print(f"🛠️ Updating {len(rows)} students with dummy GPS data...")
    
    for row in rows:
        s_id = row[0]
        name = row[1]
        
        # Random offset ~1-5km
        lat_offset = (random.random() - 0.5) * 0.05
        lng_offset = (random.random() - 0.5) * 0.05
        
        new_lat = base_lat + lat_offset
        new_lng = base_lng + lng_offset
        
        cur.execute("UPDATE students SET lat = %s, lng = %s WHERE id = %s", (new_lat, new_lng, s_id))
        print(f"   - Updated {name} -> {new_lat:.6f}, {new_lng:.6f}")
        
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Done! All students now have locations.")

if __name__ == "__main__":
    fix_gps()
