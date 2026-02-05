---
phase: 08-admin-interface
plan: 01
title: "Admin Foundation with HTTP Basic Auth"
subsystem: admin-ui
status: complete
completed: 2026-02-04
duration: ~4 minutes
tags: [authentication, jinja2, bootstrap, htmx, admin-ui]

dependency-graph:
  requires:
    - 07-03  # Schedule API for sidebar links
  provides:
    - verify_admin authentication dependency
    - admin base template with Marsh branding
    - admin router with protected routes
  affects:
    - 08-02  # Dashboard content
    - 08-03  # Insurers management
    - 08-04  # Recipients page
    - 08-05  # Schedules page
    - 08-06  # Settings page

tech-stack:
  added:
    - fastapi.security.HTTPBasic
    - fastapi.templating.Jinja2Templates
    - secrets (constant-time comparison)
  patterns:
    - HTTP Basic authentication
    - Jinja2 template inheritance
    - Named routes with url_for()

files:
  created:
    - app/routers/admin.py
    - app/templates/admin/base.html
    - app/templates/admin/dashboard.html
    - app/templates/admin/placeholder.html
  modified:
    - app/config.py
    - app/dependencies.py
    - app/main.py

key-links:
  - from: "app/routers/admin.py"
    to: "app/dependencies.py"
    via: "Depends(verify_admin)"
  - from: "app/main.py"
    to: "app/routers/admin.py"
    via: "include_router(admin.router)"

decisions:
  - decision: "HTTP Basic auth for admin pages"
    rationale: "Browser-native login prompt, no session management needed for MVP"
    alternative: "Cookie-based sessions"
  - decision: "Constant-time comparison for credentials"
    rationale: "Prevents timing attacks on password verification"
  - decision: "Empty password default forces env var configuration"
    rationale: "Prevents accidental deployment with default credentials"

metrics:
  tasks_completed: 3
  commits: 3
  tests_added: 0
  files_created: 4
  files_modified: 3
---

# Phase 08 Plan 01: Admin Foundation Summary

## One-liner
HTTP Basic auth with verify_admin dependency protecting admin routes, Marsh-branded base template with Bootstrap 5 and HTMX.

## What Was Built

### Task 1: Admin Auth Settings and Dependency
- Added `admin_username` and `admin_password` to Settings class
- Created `verify_admin` dependency with HTTPBasic security scheme
- Uses `secrets.compare_digest()` for constant-time password comparison
- Returns 401 with WWW-Authenticate header on auth failure
- Requires ADMIN_PASSWORD env var to be set (empty default)

### Task 2: Admin Router and Base Template
- Created admin router at `/admin` prefix with authentication
- Built base.html with Marsh branding:
  - CSS variables: `--marsh-blue: #00263e`, `--marsh-light-blue: #0077c8`
  - Fixed navbar with brand and username display
  - Sidebar with 6 navigation items (all named routes)
  - Bootstrap 5.3.3 and HTMX 2.0.4 via CDN
  - HTMX loading indicator CSS
- Created dashboard.html placeholder extending base
- Created placeholder.html for other pages

### Task 3: Router Registration
- Imported and registered admin router in main.py
- Admin interface accessible at `/admin`

## Files Created/Modified

| File | Purpose |
|------|---------|
| `app/config.py` | Added admin_username, admin_password settings |
| `app/dependencies.py` | Added verify_admin HTTPBasic dependency |
| `app/routers/admin.py` | Admin router with 6 named routes |
| `app/templates/admin/base.html` | Base template with Marsh branding |
| `app/templates/admin/dashboard.html` | Dashboard placeholder |
| `app/templates/admin/placeholder.html` | Generic placeholder for future pages |
| `app/main.py` | Registered admin router |

## Commits

| Hash | Message |
|------|---------|
| 50df3f6 | feat(08-01): add admin auth settings and verify_admin dependency |
| 88808c4 | feat(08-01): create admin router with base template and dashboard |
| 2571681 | feat(08-01): register admin router in main.py |

## Verification Results

| Criteria | Status |
|----------|--------|
| /admin returns 401 without credentials | PASS |
| WWW-Authenticate header triggers browser prompt | PASS |
| Valid credentials return 200 with dashboard | PASS |
| Invalid credentials return 401 | PASS |
| Marsh blue navbar rendered | PASS |
| Sidebar with 6 nav items | PASS |
| Bootstrap 5.3.3 CDN included | PASS |
| HTMX 2.0.4 CDN included | PASS |

## Requirements Addressed

| Requirement | Status | Notes |
|-------------|--------|-------|
| ADMN-01 | Partial | Web dashboard accessible (content in 08-02) |
| ADMN-02 | Complete | Basic authentication for admin pages |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Ready for Plan 08-02: Dashboard Content**

Dependencies met:
- [x] verify_admin dependency available
- [x] Base template with sidebar navigation
- [x] Dashboard route named and functional
- [x] Placeholder templates for all pages

Environment required:
- ADMIN_PASSWORD env var must be set for authentication

## Usage

```bash
# Set admin password
export ADMIN_PASSWORD=your-secure-password

# Start server
uvicorn app.main:app --reload

# Access admin interface
# Browser will prompt for credentials
# Default username: admin
```
