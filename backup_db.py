import psycopg2
import json
import os
import datetime

# Credentials (Hardcoded for Backup Script Ease)
DB_HOST = "yamabiko.proxy.rlwy.net"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN"
DB_PORT = "27535"

TABLES = ['schools', 'users', 'buses', 'students', 'route_stops', 'bus_manifest', 'trip_logs']

def backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"📦 Starting Backup to {backup_dir}...")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cur = conn.cursor()
        
        for table in TABLES:
            print(f"   Exporting {table}...", end=" ")
            try:
                cur.execute(f"SELECT * FROM {table}")
                rows = cur.fetchall()
                
                # Get column names
                colnames = [desc[0] for desc in cur.description]
                
                # Convert to List of Dicts
                data = []
                for row in rows:
                    item = {}
                    for i, val in enumerate(row):
                        # Handle DateTimes for JSON
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            val = val.isoformat()
                        item[colnames[i]] = val
                    data.append(item)
                
                # Write to file
                with open(f"{backup_dir}/{table}.json", 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"✅ ({len(data)} rows)")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        cur.close()
        conn.close()
        print(f"✅ Backup Complete! Saved to {backup_dir}")
        return backup_dir
        
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    backup()
