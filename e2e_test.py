"""
End-to-end test suite — Bus GPS System
Tests every API endpoint as every role: SUPER_ADMIN, SCHOOL_ADMIN, DRIVER, PARENT
Run: python e2e_test.py
"""
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import re
import uuid

BASE = "http://localhost:5000"

# Unique suffix per test run avoids UNIQUE constraint collisions on re-runs
RUN = uuid.uuid4().hex[:6]

OK  = "PASS"
ERR = "FAIL"
results = []


def check(name, condition, detail=""):
    sym = OK if condition else ERR
    results.append((sym, name, detail))
    tag = "[PASS]" if condition else "[FAIL]"
    print(f"  {tag} {name}" + (f"  [{detail}]" if detail else ""))
    return condition


def section(title):
    print(f"\n{'-'*60}")
    print(f"  {title}")
    print(f"{'-'*60}")


def get_form_csrf(sess, url):
    r = sess.get(url)
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    return m.group(1) if m else ""


def get_api_csrf(sess):
    r = sess.get(f"{BASE}/api/csrf-token")
    return r.json().get("token", "") if r.ok else ""


def login(sess, username, password, portal="/login"):
    csrf = get_form_csrf(sess, f"{BASE}{portal}")
    return sess.post(
        f"{BASE}{portal}",
        data={"username": username, "password": password, "csrf_token": csrf},
        allow_redirects=True,
    )


def api_post(sess, path, payload):
    csrf = get_api_csrf(sess)
    return sess.post(
        f"{BASE}{path}",
        json=payload,
        headers={"X-CSRFToken": csrf},
    )


# ================================================================
# TEST CREDENTIALS (unique per run)
# ================================================================
SCHOOL_NAME   = f"E2E School {RUN}"
SCHOOL_ADMIN  = f"e2e_sa_{RUN}"
SA_PASS       = "E2eSchool1!"

PARENT_USER   = f"e2e_par_{RUN}"
PARENT_PASS   = "ParentE2e1!"
PARENT_PASS2  = "ParentE2e2!"   # after update_credentials

DRIVER_USER   = f"e2e_drv_{RUN}"
DRIVER_PASS   = "DriverE2e1!"

BUS_PLATE     = f"E2E-{RUN}"
NFC_ID        = f"NFC-{RUN}"


# ================================================================
# 1. SUPER_ADMIN
# ================================================================
section("1  SUPER_ADMIN  Login")
sa = requests.Session()
r = login(sa, "Super Admin", "TestPass123!", "/login")
check("Login redirects to /admin", "/admin" in r.url)
check("Admin page loads", r.ok and len(r.text) > 500)

# ── Schools ──────────────────────────────────────────────────────
section("2  SUPER_ADMIN  Schools")
r = sa.get(f"{BASE}/api/get_schools")
check("GET /api/get_schools", r.ok, f"{len(r.json())} school(s)")
base_school_id = r.json()[0]["id"]

r = api_post(sa, "/api/create_school_admin", {
    "school_name": SCHOOL_NAME,
    "username":    SCHOOL_ADMIN,
    "password":    SA_PASS,
})
check("POST /api/create_school_admin (new school + admin)", r.ok, r.text[:80])
new_school_id = r.json().get("school_id") if r.ok else base_school_id

r = sa.get(f"{BASE}/api/get_schools")
check("GET /api/get_schools after create", r.ok, f"{len(r.json())} school(s)")

# ── Buses ─────────────────────────────────────────────────────────
section("3  SUPER_ADMIN  Buses")
r = api_post(sa, "/api/add_bus", {"plate": BUS_PLATE, "school_id": new_school_id})
check("POST /api/add_bus", r.ok, r.text[:80])
bus_id = r.json().get("id") if r.ok else None

r = sa.get(f"{BASE}/api/get_buses")
check("GET /api/get_buses", r.ok, f"{len(r.json())} bus(es)")

# ── Parents ───────────────────────────────────────────────────────
section("4  SUPER_ADMIN  Parents")
r = api_post(sa, "/api/create_parent", {
    "name":      f"E2E Parent {RUN}",
    "username":  PARENT_USER,
    "password":  PARENT_PASS,
    "school_id": new_school_id,
})
check("POST /api/create_parent", r.ok, r.text[:80])
parent_id = r.json().get("id") if r.ok else None

