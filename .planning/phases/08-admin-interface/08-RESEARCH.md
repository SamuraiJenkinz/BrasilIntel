# Phase 8: Admin Interface - Research

**Researched:** 2026-02-04
**Domain:** Web Dashboard / FastAPI Server-Side Rendering
**Confidence:** HIGH

## Summary

Research investigated frontend framework selection, authentication patterns, and UI component implementation for the BrasilIntel admin dashboard. The project already uses FastAPI + Jinja2 for report generation, making server-side rendering (SSR) the natural choice over a separate SPA framework.

The recommended approach is **FastAPI + Jinja2 + HTMX + Bootstrap 5**:
- **Jinja2** templates match existing report generation patterns (3 templates already in `app/templates/`)
- **HTMX** provides SPA-like interactivity (partial updates, form validation) without JavaScript framework complexity
- **Bootstrap 5** delivers professional admin UI with minimal custom CSS
- **HTTP Basic Auth** aligns with ADMN-02 requirement (username/password from environment variables)

This stack minimizes new dependencies while maximizing consistency with existing codebase patterns. The existing API endpoints (Phase 1-7) provide all necessary backend functionality; this phase adds UI layer only.

**Primary recommendation:** Use server-side rendering with Jinja2 templates enhanced by HTMX for interactivity, leveraging existing FastAPI APIs.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1.0 | HTML templating | Already used for reports, native FastAPI integration |
| HTMX | 2.0.x | AJAX/interactivity | No build step, CDN delivery, server-side paradigm |
| Bootstrap | 5.3.x | UI framework | Already used in report templates, comprehensive components |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | >=0.0.6 | File upload parsing | Already installed (FastAPI dependency for UploadFile) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTMX | React/Vue SPA | More complex build, separate deployment, duplicates API consumption |
| Bootstrap | Tailwind CSS | More custom work, no pre-built admin components |
| HTTP Basic | JWT/OAuth2 | Overkill for single-admin internal tool |

**Installation:**
No new Python dependencies required. HTMX and Bootstrap delivered via CDN.
```html
<!-- In base template head -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── templates/
│   ├── admin/           # NEW: Admin UI templates
│   │   ├── base.html    # Base template with nav, auth
│   │   ├── dashboard.html
│   │   ├── insurers.html
│   │   ├── import.html
│   │   ├── recipients.html
│   │   ├── schedules.html
│   │   ├── settings.html
│   │   └── partials/    # HTMX partial responses
│   │       ├── insurer_table.html
│   │       ├── import_preview.html
│   │       └── schedule_card.html
│   ├── report_basic.html     # Existing
│   ├── report_professional.html
│   └── alert_critical.html
├── routers/
│   └── admin.py         # NEW: Admin UI router
├── static/              # NEW: Static assets
│   ├── css/
│   │   └── admin.css    # Custom admin styles
│   └── js/
│       └── admin.js     # Minimal custom JS
└── dependencies.py      # Add auth dependency
```

### Pattern 1: HTMX Partial Updates
**What:** Return HTML fragments for partial page updates instead of full page reloads
**When to use:** Table filtering, form submissions, toggle buttons, status updates
**Example:**
```python
# Source: https://htmx.org/examples/inline-validation/
# Router returns partial HTML when hx-request header present

@router.get("/insurers/table")
async def insurers_table(
    request: Request,
    category: str = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    # Query insurers with filters
    insurers = query_insurers(db, category, search)

    # Check if HTMX request
    if request.headers.get("HX-Request"):
        # Return only table body partial
        return templates.TemplateResponse(
            "admin/partials/insurer_table.html",
            {"request": request, "insurers": insurers}
        )

    # Full page for direct navigation
    return templates.TemplateResponse(
        "admin/insurers.html",
        {"request": request, "insurers": insurers, "category": category}
    )
```

