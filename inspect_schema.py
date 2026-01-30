import psycopg2

def inspect_db():
    try:
        conn = psycopg2.connect("dbname=bus_tracking user=admin password=password host=localhost")
        cur = conn.cursor()
        
        tables = ['users', 'students', 'schools', 'buses', 'route_stops']
        
        print("--- DATABASE SCHEMA INSPECTION ---")
        for t in tables:
            cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{t}'")
            cols = cur.fetchall()
            print(f"\nTABLE: {t}")
            for c in cols:
                print(f"  - {c[0]} ({c[1]})")
                
        conn.close()
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    inspect_db()
