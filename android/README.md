# Bus GPS — Android App

Native Kotlin Android client for the Bus GPS school bus tracking system.  
Connects to the same Flask/Socket.IO backend as the web app — no backend changes required.

---

## Quick Start

### Prerequisites
- Android Studio Hedgehog (2023.1) or newer
- JDK 17+
- Android SDK 34

### Open the project
1. Launch Android Studio
2. **File → Open** → select the `android/` folder (this folder, not the parent)
3. Let Gradle sync finish (first time downloads ~200 MB of dependencies)

### Set your server URL
Open [app/build.gradle.kts](app/build.gradle.kts) and update the `BASE_URL` field:

```kotlin
buildTypes {
    debug {
        // Android emulator localhost:
        buildConfigField("String", "BASE_URL", "\"http://10.0.2.2:5000\"")
    }
    release {
        // Your Railway / production URL:
        buildConfigField("String", "BASE_URL", "\"https://your-app.up.railway.app\"")
    }
}
```

### Build & run
- **Emulator:** press the green ▶ Run button
- **Physical device:** enable USB debugging, plug in, press ▶
- **APK:** Build → Build Bundle(s) / APK(s) → Build APK(s)

---

## Architecture

```
android/
├── app/
│   ├── build.gradle.kts          # App-level build config + BASE_URL
│   ├── proguard-rules.pro        # R8 keep rules
│   └── src/main/
│       ├── AndroidManifest.xml   # Activities + permissions
│       └── java/com/busgps/android/
│           ├── App.kt            # Application class (OSMDroid init)
│           ├── network/          # HTTP + Socket.IO layer
│           ├── model/            # Data classes (Gson-serialized)
│           ├── repository/       # Business logic / API calls
│           └── ui/               # Activities, ViewModels, Adapters
├── gradle/
│   ├── libs.versions.toml        # Centralized dependency versions
│   └── wrapper/
│       └── gradle-wrapper.properties
├── build.gradle.kts              # Project-level build
├── settings.gradle.kts
└── UI_MAP.md                     # Visual screen map for designers
```

---

## User Roles & Screens

| Role | Login endpoint | Landing screen |
|------|---------------|----------------|
| Parent | `POST /parent/login` | Parent Dashboard |
| Driver | `POST /driver/login` | Driver App |
| School Admin | `POST /login` | Admin Dashboard |
| Super Admin | `POST /login` | Admin Dashboard (sees all schools) |

---

## Screens

### 1. Role Select (`RoleSelectActivity`)
The app's first screen. Three large buttons: **Parent**, **Driver**, **Admin**.  
Auto-skips to the correct dashboard if a valid session cookie is already saved.

### 2. Login screens (one per role)
- `ParentLoginActivity`
- `DriverLoginActivity`
- `AdminLoginActivity`

All share a single layout (`activity_login.xml`). Each posts form-encoded credentials to the matching Flask endpoint. On success (HTTP 302), the session cookie is saved and the user is forwarded to their dashboard.

### 3. Parent Dashboard (`ParentDashboardActivity`)
- **Live map** (OpenStreetMap via OSMDroid) — bus marker moves in real time
- **Child cards** — shows each child's name, boarding status (On Bus / At School), and bus plate
- Tapping a card while child is on bus centers the map on that bus
- Pull-to-refresh reloads children list

**Real-time events received:**
| Event | Action |
|-------|--------|
| `update_map` | Move bus marker on map |
| `student_status_update` | Update child's on-bus status |

### 4. Driver App (`DriverActivity`)
- **Live map** — self-marker updates as phone moves
- **Optimize Route** button — calls `GET /api/optimize_route/:busId` and pins stops on map
- **Student manifest** — list of all assigned students with Board / Drop buttons
- GPS location sent via Socket.IO `driver_gps_update` every ~2 seconds

**Socket.IO events emitted:**
| Event | When |
|-------|------|
| `driver_gps_update` | Every location update (FusedLocationProvider) |
| `manual_attendance` | Board or Drop button tapped |

### 5. Admin Dashboard (`AdminActivity`)
Tabbed interface with 5 tabs:

