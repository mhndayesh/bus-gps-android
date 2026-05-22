#!/bin/bash
# Run this once to start the app and create all demo accounts.
# Usage: bash setup_demo.sh
set -e
cd "$(dirname "$0")"

echo "=== Starting stack ==="
docker compose up --build -d

echo "=== Waiting for app to be ready ==="
for i in $(seq 1 30); do
  if curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo "App is up."
    break
  fi
  echo "  waiting... ($i/30)"
  sleep 3
done

echo "=== Creating demo accounts ==="
python3 - <<'PYEOF'
import requests, sys

BASE = "http://localhost:5000"
s = requests.Session()

def csrf():
    return s.get(f"{BASE}/api/csrf-token").json()["csrf_token"]

def post(path, data):
    r = s.post(f"{BASE}{path}", json={**data, "csrf_token": csrf()},
               headers={"X-CSRFToken": csrf()})
    return r

# Login as Super Admin
r = s.get(f"{BASE}/login")
from html.parser import HTMLParser
class T(HTMLParser):
    tok = ""
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("name") == "csrf_token": self.tok = d.get("value","")
p = T(); p.feed(r.text); tok = p.tok

r = s.post(f"{BASE}/login", data={"username":"Super Admin","password":"Admin123!","csrf_token":tok})
if "/admin" not in r.url:
    print("ERROR: Super Admin login failed — check INITIAL_ADMIN_PASSWORD=Admin123! in docker-compose.yml")
    sys.exit(1)
print("Logged in as Super Admin")

# Create school + school admin
r = post("/api/create_school_admin", {
    "school_name": "Demo School",
    "username":    "schooladmin",
    "password":    "School123!",
})
if not r.ok:
    print(f"School admin: {r.text}")
else:
    school_id = r.json().get("school_id")
    print(f"Created School Admin  →  school_id={school_id}")

# Get school id if creation was skipped (already exists)
if not r.ok:
    schools = s.get(f"{BASE}/api/get_schools").json()
    school_id = next((sc["id"] for sc in schools if sc["name"] == "Demo School"), schools[0]["id"])

# Create driver
r = post("/api/create_driver", {
    "username":  "driver1",
    "password":  "Driver123!",
    "school_id": school_id,
    "name":      "Demo Driver",
})
print("Created Driver       " if r.ok else f"Driver error: {r.text}")
driver_id = r.json().get("id") if r.ok else None

# Create bus
r = post("/api/add_bus", {"plate": "DEMO-001", "school_id": school_id})
print("Created Bus          " if r.ok else f"Bus error: {r.text}")
bus_id = r.json().get("id") if r.ok else None

# Assign driver to bus
if driver_id and bus_id:
    r = post("/api/assign_driver", {"driver_id": driver_id, "bus_id": bus_id})
    print("Assigned driver to bus" if r.ok else f"Assign error: {r.text}")

# Create parent
r = post("/api/create_parent", {
    "username":  "parent1",
    "password":  "Parent123!",
    "school_id": school_id,
    "name":      "Demo Parent",
})
print("Created Parent       " if r.ok else f"Parent error: {r.text}")

print("""
=== DEMO ACCOUNTS ===
Role          Login page          Username       Password
────────────  ──────────────────  ─────────────  ────────────
Super Admin   /login              Super Admin    Admin123!
School Admin  /login              schooladmin    School123!
Driver        /driver/login       driver1        Driver123!
Parent        /parent/login       parent1        Parent123!
""")
PYEOF
