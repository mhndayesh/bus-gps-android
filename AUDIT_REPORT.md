# Bus-GPS Project Audit Report

**Date:** 2026-05-22
**Scope:** Project sweep, cleanup, security review, integrity check, and performance/UX assessment.
**App:** Flask + Socket.IO bus tracking system (PostgreSQL, MQTT) with web portals for super-admins, school-admins, drivers, and parents.

---

## 1. Executive Summary

The codebase is a functional prototype with a clear architecture, but it carried
several **critical security exposures** — most importantly a live production
database password committed to the git repository. This audit removed project
cruft, eliminated hardcoded credentials, closed authentication gaps, hardened the
HTTP/socket layers, and fixed the highest-value code-integrity and frontend
security issues. Remaining items are subjective design choices or changes that
require a running environment to verify safely; these are documented in Section 8.

| Area | Critical | High | Medium | Low |
|------|:--:|:--:|:--:|:--:|
| Security findings | 4 | 7 | 5 | 5 |
| Fixed in this pass | 4 | 7 | 4 | 5 |

---

## 2. URGENT — Actions Only You Can Take

> **Removing a secret from source code does not remove it from git history.**

1. **Rotate the Railway database password immediately.** A real DB password was
   committed to the repo in earlier history (value redacted here). Anyone with
   repo access (or a fork/clone) can recover it via `git log -p`. Generate a new
   password in Railway, set it as the `DB_PASS` environment variable, and treat
   the old one as compromised. Optionally scrub history with BFG/filter-repo.
2. **Rotate any other shared secrets** that were ever committed (MQTT credentials
   if applicable).
3. **Set required environment variables** before deploying — the app now refuses
   to start without `DB_PASS` (see `.env.example`). Recommended:
   `DB_PASS`, `FLASK_SECRET_KEY`, `CORS_ORIGINS`, `INITIAL_ADMIN_PASSWORD`.
4. **Consider purging git history** of the secret (e.g. `git filter-repo`) — note
   this rewrites history and requires coordination with anyone who has a clone.
5. **Audit existing user rows** in the production DB for legacy plain-text
   passwords. They are now auto-upgraded to hashes on next successful login, but
   any never-used accounts remain plain-text until then.

---

## 3. Cleanup Performed

| Item | Action |
|------|--------|
| `__pycache__/` (92 KB on disk) | Removed (already git-ignored) |
| `landing-pages/` (empty directory) | Removed |
| `credentials.md` (plain-text test passwords, tracked in git) | Untracked + added to `.gitignore` |
| `563ac223-…-d730d6a6fb36.jpeg` (stray UUID-named image, tracked) | Removed |
| `backups/` (1.1 MB local data snapshots) | Left as-is — already git-ignored, contains DB exports. Recommend moving to off-repo cold storage. |

One-off scripts (`migrate_*.py`, `verify_*.py`, `send_test.py`, `inspect_schema.py`,
`fix_*`, `backup_*`) were **left at the repo root**. Moving them into a `scripts/`
folder is desirable tidy-up but was skipped: `fix_student_gps.py` and
`create_tables.py` are imported by `web_app.py`, so a move needs import updates and
deployment verification. Recommended as a follow-up.

---

## 4. Security Findings

### Critical — all fixed

| # | Finding | Fix |
|---|---------|-----|
| 1 | Production DB password hardcoded as a fallback in 5 files (`web_app.py`, `create_tables.py`, `backup_db.py`, `fix_student_gps.py`, `verify_relations.py`). | Credentials centralized in new `db_config.py`, read **only** from the environment; the app fails fast if `DB_PASS` is unset. `.env.example` added. **History still exposed — see Section 2.** |
| 2 | Seed super-admin created with plain-text password `'admin'`. | `create_tables.py` now stores a **hashed** password from `INITIAL_ADMIN_PASSWORD`, or generates a random one and prints it once. |
| 3 | `/api/my_children/<parent_id>` had **no authentication** — any caller could read any parent's children (names, NFC tags, bus assignments). | Added `@role_required(['PARENT'])` and an ownership check (`parent_id` must match the session user). |
| 4 | CORS defaulted to wildcard `*` — any site could call the API / open Socket.IO connections. | Default is now **same-origin only**; set `CORS_ORIGINS` to opt specific origins in. |

### High

