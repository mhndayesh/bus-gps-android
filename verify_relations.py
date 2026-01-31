import psycopg2
import os

# CREDENTIALS (from your create_tables.py)
DB_HOST = "yamabiko.proxy.rlwy.net"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "yskvrNocmTymfEkzyhpHXTKdKHIcxvDN"
DB_PORT = "27535"

def verify_data():
    print(f"🔌 Connecting to {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
        )
        cur = conn.cursor()

        print("\n--- 1. SCHOOLS ---")
        cur.execute("SELECT id, name FROM schools")
        schools = cur.fetchall()
        for s in schools:
            print(f"School ID: {s[0]} | Name: {s[1]}")

        print("\n--- 2. PARENTS (Users where role='PARENT') ---")
        cur.execute("SELECT id, name, school_id FROM users WHERE role='PARENT'")
        parents = cur.fetchall()
        parent_map = {}
        for p in parents:
            # Check for whitespace in ID
            raw_id = p[0]
            clean_id = raw_id.strip()
            warn = ""
            if raw_id != clean_id: warn = " (⚠️ WHITESPACE DETECTED)"
            
            print(f"Parent ID: '{raw_id}'{warn} | Name: {p[1]} | School ID: {p[2]}")
            parent_map[raw_id] = {"name": p[1], "school_id": p[2], "students": []}

        print("\n--- 3. STUDENTS ---")
        cur.execute("SELECT id, name, parent_id, school_id FROM students")
        students = cur.fetchall()
        
        for s in students:
            s_id, s_name, p_id, s_school_id = s
            s_p_id_raw = p_id
            
            match_status = "❌ ORPHAN (Parent not found)"
            if s_p_id_raw in parent_map:
                match_status = f"✅ Matches Parent: {parent_map[s_p_id_raw]['name']}"
                parent_map[s_p_id_raw]['students'].append(s_name)
                
                # Check School Match
                p_school_id = parent_map[s_p_id_raw]['school_id']
                if p_school_id != s_school_id:
                     match_status += f" | ⚠️ SCHOOL MISMATCH (Parent: {p_school_id}, Student: {s_school_id})"
            
            print(f"Student: {s_name} | Assigned Parent ID: '{s_p_id_raw}' | School ID: {s_school_id} -> {match_status}")

        print("\n--- 4. SUMMARY (Frontend View Simulation) ---")
        for pid, data in parent_map.items():
            print(f"Parent '{data['name']}' (ID: {pid}) has {len(data['students'])} students matched in DB: {data['students']}")
            if len(data['students']) == 0:
                print(f"   ⚠️ This parent will show NO Students in the dropdown.")

        conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_data()