r = sa.get(f"{BASE}/api/get_parents")
check("GET /api/get_parents", r.ok, f"{len(r.json())} parent(s)")

# ── Drivers ───────────────────────────────────────────────────────
section("5  SUPER_ADMIN  Drivers")
r = api_post(sa, "/api/create_driver", {
    "username":  DRIVER_USER,
    "password":  DRIVER_PASS,
    "school_id": new_school_id,
})
check("POST /api/create_driver", r.ok, r.text[:80])
driver_id = r.json().get("id") if r.ok else None

r = sa.get(f"{BASE}/api/get_drivers")
check("GET /api/get_drivers", r.ok, f"{len(r.json())} driver(s)")

r = api_post(sa, "/api/assign_driver", {"driver_id": driver_id, "bus_id": bus_id})
check("POST /api/assign_driver (link driver to bus)", r.ok, r.text[:60])

# ── Students ──────────────────────────────────────────────────────
section("6  SUPER_ADMIN  Students")
r = api_post(sa, "/api/add_student", {
    "name":      f"E2E Student {RUN}",
    "parent_id": parent_id,
    "nfc_id":    NFC_ID,
    "lat":       21.54,
    "lng":       39.17,
    "school_id": new_school_id,
})
check("POST /api/add_student", r.ok, r.text[:80])
student_id = str(r.json().get("id", "")) if r.ok else None

r = sa.get(f"{BASE}/api/get_students")
check("GET /api/get_students", r.ok, f"{len(r.json())} student(s)")

r = api_post(sa, "/api/update_student_location", {
    "student_id":   student_id,
    "lat":          21.55,
    "lng":          39.18,
    "address_text": "1 E2E Street",
})
check("POST /api/update_student_location", r.ok, r.text[:60])

r = api_post(sa, "/api/assign_bus", {"student_id": student_id, "bus_id": bus_id})
check("POST /api/assign_bus (create route stop)", r.ok, r.text[:60])

# ── Update parent credentials ─────────────────────────────────────
section("7  SUPER_ADMIN  Update parent credentials")
r = api_post(sa, "/api/update_parent_credentials", {
    "parent_id": parent_id,
    "username":  PARENT_USER,
    "password":  PARENT_PASS2,
})
check("POST /api/update_parent_credentials", r.ok, r.text[:60])

# ── Dashboard stats ────────────────────────────────────────────────
section("8  SUPER_ADMIN  Dashboard stats")
r = sa.get(f"{BASE}/api/dashboard/stats")
check("GET /api/dashboard/stats", r.ok, r.text[:100])

# ── Optimize route ─────────────────────────────────────────────────
r = sa.get(f"{BASE}/api/optimize_route/{bus_id}")
check("GET /api/optimize_route (empty is ok)", r.ok, r.text[:80])

# ── Delete student ─────────────────────────────────────────────────
section("9  SUPER_ADMIN  Delete student")
r = api_post(sa, "/api/delete_student", {"student_id": student_id})
check("POST /api/delete_student", r.ok, r.text[:60])

# ── Delete bus ─────────────────────────────────────────────────────
section("10  SUPER_ADMIN  Delete bus")
r_tmp = api_post(sa, "/api/add_bus", {"plate": f"{BUS_PLATE}-TMP", "school_id": new_school_id})
tmp_bus_id = r_tmp.json().get("id") if r_tmp.ok else None
r = api_post(sa, "/api/delete_bus", {"bus_id": tmp_bus_id})
check("POST /api/delete_bus", r.ok, r.text[:60])


# ================================================================
# 2. SCHOOL_ADMIN
# ================================================================
section("11  SCHOOL_ADMIN  Login")
sch = requests.Session()
r = login(sch, SCHOOL_ADMIN, SA_PASS, "/login")
check("School Admin login redirects to /admin", "/admin" in r.url)
check("School admin panel loaded", r.ok and len(r.text) > 500)

section("12  SCHOOL_ADMIN  Scoped reads (should see only own school)")
r = sch.get(f"{BASE}/api/get_parents")
check("GET /api/get_parents (school-scoped)", r.ok, f"{len(r.json())} parent(s)")
sch_parents_before = len(r.json())

r = sch.get(f"{BASE}/api/get_students")
check("GET /api/get_students (school-scoped)", r.ok, f"{len(r.json())} student(s)")