### Pattern 2: HTTP Basic Auth Dependency
**What:** Protect all admin routes with HTTP Basic authentication
**When to use:** All admin page endpoints
**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_admin(
    credentials: HTTPBasicCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> str:
    """Verify admin credentials from environment variables."""
    # Get expected credentials from config
    correct_username = settings.admin_username.encode("utf-8")
    correct_password = settings.admin_password.encode("utf-8")

    # Constant-time comparison prevents timing attacks
    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"), correct_username
    )
    password_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"), correct_password
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
```

### Pattern 3: HTMX Form with Preview
**What:** Two-phase form submission: preview then commit
**When to use:** Import page, destructive operations
**Example:**
```html
<!-- Source: https://htmx.org/examples/file-upload/ -->
<!-- Import form with drag-and-drop zone -->
<form id="import-form"
      hx-post="/admin/import/preview"
      hx-encoding="multipart/form-data"
      hx-target="#preview-area"
      hx-indicator="#upload-spinner">

    <div class="drop-zone" ondrop="handleDrop(event)" ondragover="handleDragOver(event)">
        <input type="file" name="file" accept=".xlsx,.xls" required>
        <p>Drag Excel file here or click to select</p>
    </div>

    <button type="submit" class="btn btn-primary">
        <span id="upload-spinner" class="htmx-indicator spinner-border spinner-border-sm"></span>
        Preview Import
    </button>
</form>

<div id="preview-area">
    <!-- HTMX will swap preview table here -->
</div>
```

### Pattern 4: Dashboard Summary Cards
**What:** Display key metrics in Bootstrap cards that auto-refresh
**When to use:** Dashboard page summary section
**Example:**
```html
<!-- Category status card with polling -->
<div class="card" hx-get="/admin/dashboard/card/health"
     hx-trigger="load, every 60s" hx-swap="innerHTML">
    <div class="card-body">
        <h5 class="card-title">Health</h5>
        <div class="d-flex justify-content-between">
            <span>Insurers: {{ health.insurer_count }}</span>
            <span class="badge bg-{{ health.status_color }}">{{ health.status }}</span>
        </div>
        <small class="text-muted">
            Last run: {{ health.last_run | timeago }}
            Next: {{ health.next_run | format_time }}
        </small>
    </div>
</div>
```

### Anti-Patterns to Avoid
- **Mixing JSON APIs with HTML endpoints:** Keep admin router separate from existing API routers
- **JavaScript-heavy state management:** Let server maintain state, HTMX handles DOM updates
- **Custom auth system:** Use FastAPI's built-in HTTPBasic, don't hand-roll session handling
- **Full page reloads for every action:** Use HTMX partial updates for better UX
- **Inline styles:** Use Bootstrap utility classes and CSS file for maintainability

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation UI | Custom JS validation | HTMX inline validation + server-side | Server is source of truth, avoid duplication |
| Drag-and-drop file upload | Custom dropzone JS | HTML5 drag events + HTMX | Minimal JS needed, works with existing endpoint |
| Modal dialogs | Custom modal system | Bootstrap modal + HTMX | Bootstrap handles accessibility, animations |
| Loading indicators | Custom spinner logic | HTMX hx-indicator | Built-in, consistent behavior |
| Tab navigation | Custom JS tabs | Bootstrap tabs + hx-trigger | Bootstrap handles accessibility, HTMX loads content |
| Data tables with sort/filter | Custom table component | Simple HTML + HTMX partial updates | Server-side filtering via existing API endpoints |
| Password masking toggle | Custom JS toggle | Bootstrap input-group + simple JS | Standard pattern, minimal code |
| Toast notifications | Custom notification system | Bootstrap toast + HTMX response headers | HX-Trigger header can trigger toasts |

**Key insight:** HTMX + Bootstrap 5 provide 90% of needed interactivity out-of-box. Custom JavaScript should be minimal (drag-drop zone, password reveal toggle).

## Common Pitfalls

### Pitfall 1: HTMX Partial vs Full Page Response Confusion
**What goes wrong:** Route returns wrong content type based on navigation method
**Why it happens:** Direct URL navigation expects full page, HTMX expects partial
**How to avoid:** Check `HX-Request` header to determine response type
**Warning signs:** Partial content showing in full browser window, missing navigation
```python
# Always check HX-Request header
is_htmx = request.headers.get("HX-Request") == "true"
template = "partials/table.html" if is_htmx else "full_page.html"
```

### Pitfall 2: Authentication Not Applied to Static Files
**What goes wrong:** Static CSS/JS files bypass auth, exposing admin asset URLs
**Why it happens:** StaticFiles mount doesn't use dependencies
**How to avoid:** Either: (1) embed admin CSS in templates, (2) use route-based serving with auth, or (3) accept that asset URLs alone don't leak data
**Warning signs:** CSS/JS accessible without login
```python
# Option: Route-based static serving with auth
@router.get("/admin/static/{path:path}")
async def admin_static(path: str, _: str = Depends(verify_admin)):
    return FileResponse(f"app/static/{path}")