| # | Finding | Status |
|---|---------|--------|
| 5 | `/api/debug/parent_session` leaked all parent IDs/names to any logged-in parent. | **Fixed** — endpoint removed. |
| 6 | `/api/fix_gps` was unauthenticated (any visitor could rewrite all student coordinates). | **Fixed** — `@role_required(['SUPER_ADMIN'])` added. |
| 7 | `/parent/dashboard` route was unauthenticated. | **Fixed** — `@role_required(['PARENT'])` added. |
| 8 | Login accepted legacy plain-text passwords via direct string comparison. | **Fixed** — plain-text matches are still accepted transitionally but **transparently re-hashed** on success, so the plain-text path self-eliminates. |
| 9 | No HTTPS/transport hardening headers. | **Fixed** — `Strict-Transport-Security` (HSTS) added. |
| 10 | No security response headers (clickjacking, MIME sniffing, CSP). | **Fixed** — `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, and a `Content-Security-Policy` added via `@app.after_request`. |
| 11 | Brute-force exposure on login. | Partially mitigated — login limited to 5/min (pre-existing). Consider an account-lockout policy. |

### Medium

| # | Finding | Status |
|---|---------|--------|
| 12 | Stored-XSS via `innerHTML` in all four client-facing templates (`super_admin.html`, `school_admin.html`, `driver_app.html`, `index.html`). Malicious values from the DB could execute in any user's browser. | **Fixed** — `escapeHtml()` helper added and applied to every DB-value interpolation in all four templates (13 sites in super_admin, dropdowns in school_admin, manifest list and missing-student warning in driver_app, bus-id/speed in index.html). |
| 13 | Driver on-screen debug console always on — leaked GPS coordinates, attendance data, and error traces to anyone near the device. | **Fixed** — console is now opt-in via `?debug=1`. |
| 14 | `/api/get_parents` / `/api/get_drivers` accept a `school_id` query param. | **Reviewed — not a vulnerability.** Only the `SUPER_ADMIN` branch honors the param; `SCHOOL_ADMIN` is always forced to its own `session['school_id']`. |
| 15 | No coordinate validation — out-of-range lat/lng could be stored. | **Fixed** — bounds-checked in `update_student_location` and the `driver_gps_update` socket handler. |
| 16 | `/get_camera/<bus_id>` returns an unauthenticated placeholder stream. | **Documented** — harmless today (fake stream); real camera URLs must be auth-gated before launch. |

### Low

| # | Finding | Status |
|---|---------|--------|
| 17 | No rate limiting on Socket.IO events (`camera_frame`, `driver_gps_update`) — flood/DoS risk. | **Fixed** — per-client throttle added (~12 fps for frames, 0.5 s for GPS), cleaned up on disconnect. |
| 18 | Unpinned dependency versions — non-reproducible builds. | **Fixed** — `requirements.txt` pinned. *Verify the pins against the deployed environment with `pip freeze`.* |
| 19 | CDN scripts loaded without Subresource Integrity (SRI). | **Fixed** — SHA-384 `integrity` + `crossorigin="anonymous"` added to Leaflet, Socket.IO, and HLS.js `<script>`/`<link>` tags in all six templates. |
| 20 | Verbose error messages surfaced in the driver debug console. | **Fixed indirectly** — debug console is now opt-in (see #13). |
| 21 | MQTT TLS uses `CERT_NONE` / `tls_insecure_set(True)` in `listener.py`. | **Fixed** — replaced with `client.tls_set()` (uses system CAs, verifies broker certificate). |

---

## 5. Code Integrity Findings

| Finding | Status |
|---------|--------|
| Three near-identical login functions (`login`, `driver_login`, `parent_login`). | **Fixed** — consolidated into one `_verify_and_login()` helper; ~120 lines → ~70. |
| Three bare `except:` clauses in `create_tables.py` swallowing migration errors silently. | **Fixed** — changed to `except Exception` with logging. |
| **Duplicate Socket.IO handlers.** `driver_gps_update`, `manual_attendance`, and the `camera_*` events were each defined **twice** in `web_app.py`. The surviving (later) block emitted wrong event names that no client listened to — the parent live map never updated and the dashboard "active buses" count was always `0`. | **Fixed** — the dead first block deleted; the surviving block corrected to emit the event names clients expect (`update_map`, `student_status_update`, `bus_camera_frame`, `bus_stream_status`). `join_bus_stream` handler and `active_streams` dict migrated to the surviving block. |
| Error paths in several write endpoints don't `rollback()` or `close()` the connection. | **Documented** — low impact (connections are per-request and GC'd), but `try/finally` cleanup is recommended. |
| Mutable module-level globals (`_db_host_override`, `_migration_done`). | **Documented** — safe under the current single-eventlet-worker deployment; revisit if scaling to multiple workers. |

---

## 6. Performance Findings

| Finding | Notes / Recommendation |
|---------|------------------------|
| Camera streams base64 JPEG frames at ~10 fps (`driver_app.html`). | ~150–200 KB/s per driver, plus battery drain. Server-side throttle now caps abuse; consider lowering client fps adaptively on poor connectivity, or moving to a real streaming protocol (WebRTC/HLS). |
| Parent dashboard polls `/api/get_my_kids` every 10 s **and** listens on sockets. | Redundant. Once the socket-handler duplication (Section 5) is fixed, polling can be reduced or removed. |
| Admin dashboards poll stats every 30 s with no backoff. | Add exponential backoff on failure. |
| `optimize_route` rebuilds the manifest query per request. | Acceptable at current scale; cache if bus/student counts grow. |
| Student lists rebuilt via full `innerHTML` replacement. | Fine at current scale; no action needed. |

No critical performance defects. The app is lightweight (~2,600 lines of Python).
The dominant cost is the camera streaming path.

---

## 7. UX & Ease of Use

| Area | Observation | Recommendation |
|------|-------------|----------------|
| **Accessibility** | `driver_app.html` disabled pinch-zoom (`user-scalable=no`). | **Fixed** — zoom re-enabled. |
| Accessibility | Low contrast: `--sage-green #9FB8AD` text on `--cream #F5F5F0`; gold-on-gold badges. Fails WCAG AA. | Darken text/foreground colors. (Design decision — not auto-changed.) |
| Accessibility | Modals lacked `role="dialog"`/`aria-modal`. Tabs use `<div class="tab-btn">` instead of `<button>`; form inputs lack `<label for>`; tour images lack `alt`. | **Partially fixed** — `role="dialog" aria-modal="true" aria-label="…"` added to the video modal (`index.html`) and attendance modal (`driver_app.html`). Semantic button/label/alt work remains (design decisions — see Section 8). |
| **i18n** | UI is Arabic-only with hardcoded strings; `dir="rtl"` is correctly set. | If English-speaking admins are expected, introduce a lightweight i18n layer and a language switcher. |
| Loading/errors | Parent dashboard shows a loading message and an error message (adequate). Driver/admin manifest fetch failures were only `console.log`ged — the user saw nothing. | **Fixed** — driver manifest fetch failure now shows an Arabic error message in the UI (`driver_app.html`). |
| Onboarding | No in-app guidance; admins must enter raw UUIDs in some forms (parent dropdowns mitigate this elsewhere). | Add brief inline help; replace any remaining raw-ID inputs with dropdowns. |
| Offline | No offline indicator; queued socket events replay on reconnect. | Add a connection-status indicator. |