| Tab | Content | Actions |
|-----|---------|---------|
| Overview | Stats card: total buses, active buses, total students, on-bus count | — |
| Students | List with name, code, address | Add, Delete, Assign Bus |
| Buses | List with plate and ID | Assign Driver |
| Drivers | List | Add (create login) |
| Parents | List | Add (create login) |

FAB (➕) in bottom-right opens an add dialog for the current tab.

### 6. Super Admin (`SuperAdminActivity`)
List of all schools (name + ID). Super admins also see the Admin Dashboard with cross-school data.

---

## Network Layer

### `ApiClient`
- Built on **Retrofit 2** + **OkHttp 4**
- `PersistentCookieJar` saves the Flask session cookie to `SharedPreferences` so the user stays logged in between app restarts
- `CsrfInterceptor` (inline in OkHttp chain) automatically adds `X-CSRFToken` header to every POST/PUT/DELETE after the token is fetched from `GET /api/csrf-token`
- Redirect following is **disabled** — login success is detected by HTTP 302 response code

### `SocketManager`
- Singleton wrapping **socket.io-client-java 2.1.0** (compatible with Socket.IO 4.x server)
- Session cookie is read from the cookie jar and passed as a `Cookie` header on connection
- Reconnects automatically (up to 10 attempts, 1s delay)

---

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| Retrofit 2 | 2.11.0 | REST API calls |
| OkHttp 4 | 4.12.0 | HTTP client + logging |
| socket.io-client | 2.1.0 | Real-time Socket.IO |
| OSMDroid | 6.1.18 | OpenStreetMap (no API key needed) |
| Google Play Services Location | 21.3.0 | FusedLocationProvider for driver GPS |
| CameraX | 1.3.4 | Camera access (driver stream — future) |
| Material Components | 1.12.0 | UI components |
| Lifecycle ViewModel/LiveData | 2.8.3 | MVVM architecture |
| Kotlin Coroutines | 1.8.1 | Async API calls |
| Gson | 2.10.1 | JSON serialization |

---

## Permissions

| Permission | Used by |
|-----------|---------|
| `INTERNET` | All API + Socket.IO calls |
| `ACCESS_FINE_LOCATION` | Driver GPS tracking |
| `ACCESS_COARSE_LOCATION` | Driver GPS fallback |
| `CAMERA` | Driver camera stream (future) |
| `WRITE_EXTERNAL_STORAGE` | OSMDroid map tile cache (Android ≤ 9) |

---

## Session & Security

- **Cookies** are persisted in `SharedPreferences` under the key `cookies`
- **CSRF token** is fetched from `GET /api/csrf-token` before the first login POST, then cached in memory and added as `X-CSRFToken` to all subsequent state-changing requests
- **Logout** clears both the cookie jar and the `session` prefs, then returns to the Role Select screen
- **Auto-login** on app start: if a valid session cookie exists, the role stored in `session` prefs is used to jump directly to the correct dashboard

---

## Configuration Reference

| File | What to change |
|------|---------------|
| `app/build.gradle.kts` | `BASE_URL` for debug and release |
| `app/src/main/java/.../network/SocketManager.kt` | Socket transport options, reconnect policy |
| `app/src/main/res/values/colors.xml` | Brand colors |
| `app/src/main/res/values/strings.xml` | All user-facing text (Arabic translation: add `values-ar/strings.xml`) |
| `app/src/main/res/values/themes.xml` | App theme, button styles |

---

## Adding Arabic (RTL) Support

1. Create `app/src/main/res/values-ar/strings.xml` with Arabic translations
2. `android:supportsRtl="true"` is already set in `AndroidManifest.xml`
3. Layout files use `Start`/`End` (not `Left`/`Right`) — RTL mirrors automatically

---

## Roadmap

- [ ] Driver camera stream (CameraX → base64 → Socket.IO `camera_frame`)
- [ ] Push notifications for boarding/drop events (FCM)
- [ ] Arabic localization (`values-ar/strings.xml`)
- [ ] Dark mode (`values-night/themes.xml`)
- [ ] Offline map tile caching
- [ ] Super Admin: create school + admin from app