```

### Pitfall 3: HTMX Form State Lost on Error
**What goes wrong:** File input clears after validation error, user must re-select
**Why it happens:** HTML file inputs can't be pre-populated for security
**How to avoid:** Show validation errors without full form swap, or store file server-side in session (existing import preview pattern)
**Warning signs:** Users complaining about re-uploading files
```html
<!-- Target specific error area, not whole form -->
<form hx-post="/upload" hx-target="#error-area" hx-swap="innerHTML">
```

### Pitfall 4: Bootstrap Modal + HTMX Lifecycle Issues
**What goes wrong:** Modal doesn't close after HTMX action, or content doesn't load
**Why it happens:** Bootstrap JS lifecycle conflicts with HTMX DOM swapping
**How to avoid:** Use HX-Trigger response header to control modal via events
**Warning signs:** Modals stuck open, stale content in modals
```python
# Server response to close modal
response.headers["HX-Trigger"] = "closeModal"
```
```javascript
// Listener to close modal
document.body.addEventListener('closeModal', () => {
    bootstrap.Modal.getInstance(document.getElementById('myModal')).hide();
});
```

### Pitfall 5: Slow Dashboard from Multiple Serial Requests
**What goes wrong:** Dashboard feels slow loading all category cards sequentially
**Why it happens:** Each card makes separate request, browser blocks after 6 connections
**How to avoid:** Use single endpoint that returns all dashboard data, or use `hx-trigger="load"` for parallel loading
**Warning signs:** Dashboard taking 3+ seconds to fully load

## Code Examples

Verified patterns from official sources:

### Base Admin Template with Auth
```html
<!-- Source: https://fastapi.tiangolo.com/advanced/templates/ -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin{% endblock %} - BrasilIntel</title>

    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>

    <style>
        :root {
            --marsh-blue: #00263e;
            --marsh-light-blue: #0077c8;
        }
        .navbar { background: var(--marsh-blue) !important; }
        .sidebar { min-height: calc(100vh - 56px); }
        .htmx-indicator { display: none; }
        .htmx-request .htmx-indicator { display: inline-block; }
    </style>
    {% block head %}{% endblock %}
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">BrasilIntel Admin</span>
            <span class="navbar-text text-white">{{ username }}</span>
        </div>
    </nav>

    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <nav class="col-md-2 d-md-block bg-light sidebar py-3">
                <ul class="nav flex-column">
                    <li class="nav-item">
                        <a class="nav-link {% if active == 'dashboard' %}active{% endif %}"
                           href="{{ url_for('admin_dashboard') }}">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if active == 'insurers' %}active{% endif %}"
                           href="{{ url_for('admin_insurers') }}">Insurers</a>
                    </li>
                    <!-- ... more nav items -->
                </ul>
            </nav>

            <!-- Main content -->
            <main class="col-md-10 ms-sm-auto px-md-4 py-3">
                {% block content %}{% endblock %}
            </main>
        </div>
    </div>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Admin Router with Auth Dependency
