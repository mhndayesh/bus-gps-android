import psycopg2
import os

DB_HOST = "yamabiko.proxy.rlwy.net"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN"
DB_PORT = "27535"

try:
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    # Check columns in bus_manifest
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'bus_manifest';
    """)
    columns = cur.fetchall()
    
    print("📋 Columns in 'bus_manifest':")
    found_status = False
    for col in columns:
        print(f" - {col[0]} ({col[1]})")
        if col[0] == 'status':
            found_status = True
            
    if found_status:
        print("\n✅ 'status' column EXISTS!")
    else:
        print("\n❌ 'status' column MISSING!")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
