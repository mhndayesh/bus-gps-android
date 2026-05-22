#!/bin/bash
# Run this once to start the app and create all demo accounts.
# Usage: bash setup_demo.sh
set -e
cd "$(dirname "$0")"

echo "=== Starting stack ==="
docker compose up --build -d

echo "=== Waiting for app to be ready (DB migration runs on first request) ==="
READY=0
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 2>/dev/null || echo "000")
  if [ "$code" = "200" ] || [ "$code" = "302" ]; then
    echo "App is up (HTTP $code). Waiting 6s for DB migration to finish..."
    sleep 6
    READY=1
    break
  fi
  echo "  waiting... ($i/60)  [HTTP $code]"
  sleep 3
done

if [ "$READY" = "0" ]; then
  echo "ERROR: App did not come up after 3 minutes. Check logs with:"
  echo "  docker compose logs web"
  exit 1
fi

echo "=== Creating demo accounts ==="
python3 - <<'PYEOF'
import requests, sys, time

BASE = "http://localhost:5000"
s = requests.Session()

# Retry wrapper for the first few requests while eventlet settles
def get_retry(url, retries=5):
    for i in range(retries):
        try:
            r = s.get(url, timeout=10)
            return r
        except Exception as e:
            if i == retries - 1: raise
            print(f"  retrying ({i+1}/{retries})...")
            time.sleep(2)

def csrf():
    return s.get(f"{BASE}/api/csrf-token", timeout=10).json()["csrf_token"]

def post(path, data):
    r = s.post(f"{BASE}{path}", json={**data, "csrf_token": csrf()},
               headers={"X-CSRFToken": csrf()}, timeout=10)
    return r

# Login as Super Admin
r = get_retry(f"{BASE}/login")
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