```python
# Source: https://fastapi.tiangolo.com/advanced/security/http-basic-auth/
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from app.config import Settings, get_settings
from app.dependencies import get_db

router = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="app/templates")
security = HTTPBasic()


def verify_admin(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)]
) -> str:
    """Verify admin credentials using constant-time comparison."""
    expected_user = (settings.admin_username or "admin").encode("utf-8")
    expected_pass = (settings.admin_password or "changeme").encode("utf-8")

    user_ok = secrets.compare_digest(credentials.username.encode("utf-8"), expected_user)
    pass_ok = secrets.compare_digest(credentials.password.encode("utf-8"), expected_pass)

    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic realm='BrasilIntel Admin'"},
        )
    return credentials.username


@router.get("", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
):
    """Admin dashboard with summary cards."""
    # Gather dashboard data from existing APIs
    insurer_stats = get_insurer_stats(db)
    schedule_info = get_schedule_summary()
    recent_reports = get_recent_reports(limit=5)
    health_status = get_system_health()

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "username": username,
            "active": "dashboard",
            "stats": insurer_stats,
            "schedules": schedule_info,
            "reports": recent_reports,
            "health": health_status,
        }
    )
```

### HTMX-Enhanced Insurer Table with Filters
```html
<!-- Source: https://htmx.org/docs/ -->
{% extends "admin/base.html" %}
{% block content %}
<h2>Insurers</h2>

<!-- Filter tabs -->
<ul class="nav nav-tabs mb-3" id="category-tabs">
    <li class="nav-item">
        <a class="nav-link {% if not category %}active{% endif %}"
           hx-get="{{ url_for('admin_insurers') }}"
           hx-target="#insurer-list"
           hx-push-url="true">All</a>
    </li>
    {% for cat in ['Health', 'Dental', 'Group Life'] %}
    <li class="nav-item">
        <a class="nav-link {% if category == cat %}active{% endif %}"
           hx-get="{{ url_for('admin_insurers') }}?category={{ cat }}"
           hx-target="#insurer-list"
           hx-push-url="true">{{ cat }}</a>
    </li>
    {% endfor %}
</ul>

<!-- Search and actions -->
<div class="row mb-3">
    <div class="col-md-4">
        <input type="search"
               class="form-control"
               placeholder="Search by name or ANS code..."
               name="search"
               hx-get="{{ url_for('admin_insurers') }}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#insurer-list"
               hx-include="[name='category']">
    </div>
    <div class="col-md-4">
        <select class="form-select" name="enabled"
                hx-get="{{ url_for('admin_insurers') }}"
                hx-trigger="change"
                hx-target="#insurer-list"
                hx-include="[name='search'],[name='category']">
            <option value="">All Status</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
        </select>
    </div>
    <div class="col-md-4 text-end">
        <button class="btn btn-outline-secondary"
                id="bulk-enable"
                disabled
                hx-post="{{ url_for('admin_bulk_enable') }}"
                hx-include="[name='selected']">
            Enable Selected
        </button>
        <button class="btn btn-outline-secondary"
                id="bulk-disable"
                disabled
                hx-post="{{ url_for('admin_bulk_disable') }}"
                hx-include="[name='selected']">
            Disable Selected
        </button>
    </div>
</div>

<!-- Insurer table (HTMX target) -->
<div id="insurer-list">
    {% include "admin/partials/insurer_table.html" %}
</div>
{% endblock %}
```

### Import Page with Drag-Drop
```html
<!-- Source: https://htmx.org/examples/file-upload/ -->
{% extends "admin/base.html" %}
{% block content %}
<h2>Import Insurers</h2>

<form id="import-form"
      hx-post="{{ url_for('admin_import_preview') }}"
      hx-encoding="multipart/form-data"
      hx-target="#preview-section"
      hx-indicator="#upload-indicator">

    <div id="drop-zone" class="border border-2 border-dashed rounded p-5 text-center mb-3"
         ondrop="handleDrop(event)"
         ondragover="handleDragOver(event)"
         ondragleave="handleDragLeave(event)">
        <input type="file" name="file" id="file-input" accept=".xlsx,.xls"
               required class="d-none" onchange="fileSelected(this)">
        <label for="file-input" class="btn btn-outline-primary btn-lg mb-2">
            Choose Excel File
        </label>
        <p class="text-muted mb-0" id="file-name">Or drag and drop .xlsx file here</p>
    </div>

    <button type="submit" class="btn btn-primary" id="preview-btn" disabled>
        <span id="upload-indicator" class="htmx-indicator spinner-border spinner-border-sm me-1"></span>
        Preview Import
    </button>
</form>

<div id="preview-section" class="mt-4">
    <!-- HTMX swaps preview content here -->
</div>

{% endblock %}

{% block scripts %}
<script>
function handleDrop(e) {
    e.preventDefault();
    document.getElementById('drop-zone').classList.remove('border-primary');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        document.getElementById('file-input').files = files;
        fileSelected(document.getElementById('file-input'));
    }
}

function handleDragOver(e) {
    e.preventDefault();
    document.getElementById('drop-zone').classList.add('border-primary');
}

function handleDragLeave(e) {
    document.getElementById('drop-zone').classList.remove('border-primary');
}

function fileSelected(input) {
    const fileName = input.files[0]?.name || 'No file selected';
    document.getElementById('file-name').textContent = fileName;
    document.getElementById('preview-btn').disabled = !input.files.length;
}
</script>
{% endblock %}
```

