"""
Admin interface router for BrasilIntel.

Provides web-based administration with HTTP Basic authentication.
Serves HTML pages using Jinja2 templates.
"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies import get_db, verify_admin
from app.models.insurer import Insurer
from app.services.excel_service import parse_excel_insurers

router = APIRouter(prefix="/admin", tags=["Admin"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# In-memory storage for import previews
# Key: session_id, Value: {"data": [...], "errors": [...], "expires": datetime}
import_sessions: dict[str, dict] = {}


def cleanup_expired_sessions() -> None:
    """Remove expired preview sessions."""
    now = datetime.now()
    expired = [k for k, v in import_sessions.items() if v["expires"] < now]
    for k in expired:
        del import_sessions[k]


@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Admin dashboard page.

    Shows system overview with run statistics, recent activity,
    and quick actions. Content detailed in Plan 08-02.

    Args:
        request: FastAPI request object
        username: Authenticated admin username

    Returns:
        Rendered dashboard HTML page
    """
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "username": username,
            "active": "dashboard"
        }
    )


@router.get("/insurers", response_class=HTMLResponse, name="admin_insurers")
async def insurers(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Insurers management page.

    Lists all insurers with filtering and management capabilities.
    Content detailed in Plan 08-03.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "insurers",
            "page_title": "Insurers",
            "page_icon": "bi-building",
            "plan_number": "08-03"
        }
    )


@router.get("/import", response_class=HTMLResponse, name="admin_import")
async def import_page(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Import management page.

    Provides drag-and-drop file upload for Excel insurer data.
    Supports ADMN-08 (drag-drop upload) and ADMN-09 (preview with validation).
    """
    return templates.TemplateResponse(
        "admin/import.html",
        {
            "request": request,
            "username": username,
            "active": "import"
        }
    )


@router.post("/import/preview", response_class=HTMLResponse, name="admin_import_preview")
async def admin_import_preview(
    request: Request,
    file: UploadFile = File(...),
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Parse uploaded Excel file and return preview partial.

    Validates file type, parses contents, stores in session for later commit.
    Returns preview table with validation errors inline.

    Args:
        request: FastAPI request object
        file: Uploaded Excel file
        username: Authenticated admin username

    Returns:
        Rendered preview partial HTML
    """
    cleanup_expired_sessions()

    # Validate file type
    if not file.filename or not file.filename.endswith(('.xlsx', '.xls')):
        return templates.TemplateResponse(
            "admin/partials/import_preview.html",
            {"request": request, "error": "Please upload an Excel file (.xlsx or .xls)"}
        )

    # Parse Excel file
    try:
        content = await file.read()
        from io import BytesIO
        insurers, errors = parse_excel_insurers(BytesIO(content))
    except Exception as e:
        return templates.TemplateResponse(
            "admin/partials/import_preview.html",
            {"request": request, "error": f"Failed to parse file: {str(e)}"}
        )

    # Store in session for commit
    session_id = str(uuid.uuid4())
    import_sessions[session_id] = {
        "data": insurers,
        "errors": errors,
        "expires": datetime.now() + timedelta(minutes=30)
    }

    return templates.TemplateResponse(
        "admin/partials/import_preview.html",
        {
            "request": request,
            "session_id": session_id,
            "insurers": insurers[:100],  # Preview first 100
            "total": len(insurers),
            "errors": errors,
            "has_errors": len(errors) > 0,
        }
    )


@router.post("/import/commit", response_class=HTMLResponse, name="admin_import_commit")
async def admin_import_commit(
    request: Request,
    session_id: str = Form(...),
    mode: str = Form("merge"),
    username: str = Depends(verify_admin),
    db: Session = Depends(get_db)
) -> HTMLResponse:
    """
    Commit previewed import data to database.

    Takes session_id from preview, imports data with merge or skip mode.
    Merge mode updates existing records, skip mode ignores them.

    Args:
        request: FastAPI request object
        session_id: Session ID from preview
        mode: Import mode - "merge" updates existing, "skip" ignores existing
        username: Authenticated admin username
        db: Database session

    Returns:
        Success or error message HTML
    """
    # Get session data
    session = import_sessions.get(session_id)
    if not session:
        return HTMLResponse(
            '<div class="alert alert-danger">Session expired. Please upload again.</div>'
        )

    insurers = session["data"]
    created, updated, skipped = 0, 0, 0

    try:
        for data in insurers:
            existing = db.query(Insurer).filter(Insurer.ans_code == data["ans_code"]).first()
            if existing:
                if mode == "merge":
                    for key, value in data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    skipped += 1
            else:
                db.add(Insurer(**data))
                created += 1

        db.commit()

        # Clear session
        del import_sessions[session_id]

        return HTMLResponse(f'''
        <div class="alert alert-success">
            <strong>Import complete!</strong><br>
            Created: {created}, Updated: {updated}, Skipped: {skipped}
        </div>
        ''')
    except Exception as e:
        db.rollback()
        return HTMLResponse(f'''
        <div class="alert alert-danger">
            <strong>Import failed:</strong> {str(e)}
        </div>
        ''')


@router.get("/recipients", response_class=HTMLResponse, name="admin_recipients")
async def recipients(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Email recipients management page.

    Configure report recipients per category.
    Content detailed in Plan 08-04.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "recipients",
            "page_title": "Recipients",
            "page_icon": "bi-people",
            "plan_number": "08-04"
        }
    )


@router.get("/schedules", response_class=HTMLResponse, name="admin_schedules")
async def schedules(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Schedule management page.

    View and modify category run schedules.
    Content detailed in Plan 08-05.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "schedules",
            "page_title": "Schedules",
            "page_icon": "bi-calendar-check",
            "plan_number": "08-05"
        }
    )


@router.get("/settings", response_class=HTMLResponse, name="admin_settings")
async def settings(
    request: Request,
    username: str = Depends(verify_admin)
) -> HTMLResponse:
    """
    Settings page.

    System configuration and status.
    Content detailed in Plan 08-06.
    """
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "username": username,
            "active": "settings",
            "page_title": "Settings",
            "page_icon": "bi-gear",
            "plan_number": "08-06"
        }
    )
