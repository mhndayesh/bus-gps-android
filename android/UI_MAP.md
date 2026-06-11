# Bus GPS Android — UI Map
> Visual reference for all screens, flows, and component slots.  
> Use this to plug in final designs, icons, and branding.

---

## Navigation Flow

```
┌─────────────────────────────────────────────────────────┐
│                      App Launch                         │
│           (checks saved session cookie)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
           ┌───────────▼───────────┐
           │   No session saved    │     Session exists
           │                       ├──────────────────────┐
           └───────────┬───────────┘                      │
                       │                                  ▼
           ┌───────────▼───────────┐         Jump to saved role's dashboard
           │    ROLE SELECT        │         (Parent / Driver / Admin)
           │  [Parent] [Driver]    │
           │      [Admin]          │
           └──┬────────┬────────┬──┘
              │        │        │
     ┌────────▼─┐  ┌───▼──┐  ┌─▼──────┐
     │ Parent   │  │Driver│  │ Admin  │
     │ Login    │  │Login │  │ Login  │
     └────┬─────┘  └──┬───┘  └───┬────┘
          │           │          │
          ▼           ▼          ▼
    Parent Dash   Driver App  Admin Dash
                             (+ Super Admin
                              if role=SUPER_ADMIN)
```

---

## Screen 1 — Role Select

**File:** `activity_role_select.xml` · `RoleSelectActivity.kt`

```
┌─────────────────────────────┐
│                             │
│         [APP LOGO]          │  ← 100×100dp image
│                             │
│         Bus GPS             │  ← App name, 32sp bold, primary color
│  Real-time school bus       │  ← Subtitle, 14sp, grey
│       tracking              │
│                             │
│      Who are you?           │  ← Label, 18sp
│                             │
│  ╔═══════════════════════╗  │
│  ║       PARENT          ║  │  ← Green button, icon left
│  ╚═══════════════════════╝  │
│                             │
│  ╔═══════════════════════╗  │
│  ║       DRIVER          ║  │  ← Blue button, icon left
│  ╚═══════════════════════╝  │
│                             │
│  ╔═══════════════════════╗  │
│  ║    SCHOOL ADMIN       ║  │  ← Red button, icon left
│  ╚═══════════════════════╝  │
│                             │
│            v1.0.0           │  ← Version string, bottom
└─────────────────────────────┘

DESIGN SLOTS:
  • App logo        → replace @mipmap/ic_launcher with branded bus icon
  • Background      → solid color (#F8F9FA) or gradient / illustration
  • Button icons    → family icon / steering wheel / admin badge
  • Font            → currently system default; swap to Tajawal for Arabic feel
  • Accent colors   → Green=#34A853 Blue=#1A73E8 Red=#EA4335 (change in colors.xml)
```

---

## Screen 2 — Login (shared layout, 3 instances)

**File:** `activity_login.xml` · `*LoginActivity.kt`

```
┌─────────────────────────────┐
│                             │
│         [APP LOGO]          │  ← 80×80dp
│                             │
│      Parent Login           │  ← tvRoleTitle — set per role in code
│  Track your child's bus     │  ← tvRoleSubtitle — set per role in code
│      in real time           │
│                             │
│  ┌─────────────────────┐   │
│  │ Username            │   │  ← Outlined TextInputLayout
│  └─────────────────────┘   │
│                             │
│  ┌─────────────────────┐   │
│  │ Password        👁  │   │  ← Password toggle built in
│  └─────────────────────┘   │
│                             │
│           [●●●]             │  ← ProgressBar (hidden until login tap)
│                             │
│  ╔═══════════════════════╗  │
│  ║         LOGIN         ║  │  ← Primary button, 56dp height
│  ╚═══════════════════════╝  │
│                             │
│   ← Back to role selection  │  ← Text link
│                             │
└─────────────────────────────┘

DESIGN SLOTS:
  • Hero area       → illustration per role (bus+family / driver / admin desk)
  • Error state     → Snackbar currently; could become inline field error
  • Loading state   → ProgressBar; could become button shimmer
  • "Forgot password" link → not yet wired (no backend endpoint)
```

---

## Screen 3 — Parent Dashboard

**File:** `activity_parent_dashboard.xml` · `ParentDashboardActivity.kt`

```
┌─────────────────────────────┐
│ My Children          LOGOUT │  ← Toolbar, primary blue
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │                       │  │
│  │    LIVE MAP           │  │  ← MapView 200dp tall
│  │   [🚌 Bus marker]     │  │    OSMDroid / OpenStreetMap tiles
│  │                       │  │    marker moves via socket update_map
│  └───────────────────────┘  │
│                             │
│  ╔═══════════════════════╗  │  ← Card (item_kid_status.xml)
│  ║  Ahmed Al-Rashid      ║  │    tvKidName — bold
│  ║  🟢 On Bus            ║  │    tvStatus — green if on bus, grey if not
│  ║  Plate: ABC-1234      ║  │    tvBusPlate
│  ║                   [→] ║  │    arrow → taps center map on bus
│  ╚═══════════════════════╝  │
│                             │
│  ╔═══════════════════════╗  │
│  ║  Sara Al-Rashid       ║  │
│  ║  ⚫ At School / Home  ║  │
│  ║  Plate: —             ║  │
│  ╚═══════════════════════╝  │
│                             │
│  (pull down to refresh)     │
└─────────────────────────────┘

REAL-TIME:
  • Bus marker position ← socket event "update_map"
  • Child on-bus status ← socket event "student_status_update"

DESIGN SLOTS:
  • Toolbar color/logo → currently flat color; add logo or gradient
  • Map style          → can switch to satellite, dark mode tiles in OSMDroid
  • Bus marker icon    → replace default pin with custom bus SVG
  • Status badge       → pill chip instead of plain text
  • Empty state        → "No children registered" text; add illustration
  • Child avatar       → circular initial avatar per child name
```