### Schedule Page with Toggle and Trigger
```html
<!-- Source: https://htmx.org/docs/ -->
{% extends "admin/base.html" %}
{% block content %}
<h2>Schedules</h2>

<div class="row" id="schedule-cards">
    {% for schedule in schedules %}
    <div class="col-md-4 mb-3">
        <div class="card" id="schedule-{{ schedule.category|replace(' ', '-')|lower }}">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">{{ schedule.category }}</h5>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch"
                           {% if schedule.enabled %}checked{% endif %}
                           hx-put="{{ url_for('admin_toggle_schedule', category=schedule.category) }}"
                           hx-vals='{"enabled": {% if schedule.enabled %}false{% else %}true{% endif %}}'
                           hx-target="#schedule-{{ schedule.category|replace(' ', '-')|lower }}"
                           hx-swap="outerHTML">
                </div>
            </div>
            <div class="card-body">
                <dl class="row mb-0">
                    <dt class="col-5">Cron:</dt>
                    <dd class="col-7"><code>{{ schedule.cron_expression }}</code></dd>

                    <dt class="col-5">Next Run:</dt>
                    <dd class="col-7">{{ schedule.next_run_time|format_datetime }}</dd>

                    <dt class="col-5">Last Run:</dt>
                    <dd class="col-7">
                        {% if schedule.last_run_time %}
                        {{ schedule.last_run_time|format_datetime }}
                        <span class="badge bg-{{ schedule.last_run_status|status_color }}">
                            {{ schedule.last_run_status }}
                        </span>
                        {% else %}
                        <span class="text-muted">Never</span>
                        {% endif %}
                    </dd>
                </dl>
            </div>
            <div class="card-footer">
                <button class="btn btn-sm btn-primary"
                        hx-post="{{ url_for('admin_trigger_run', category=schedule.category) }}"
                        hx-indicator="#trigger-spinner-{{ loop.index }}"
                        hx-target="#trigger-result-{{ loop.index }}"
                        hx-swap="innerHTML">
                    <span id="trigger-spinner-{{ loop.index }}"
                          class="htmx-indicator spinner-border spinner-border-sm"></span>
                    Run Now
                </button>
                <span id="trigger-result-{{ loop.index }}" class="ms-2"></span>
            </div>
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}
```

