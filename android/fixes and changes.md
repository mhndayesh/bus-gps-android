# Fixes and Changes

This document tracks the fixes, architectural improvements, and compatibility updates made to the BusGPS Android project.

## 1. Build & Compatibility Fixes

### 16 KB Page Size Compatibility
*   **Issue:** The app showed a compatibility warning: "This app isn't 16 KB compatible. ELF alignment check failed."
*   **Fix:** 
    *   Updated **Android Gradle Plugin (AGP)** from `8.3.2` to `8.7.2`.
    *   Updated **Gradle Wrapper** from `8.6` to `8.10.2`.
    *   Updated **compileSdk** and **targetSdk** to `35`.
    *   Updated **CameraX** dependencies to `1.4.0` (stable version compatible with SDK 35).
    *   Added `packaging { jniLibs { useLegacyPackaging = false } }` to `app/build.gradle.kts` to force native library alignment.
    *   These updates ensure native libraries are correctly aligned to 16 KB boundaries for modern Android hardware.

### Adaptive Icon & Themed Icons
*   **Issue:** Build failed because `<adaptive-icon>` was in a folder used by older devices (API < 26).
*   **Fix:** 
    *   Moved adaptive icons to `mipmap-anydpi-v26/`.
    *   Created legacy vector icons in `mipmap-mdpi/`.
    *   Added `<monochrome>` support to enable themed icons on Android 13+.

### Missing KTX Dependencies
*   **Issue:** Compilation failed because `by viewModels()` was used without the required KTX libraries.
*   **Fix:** Added `androidx.activity:activity-ktx` and `androidx.fragment:fragment-ktx` to the project.

## 2. Network & Connectivity Fixes

### Base URL & Retrofit Initialization
*   **Issue:** `BASE_URL` was missing a trailing slash (`/`), which causes Retrofit to fail at runtime.
*   **Fix:** Added trailing slashes to all URL definitions in `app/build.gradle.kts`.

### API Client Initialization
*   **Issue:** `ApiClient` was never initialized in the `Application` class, causing crashes on any network call.
*   **Fix:** Added `ApiClient.init(this)` to `App.kt`.

### Physical Device Connectivity & Multi-Platform Support
*   **Issue:** App worked on emulator (`10.0.2.2`) but not on physical phones or outside the local network.
*   **Fix:** Pointed all build types (`defaultConfig`, `debug`, `release`) to the production Railway URL:
    ```
    https://bus-gps-system-production.up.railway.app/
    ```
    Both the **web browser** and the **Android app** now connect to the same Railway backend. No local server is required — the app works on any phone with an internet connection, anywhere.

### CSRF & Session Security
*   **Issue:** Redundant network calls for CSRF tokens and lost session cookies on app restart.
*   **Fix:** 
    *   Optimized `AuthRepository` to fetch and cache the CSRF token once.
    *   Updated `PersistentCookieJar` to correctly save and restore cookie expiration timestamps (`expiresAt`).

### Socket.IO Authentication
*   **Issue:** Real-time updates failed when the server URL included a port number (common in dev environments).
*   **Fix:** Improved `getCookiesForSocket` to correctly parse URLs with ports when attaching session cookies to the socket connection.

## 3. UI/UX Improvements

### Parent Map Stability
*   **Issue:** Map would automatically "jump" or re-center whenever *any* bus moved, even if it wasn't the child's bus.
*   **Fix:** Added a `selectedBusId` filter. The map now only re-centers when the specific bus the parent is tracking sends an update.

## 4. Cross-Platform API Compatibility Fixes

### Type Mismatches Between Flask Responses and Android Models
*   **Issue:** After pointing the app at the Railway production backend, several screens would silently fail to load due to Gson parse errors caused by type mismatches between what Flask returned and what the Android models expected.
*   **Fixes applied:**

    | Endpoint | Field | Flask returned | Android expected | Fix |
    |---|---|---|---|---|
    | `GET /api/get_buses` | `id` | `str(int)` e.g. `"3"` | `Int` | Changed `Bus.id` to `String` |
    | `GET /api/get_drivers` | `id` | raw `Int` | `String` | Flask now returns `str(r[0])` |
    | `GET /api/get_drivers` | `school_id` | `""` (empty string) | `Int?` | Flask now returns `None` (null) |
    | `GET /api/driver/manifest` | `id` | raw `Int` | `String` | Flask now returns `str(r[0])` |

*   **Cascade fixes in Android** (all caused by `Bus.id: Int → String`):
    *   `AssignBusRequest.busId` and `AssignDriverRequest.busId` changed to `String`
    *   `BusAdapter`, `AdminActivity`, `AdminViewModel`, `DataRepository` updated accordingly
    *   Flask `assign_bus` and `assign_driver` now explicitly cast `bus_id` to `int()` to safely accept both string and integer JSON values

## 5. Super Admin Login & Role Detection Fix

### Hardcoded Role After Admin Login
*   **Issue:** `AdminLoginActivity` always saved `role = "SCHOOL_ADMIN"` after a successful admin login, even when the actual user was a `SUPER_ADMIN`. This meant Super Admin users were always sent to `AdminActivity` (school view) instead of `SuperAdminActivity` (multi-school view).
*   **Fix:**
    *   Added `GET /api/me` endpoint to Flask — returns `{ role, name }` for the current session.
    *   After a successful login, `AdminLoginActivity` calls `/api/me` to fetch the real role.
    *   If role is `SUPER_ADMIN` → navigates to `SuperAdminActivity`. Otherwise → `AdminActivity`.
    *   Added `MeResponse` model and `getMe()` to `ApiService`.

### Super Admin Password Reset
*   **Issue:** `INITIAL_ADMIN_PASSWORD` env var was not set on Railway, so the Super Admin password was an unknown random value generated at first deploy.
*   **Fix:** Password reset directly in the Railway DB to `Admin123!`.
    *   **Credentials:** Username `Super Admin`, Password `Admin123!`

---
*Last Updated: June 2026*