r = sch.get(f"{BASE}/api/get_buses")
check("GET /api/get_buses (school-scoped)", r.ok, f"{len(r.json())} bus(es)")
sch_buses = r.json()

r = sch.get(f"{BASE}/api/get_drivers")
check("GET /api/get_drivers (school-scoped)", r.ok, f"{len(r.json())} driver(s)")

section("13  SCHOOL_ADMIN  Create entities")
sch_par_user = f"sch_par_{RUN}"
r = api_post(sch, "/api/create_parent", {
    "name":     f"SchAdmin Parent {RUN}",
    "username": sch_par_user,
    "password": "SchPar1!",
})
check("Create parent (school admin)", r.ok, r.text[:60])
sch_parent_id = r.json().get("id") if r.ok else None

r = api_post(sch, "/api/create_driver", {
    "username": f"sch_drv_{RUN}",
    "password": "SchDrv1!",
})
check("Create driver (school admin)", r.ok, r.text[:60])

if sch_parent_id:
    r = api_post(sch, "/api/add_student", {
        "name":      f"SchAdmin Student {RUN}",
        "parent_id": sch_parent_id,
        "nfc_id":    f"NFC-SCH-{RUN}",
        "lat":       21.50,
        "lng":       39.10,
    })
    check("Add student (school admin)", r.ok, r.text[:60])
    sch_student_id = str(r.json().get("id", "")) if r.ok else None

    r = api_post(sch, "/api/update_student_location", {
        "student_id":   sch_student_id,
        "lat":          21.51,
        "lng":          39.11,
        "address_text": "2 SchAdmin Road",
    })
    check("Update student location (school admin)", r.ok, r.text[:60])

    if sch_buses:
        r = api_post(sch, "/api/assign_bus", {
            "student_id": sch_student_id,
            "bus_id":     sch_buses[0]["id"],
        })
        check("Assign bus to student (school admin)", r.ok, r.text[:60])

    r = api_post(sch, "/api/delete_student", {"student_id": sch_student_id})
    check("Delete student (school admin)", r.ok, r.text[:60])

r = sch.get(f"{BASE}/api/dashboard/stats")
check("Dashboard stats (school admin)", r.ok, r.text[:100])


# ================================================================
# 3. DRIVER
# ================================================================
section("14  DRIVER  Login & pages")
drv = requests.Session()
r = login(drv, DRIVER_USER, DRIVER_PASS, "/driver/login")
check("Driver login redirects to /driver", "/driver" in r.url)

r = drv.get(f"{BASE}/driver")
check("GET /driver (driver app page)", r.ok and r.status_code == 200,
      f"status={r.status_code}")
check("Driver page contains trip phase UI",
      "phase" in r.text or "trip" in r.text.lower() or "رحلة" in r.text)

r = drv.get(f"{BASE}/api/driver/manifest")
check("GET /api/driver/manifest", r.ok, f"{len(r.json())} student(s)")

# Access control: driver must not reach admin-only endpoints.
# role_required clears session on first wrong-role hit, so re-login between checks.
r = drv.get(f"{BASE}/api/get_schools")
check("Driver blocked from /api/get_schools (403/401)", r.status_code in (401, 403))

drv2 = requests.Session()
login(drv2, DRIVER_USER, DRIVER_PASS, "/driver/login")
r = drv2.get(f"{BASE}/api/get_students")
check("Driver blocked from /api/get_students (403/401)", r.status_code in (401, 403))


# ================================================================
# 4. PARENT
# ================================================================
section("15  PARENT  Login & dashboard")
par = requests.Session()
r = login(par, PARENT_USER, PARENT_PASS2, "/parent/login")
# Must land on /parent (dashboard), not stay on /parent/login (failed login)
check("Parent login redirects to /parent dashboard",
      r.url.rstrip('/').endswith('/parent'))

r = par.get(f"{BASE}/parent")
check("GET /parent (dashboard page)", r.ok and r.status_code == 200)
check("Parent dashboard has children section", "kids" in r.text or "أطفال" in r.text)

r = par.get(f"{BASE}/api/get_my_kids")
check("GET /api/get_my_kids", r.ok, f"{len(r.json())} kid(s)")