### Settings Page with Masked API Keys
```html
{% extends "admin/base.html" %}
{% block content %}
<h2>Settings</h2>

<div class="card mb-4">
    <div class="card-header">Company Branding</div>
    <div class="card-body">
        <form hx-put="{{ url_for('admin_update_settings') }}"
              hx-target="#save-result"
              hx-swap="innerHTML">
            <div class="mb-3">
                <label class="form-label">Company Name</label>
                <input type="text" class="form-control" name="company_name"
                       value="{{ settings.company_name }}">
            </div>
            <div class="mb-3">
                <label class="form-label">Classification Level</label>
                <select class="form-select" name="classification_level">
                    <option {% if settings.classification_level == 'CONFIDENTIAL' %}selected{% endif %}>CONFIDENTIAL</option>
                    <option {% if settings.classification_level == 'INTERNAL' %}selected{% endif %}>INTERNAL</option>
                    <option {% if settings.classification_level == 'PUBLIC' %}selected{% endif %}>PUBLIC</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary">Save</button>
            <span id="save-result" class="ms-2"></span>
        </form>
    </div>
</div>

<div class="card mb-4">
    <div class="card-header">API Keys (Read-Only)</div>
    <div class="card-body">
        {% for key_name, key_value in api_keys.items() %}
        <div class="mb-3">
            <label class="form-label">{{ key_name }}</label>
            <div class="input-group">
                <input type="password" class="form-control"
                       id="key-{{ loop.index }}"
                       value="{{ key_value }}"
                       readonly>
                <button class="btn btn-outline-secondary" type="button"
                        onclick="toggleKeyVisibility(this, 'key-{{ loop.index }}')">
                    <i class="bi bi-eye"></i> Show
                </button>
            </div>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function toggleKeyVisibility(btn, inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<i class="bi bi-eye-slash"></i> Hide';
    } else {
        input.type = 'password';
        btn.innerHTML = '<i class="bi bi-eye"></i> Show';
    }
}
</script>
{% endblock %}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SPA for everything | Hypermedia (HTMX) for admin tools | 2023-2025 | Simpler, less JS, better with Python backends |
| React Admin | Server-rendered + HTMX | 2024+ | No build step, faster development |
| Custom auth systems | Built-in HTTPBasic | Always | Secure, browser-native login prompt |
| Full page reloads | HTMX partial updates | 2020+ | Better UX, less server load |

**Deprecated/outdated:**
- jQuery for AJAX: Use HTMX attributes instead
- Bootstrap 4: Use Bootstrap 5 (no jQuery dependency)
- Custom loading spinners: Use `hx-indicator` attribute

## Open Questions

Things that couldn't be fully resolved:

1. **Static file authentication**
   - What we know: StaticFiles mount doesn't support dependencies
   - What's unclear: Whether exposing admin CSS/JS URLs is a security concern
   - Recommendation: Embed critical styles in templates, accept that asset URLs alone aren't sensitive

2. **Recipients page data model**
   - What we know: Recipients currently stored in environment variables
   - What's unclear: Whether ADMN-10/11 expects database-backed recipients
   - Recommendation: Start with read-only display of env vars; database-backed recipients is a larger change

3. **Settings persistence**
   - What we know: Settings loaded from environment variables via pydantic-settings
   - What's unclear: Whether settings page should write to .env file or database
   - Recommendation: Display current settings read-only, or store overrides in database settings table

## Sources

### Primary (HIGH confidence)
- [FastAPI Templates Documentation](https://fastapi.tiangolo.com/advanced/templates/) - Jinja2Templates setup and usage
- [FastAPI HTTP Basic Auth](https://fastapi.tiangolo.com/advanced/security/http-basic-auth/) - Authentication implementation
- [HTMX Documentation](https://htmx.org/docs/) - Core HTMX patterns
- [HTMX File Upload Example](https://htmx.org/examples/file-upload/) - File upload with progress
- [HTMX Inline Validation](https://htmx.org/examples/inline-validation/) - Form validation patterns

### Secondary (MEDIUM confidence)
- [TestDriven.io FastAPI + HTMX](https://testdriven.io/blog/fastapi-htmx/) - Integration patterns
- [Bootstrap 5 Admin Templates](https://colorlib.com/wp/free-bootstrap-admin-dashboard-templates/) - UI component patterns
- [FastAPI File Uploads Guide](https://oneuptime.com/blog/post/2026-01-26-fastapi-file-uploads/view) - File handling best practices

### Tertiary (LOW confidence)
- Various Medium articles on Django + HTMX patterns (applicable to FastAPI with adaptation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using existing project technologies (Jinja2, Bootstrap) plus well-documented HTMX
- Architecture: HIGH - Patterns verified from official FastAPI and HTMX documentation
- Pitfalls: MEDIUM - Based on community patterns and general HTMX experience

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - stable technologies)