---

## Screen 4 — Driver App

**File:** `activity_driver.xml` · `DriverActivity.kt`

```
┌─────────────────────────────┐
│ 12 students          LOGOUT │  ← Toolbar (tvStudentCount), blue
├─────────────────────────────┤
│                             │
│  ┌───────────────────────┐  │
│  │                       │  │
│  │    LIVE MAP           │  │  ← MapView 180dp tall
│  │   [📍 My Location]   │  │    Self-marker updated by GPS
│  │   [📌 Stop 1]        │  │    Route stop markers after optimize
│  │   [📌 Stop 2]        │  │
│  └───────────────────────┘  │
│                             │
│  ╔═══════════════════════╗  │
│  ║   OPTIMIZE ROUTE  🗺  ║  │  ← Green button
│  ╚═══════════════════════╝  │
│                             │
│  ════ Student Manifest ═══  │
│                             │
│  ╔═══════════════════════╗  │  ← Card (item_manifest.xml)
│  ║  Khalid Hassan        ║  │
│  ║  ⚫ Waiting           ║  │    status: Waiting / On Bus / Dropped Off
│  ║           [BOARD][DROP]║  │    two action buttons
│  ╚═══════════════════════╝  │
│                             │
│  ╔═══════════════════════╗  │
│  ║  Nora Alami           ║  │
│  ║  🟢 On Bus            ║  │
│  ║           [BOARD][DROP]║  │
│  ╚═══════════════════════╝  │
│                             │
│  (pull down to refresh)     │
└─────────────────────────────┘

GPS:
  • Location updates every 2s → emits socket "driver_gps_update"
  • Requires ACCESS_FINE_LOCATION permission (requested at runtime)

DESIGN SLOTS:
  • Toolbar color      → currently role_driver blue; could be brand color
  • Map style          → dark/satellite option for night driving
  • Stop marker icons  → numbered pins (1,2,3…) for route sequence
  • Status chips       → color-coded pill: grey=waiting green=boarded blue=dropped
  • Board/Drop buttons → icon-only buttons to save space on small screens
  • GPS status badge   → show "GPS Active 🟢" / "No GPS 🔴" in toolbar
```

---

## Screen 5 — Admin Dashboard

**File:** `activity_admin.xml` · `AdminActivity.kt`

```
┌─────────────────────────────┐
│ Admin Dashboard      LOGOUT │  ← Toolbar, red (#EA4335)
├─────────────────────────────┤
│[Overview][Students][Buses]  │  ← TabLayout, scrollable
│         [Drivers][Parents]  │
├─────────────────────────────┤
│                             │
│  ── TAB: Overview ──        │
│                             │
│  ┌──────────┬──────────┐   │
│  │ 🚌 8     │ ✅ 6     │   │  ← Stats grid card
│  │Total     │Active    │   │
│  │Buses     │Buses     │   │
│  ├──────────┼──────────┤   │
│  │ 👦 124   │ 🟢 87   │   │
│  │Students  │On Bus    │   │
│  └──────────┴──────────┘   │
│                             │
│  ── TAB: Students ──        │
│                             │
│  ╔═══════════════════════╗  │  ← Item card (item_student.xml)
│  ║ Ahmed Hassan          ║  │
│  ║ Code: STD-042         ║  │
│  ║ 12 Palm Street        ║  │
│  ║           [Bus] [✕]  ║  │  ← Assign Bus + Delete
│  ╚═══════════════════════╝  │
│                             │
│  ── TAB: Buses ──           │
│                             │
│  ╔═══════════════════════╗  │  ← Item card (item_bus.xml)
│  ║ ABC-1234              ║  │
│  ║ Bus #3                ║  │
│  ║         [Assign Driver]║  │
│  ╚═══════════════════════╝  │
│                             │
│  ── TAB: Drivers ──         │
│                             │
│  ╔═══════════════════════╗  │  ← Item card (item_driver.xml)
│  ║ Mohammed K.           ║  │
│  ║ ID: a3f9c1b2…         ║  │
│  ╚═══════════════════════╝  │
│                             │
│  ── TAB: Parents ──         │
│  (same structure as Drivers)│
│                             │
│                         [+] │  ← FAB bottom-right (opens add dialog)
└─────────────────────────────┘

ADD DIALOGS (triggered by FAB):
  Students → name + parent picker spinner
  Drivers  → username + password
  Parents  → name + username + password

DESIGN SLOTS:
  • Stats card    → animated counters, progress rings, trend arrows
  • Tab indicator → custom underline color / pill style
  • Item cards    → leading avatar/icon per type (bus icon, person icon)
  • FAB           → keep or replace with bottom sheet for multi-action
  • Search/filter → add search bar above RecyclerView (not yet implemented)
  • Empty state   → illustration per tab (no students yet / no buses etc.)
```