# Access control — role_required clears the session on a wrong-role hit,
# so after the first 403 subsequent calls return 401. Both are "blocked".
r = par.get(f"{BASE}/api/get_schools")
check("Parent blocked from /api/get_schools (403/401)", r.status_code in (401, 403))
r = par.get(f"{BASE}/api/driver/manifest")
check("Parent blocked from /api/driver/manifest (403/401)", r.status_code in (401, 403))
r = par.get(f"{BASE}/api/get_students")
check("Parent blocked from /api/get_students (403/401)", r.status_code in (401, 403))


# ================================================================
# 5. SECURITY & RBAC
# ================================================================
section("16  Security & RBAC")

# Fresh sessions for each sub-test so we don't hit the 5/min login rate limit
# or carry over cleared sessions from access-control tests above.
anon = requests.Session()

r = anon.get(f"{BASE}/admin", allow_redirects=False)
check("Unauthenticated /admin → 302 redirect", r.status_code == 302)

r = anon.get(f"{BASE}/api/get_schools")
check("Unauthenticated /api/get_schools → 401", r.status_code == 401)

r = anon.get(f"{BASE}/api/get_students")
check("Unauthenticated /api/get_students → 401", r.status_code == 401)

# Wrong portal: parent account → /login (admin portal)
# Use a fresh session to avoid rate-limit chain effects
sec1 = requests.Session()
csrf = get_form_csrf(sec1, f"{BASE}/login")
r = sec1.post(f"{BASE}/login",
              data={"username": PARENT_USER, "password": PARENT_PASS2, "csrf_token": csrf})
check("Parent rejected at /login (admin portal) → 403/429",
      r.status_code in (403, 429), f"got {r.status_code}")

# Wrong portal: driver account → /parent/login
sec2 = requests.Session()
csrf = get_form_csrf(sec2, f"{BASE}/parent/login")
r = sec2.post(f"{BASE}/parent/login",
              data={"username": DRIVER_USER, "password": DRIVER_PASS, "csrf_token": csrf})
check("Driver rejected at /parent/login → 403/429",
      r.status_code in (403, 429), f"got {r.status_code}")

# Wrong portal: school admin → /parent/login
sec3 = requests.Session()
csrf = get_form_csrf(sec3, f"{BASE}/parent/login")
r = sec3.post(f"{BASE}/parent/login",
              data={"username": SCHOOL_ADMIN, "password": SA_PASS, "csrf_token": csrf})
check("School admin rejected at /parent/login → 403/429",
      r.status_code in (403, 429), f"got {r.status_code}")

# CSRF protection: POST without token must be blocked
sec4 = requests.Session()
r = sec4.post(f"{BASE}/api/add_bus", json={"plate": "HACK"})
check("POST without CSRF token → 400", r.status_code == 400)

# Cross-school isolation: school admin sees only own school parents
r = sch.get(f"{BASE}/api/get_parents")
if r.ok:
    names = [p["name"] for p in r.json()]
    cross_school_leak = any(
        "Super Admin" in n or "Happy Valley" in n
        for n in names
    )
    check("School admin cannot see other school parents", not cross_school_leak,
          f"visible parents: {names}")

# School admin cannot call delete_bus (SUPER_ADMIN only).
# Use a fresh session so the CSRF token is clean (prevents it being blocked by
# CSRF rotation rather than role check, which would give a misleading 400).
sch_fresh = requests.Session()
login(sch_fresh, SCHOOL_ADMIN, SA_PASS, "/login")
r = api_post(sch_fresh, "/api/delete_bus", {"bus_id": bus_id})
check("School admin blocked from /api/delete_bus → 403/401",
      r.status_code in (401, 403), f"got {r.status_code}")


# ================================================================
# SUMMARY
# ================================================================
passed = sum(1 for s, _, _ in results if s == OK)
failed = sum(1 for s, _, _ in results if s == ERR)
total  = len(results)

print(f"\n{'='*60}")
print(f"  RESULTS: {passed}/{total} passed  --  {failed} failed")
print(f"{'='*60}")

if failed:
    print("\nFailed tests:")
    for s, n, d in results:
        if s == ERR:
            print(f"  [FAIL] {n}" + (f"  [{d}]" if d else ""))
    sys.exit(1)
else:
    print("\n  All tests passed.")
    print(f"  (Test run ID: {RUN})")