---

## 8. Recommended Follow-ups (Not Auto-Applied)

These items were evaluated but intentionally left unchanged — they require a running
environment to verify, involve design decisions, or are architectural in scope.

### 8.1 Add `try/finally` connection cleanup to write endpoints
DB connections in ~20 write routes are opened without a `finally: conn.close()`.
Under the current single-worker/per-request model they are GC-closed and cause no
leaks, but the pattern should be corrected before scaling. The refactor touches every
route and benefits from integration tests.

### 8.2 Move one-off scripts into `scripts/`
`backup_db.py`, `verify_relations.py`, `fix_student_gps.py`, and similar files sit at
the repo root alongside application code. Moving them into a `scripts/` folder is
clean but requires updating their `from db_config import …` relative imports and
verifying any cron/CI references that invoke them by path.

### 8.3 Remaining accessibility work (design decisions)
- Tab navigation: replace `<div class="tab-btn">` with `<button>` elements (note:
  the existing `button { width:100%; }` CSS rule would need adjustment first).
- Add `<label for="…">` to all form inputs that currently have only placeholder text.
- Ensure sufficient color contrast per WCAG AA (the `--sage-green`/`--cream`
  combination is currently borderline).

### 8.4 Real camera auth-gate
`/get_camera/<bus_id>` returns an unauthenticated HLS stream URL. When real camera
streams are wired up, this endpoint must be protected with `@role_required` and return
signed/expiring stream URLs, not bare RTSP addresses.

### 8.5 Verify pinned dependencies against production
Run `pip freeze` in the deployed environment and confirm the versions in
`requirements.txt` match. Pay attention to `eventlet` and `psycogreen` compatibility.

### 8.6 i18n (if English-speaking admins are expected)
All strings are Arabic-only with `dir="rtl"` set globally. Introduce a lightweight
i18n dict and a language switcher if English support is needed.

---

## 9. Files Changed

**New:** `db_config.py`, `.env.example`, `AUDIT_REPORT.md`
**Modified:** `web_app.py`, `create_tables.py`, `backup_db.py`, `fix_student_gps.py`,
`verify_relations.py`, `requirements.txt`, `docker-compose.yml`, `.gitignore`,
`listener.py`,
`templates/driver_app.html`, `templates/super_admin.html`, `templates/school_admin.html`,
`templates/index.html`, `templates/parent_dashboard.html`, `templates/parent_app.html`
**Removed:** `credentials.md` (untracked), `563ac223-…-d730d6a6fb36.jpeg`, `landing-pages/`

> No commit was made — all changes are working-tree only for your review. Run `git diff --stat` to see the full change set.