---

## Screen 6 — Super Admin

**File:** `activity_super_admin.xml` · `SuperAdminActivity.kt`

```
┌─────────────────────────────┐
│ 5 schools            LOGOUT │  ← Toolbar, purple
├─────────────────────────────┤
│                             │
│  ╔═══════════════════════╗  │  ← School card (item_school.xml)
│  ║ 🏫  Al-Noor School    ║  │    tvSchoolName
│  ║     ID: 1             ║  │    tvSchoolId
│  ╚═══════════════════════╝  │
│                             │
│  ╔═══════════════════════╗  │
│  ║ 🏫  Al-Salam Academy  ║  │
│  ║     ID: 2             ║  │
│  ╚═══════════════════════╝  │
│                             │
│  (pull down to refresh)     │
└─────────────────────────────┘

DESIGN SLOTS:
  • School icon     → school/building SVG instead of system drawable
  • Tap action      → open that school's full admin view (not yet wired)
  • Add school FAB  → create school + admin dialog (not yet implemented)
  • Stats per school → student count, bus count inline on card
```

---

## Shared Components

### Toolbar (all screens)
```
┌──────────────────────────────────────┐
│ [optional logo] Screen Title  LOGOUT │
│                                      │
│ COLOR: role-specific                 │
│   Parent → primary blue #1A73E8      │
│   Driver → role_driver blue #1A73E8  │
│   Admin  → role_admin  red  #EA4335  │
│   Super  → purple #6200EE            │
└──────────────────────────────────────┘
DESIGN SLOT: replace flat color toolbar with gradient or image header
```

### Snackbar (feedback messages)
```
┌──────────────────────────────────────┐
│  ✅ Student added          [DISMISS] │  ← bottom of screen, auto-dismiss
└──────────────────────────────────────┘
DESIGN SLOT: custom styled snackbar with icon
```

### Progress/Loading
```
Currently: Snackbar — SwipeRefreshLayout spinner (pull-to-refresh)
DESIGN SLOT: skeleton loading cards (shimmer effect) for better UX
```

---

## Color Palette

| Token | Hex | Used for |
|-------|-----|---------|
| `primary` | `#1A73E8` | Buttons, links, toolbar |
| `primary_dark` | `#1558C0` | Status bar |
| `secondary` | `#34A853` | Success, On Bus, Optimize btn |
| `role_parent` | `#34A853` | Parent role button |
| `role_driver` | `#1A73E8` | Driver role button |
| `role_admin` | `#EA4335` | Admin role button |
| `background` | `#F8F9FA` | Screen backgrounds |
| `surface` | `#FFFFFF` | Cards |
| `error` | `#EA4335` | Delete, error states |
| `text_secondary` | `#5F6368` | Subtitles, metadata |

> All tokens live in `app/src/main/res/values/colors.xml` — change once, applies everywhere.

---

## Typography Scale

| Role | Size | Weight | Used for |
|------|------|--------|---------|
| Display | 32sp | Bold | App name on role select |
| Headline | 24sp | Bold | Login screen title |
| Title | 18sp | Bold | Toolbar, section headers |
| Body | 15–16sp | Regular | Student names, list items |
| Caption | 12–13sp | Regular | IDs, addresses, subtitles |
| Label | 11–12sp | Regular | Buttons (small), chips |

> Font: currently system default. To use **Tajawal** (Arabic-compatible):  
> 1. Add font to `res/font/tajawal_regular.ttf`  
> 2. Set `android:fontFamily="@font/tajawal_regular"` in `themes.xml`

---

## Icon Slots (replace with branded icons)

| Location | Current | Recommended |
|----------|---------|-------------|
| App launcher | Adaptive icon placeholder | Custom bus SVG |
| Role Select — Parent btn | `ic_menu_myplaces` | Family / child icon |
| Role Select — Driver btn | `ic_menu_directions` | Steering wheel icon |
| Role Select — Admin btn | `ic_menu_manage` | Shield / badge icon |
| Bus marker on map | Default OSMDroid pin | Custom bus top-down SVG |
| School card | `ic_menu_agenda` | Building / school icon |
| FAB | `ic_input_add` | Plus icon (already correct) |

---

## Responsive Breakpoints

The app is portrait-only (`screenOrientation="portrait"` in manifest).  
All layouts use `ConstraintLayout` / `LinearLayout` with `dp` units.

| Device class | Notes |
|-------------|-------|
| Small (360dp) | All content fits; map height may feel tight |
| Normal (390dp) | Target design size |
| Large/tablet | No tablet-specific layout yet; add `layout-sw600dp/` variants |
