"""
Password Migration Script
Converts existing plain-text passwords to secure hashed passwords.

Run this ONCE after deploying the security update.
Usage: python migrate_passwords.py
"""

import psycopg2
import os
from werkzeug.security import generate_password_hash

# Database connection from environment
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_NAME = os.environ.get("DB_NAME", "bus_tracker_db")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "password")
DB_PORT = "5432"

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT
    )

def migrate_passwords():
    """Migrate all plain-text passwords to hashed passwords."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get all users with passwords that are NOT already hashed
    cur.execute("""
        SELECT id, name, password_hash 
        FROM users 
        WHERE password_hash IS NOT NULL 
          AND password_hash NOT LIKE 'pbkdf2:%'
          AND password_hash NOT LIKE 'scrypt:%'
    """)
    
    users = cur.fetchall()
    print(f"Found {len(users)} users with plain-text passwords")
    
    migrated = 0
    for user_id, name, plain_password in users:
        # Hash the existing plain-text password
        hashed = generate_password_hash(plain_password)
        
        cur.execute("""
            UPDATE users SET password_hash = %s WHERE id = %s
        """, (hashed, user_id))
        
        print(f"  ✅ Migrated: {name}")
        migrated += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n🎉 Migration complete! {migrated} passwords hashed.")

if __name__ == "__main__":
    print("🔒 Password Migration Script")
    print("=" * 40)
    migrate_passwords()
