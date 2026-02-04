"""
Import/Export router for BrasilIntel API.

Provides endpoints for bulk data import from Excel with preview-before-commit workflow:
- POST /api/import/preview - Parse Excel and return preview with validation
- POST /api/import/commit/{session_id} - Commit previewed data to database

Supports:
- DATA-04: Upload Excel file
- DATA-05: Preview before commit
- DATA-07: Validate required fields
- DATA-08: Reject/handle duplicates
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.insurer import Insurer
from app.services.excel_service import parse_excel_insurers, generate_excel_export

router = APIRouter(prefix="/api/import", tags=["import"])

# In-memory session storage for preview data
# For MVP - production would use Redis or database-backed sessions
preview_sessions: Dict[str, dict] = {}
SESSION_TTL_MINUTES = 30


def cleanup_expired_sessions() -> int:
    """Remove expired preview sessions. Returns count of removed sessions."""
    now = datetime.utcnow()
    expired = [
        sid for sid, session in preview_sessions.items()
        if now - session['created_at'] > timedelta(minutes=SESSION_TTL_MINUTES)
    ]
    for sid in expired:
        del preview_sessions[sid]
    return len(expired)


@router.post("/preview")
async def preview_import(
    file: UploadFile,
    db: Session = Depends(get_db)
) -> dict:
    """
    Preview Excel import before committing to database (DATA-04, DATA-05).

    Parses the uploaded Excel file, validates all rows, and returns:
    - Validated data ready for import
    - Validation errors for invalid rows
    - Duplicate detection (within file and against database)

    The preview is stored in a session and can be committed within 30 minutes.

    Args:
        file: Excel file (.xlsx or .xls)

    Returns:
        Preview response with session_id for commit, validation results,
        and first 20 rows for display

    Raises:
        HTTPException 400: If file is not Excel format
    """
    # Cleanup old sessions periodically
    cleanup_expired_sessions()

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be Excel format (.xlsx or .xls)"
        )

    # Parse Excel file
    try:
        validated, errors = parse_excel_insurers(file.file)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse Excel file: {str(e)}"
        )

    # Check for duplicates within uploaded data
    seen_codes: Dict[str, int] = {}
    internal_duplicates = []

    for idx, item in enumerate(validated):
        code = item['ans_code']
        row_num = idx + 2  # Excel row (1-indexed + header)

        if code in seen_codes:
            internal_duplicates.append({
                'ans_code': code,
                'first_row': seen_codes[code],
                'duplicate_row': row_num
            })
        else:
            seen_codes[code] = row_num

    # Check for existing ANS codes in database (DATA-08)
    existing_codes = {r[0] for r in db.query(Insurer.ans_code).all()}
    db_duplicates = [
        {'ans_code': v['ans_code'], 'action': 'will_update'}
        for v in validated if v['ans_code'] in existing_codes
    ]
    new_records = [
        v for v in validated if v['ans_code'] not in existing_codes
    ]

    # Store session for commit
    session_id = str(uuid.uuid4())
    preview_sessions[session_id] = {
        'data': validated,
        'created_at': datetime.utcnow(),
        'existing_codes': list(existing_codes),
        'filename': file.filename
    }

    # Calculate counts
    total_rows = len(validated) + len(errors)
    valid_rows = len(validated)
    duplicate_in_file = len(internal_duplicates)
    will_update = len(db_duplicates)
    will_create = len(new_records)

    return {
        'session_id': session_id,
        'filename': file.filename,
        'summary': {
            'total_rows': total_rows,
            'valid_rows': valid_rows,
            'error_rows': len(errors),
            'duplicates_in_file': duplicate_in_file,
            'will_create': will_create,
            'will_update': will_update
        },
        'errors': errors,
        'internal_duplicates': internal_duplicates,
        'existing_in_db': db_duplicates,
        'preview': validated[:20],  # First 20 rows for display
        'expires_in_minutes': SESSION_TTL_MINUTES
    }


@router.post("/commit/{session_id}")
async def commit_import(
    session_id: str,
    mode: str = "merge",
    db: Session = Depends(get_db)
) -> dict:
    """
    Commit previewed import data to database.

    Takes a session_id from a previous preview call and imports the data.
    Existing records (by ANS code) are updated, new records are created.

    Args:
        session_id: Session ID from preview response
        mode: Import mode - "merge" updates existing (default), "skip" ignores existing

    Returns:
        Import result with created/updated counts

    Raises:
        HTTPException 404: If session not found
        HTTPException 410: If session expired
        HTTPException 500: On database error
    """
    # Validate session exists
    if session_id not in preview_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preview session not found or expired. Please upload the file again."
        )

    session = preview_sessions[session_id]

    # Check session age
    if datetime.utcnow() - session['created_at'] > timedelta(minutes=SESSION_TTL_MINUTES):
        del preview_sessions[session_id]
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Preview session expired. Please upload the file again."
        )

    validated_data = session['data']
    existing_codes = set(session['existing_codes'])

    try:
        created = 0
        updated = 0
        skipped = 0

        for item in validated_data:
            if item['ans_code'] in existing_codes:
                if mode == "merge":
                    # Update existing record
                    db.query(Insurer).filter(
                        Insurer.ans_code == item['ans_code']
                    ).update({
                        'name': item['name'],
                        'cnpj': item.get('cnpj'),
                        'category': item['category'],
                        'market_master': item.get('market_master'),
                        'status': item.get('status'),
                    })
                    updated += 1
                else:
                    # Skip existing
                    skipped += 1
            else:
                # Create new record
                insurer = Insurer(
                    ans_code=item['ans_code'],
                    name=item['name'],
                    cnpj=item.get('cnpj'),
                    category=item['category'],
                    market_master=item.get('market_master'),
                    status=item.get('status'),
                    enabled=True
                )
                db.add(insurer)
                created += 1

        db.commit()

        # Clean up session after successful import
        del preview_sessions[session_id]

        return {
            'status': 'success',
            'mode': mode,
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'total': created + updated
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/sessions")
async def list_sessions() -> dict:
    """
    List active preview sessions (admin/debug endpoint).

    Returns:
        List of active sessions with basic info
    """
    cleanup_expired_sessions()

    sessions = []
    for sid, session in preview_sessions.items():
        age_minutes = (datetime.utcnow() - session['created_at']).seconds // 60
        sessions.append({
            'session_id': sid,
            'filename': session.get('filename', 'unknown'),
            'row_count': len(session['data']),
            'age_minutes': age_minutes,
            'expires_in_minutes': SESSION_TTL_MINUTES - age_minutes
        })

    return {
        'active_sessions': len(sessions),
        'sessions': sessions
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    """
    Delete a preview session (cancel import).

    Args:
        session_id: Session ID to delete

    Returns:
        Confirmation message
    """
    if session_id not in preview_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    del preview_sessions[session_id]
    return {'status': 'deleted', 'session_id': session_id}


@router.get("/export")
def export_insurers(
    category: str | None = None,
    enabled: bool | None = None,
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Export insurers to Excel file (DATA-06).

    Downloads an Excel file containing insurer data matching the original
    import format for round-trip compatibility. Supports optional filtering.

    Args:
        category: Filter by category (Health, Dental, Group Life)
        enabled: Filter by enabled status (true/false)

    Returns:
        StreamingResponse with Excel file download

    Raises:
        HTTPException 404: If no insurers found matching criteria
    """
    # Build query with optional filters
    query = db.query(Insurer)

    if category:
        query = query.filter(Insurer.category == category)
    if enabled is not None:
        query = query.filter(Insurer.enabled == enabled)

    insurers = query.order_by(Insurer.category, Insurer.name).all()

    if not insurers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No insurers found matching criteria"
        )

    # Generate Excel
    output = generate_excel_export(insurers)

    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"insurers_export_{timestamp}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/stats")
def get_import_stats(db: Session = Depends(get_db)) -> dict:
    """
    Get summary statistics about insurers.

    Provides quick overview of total insurer counts by category
    and enabled status for dashboard display.

    Returns:
        Dictionary with total, enabled/disabled counts, and category breakdown
    """
    total = db.query(Insurer).count()
    enabled_count = db.query(Insurer).filter(Insurer.enabled == True).count()

    # Count by category
    by_category = {}
    for category_name in ['Health', 'Dental', 'Group Life']:
        count = db.query(Insurer).filter(Insurer.category == category_name).count()
        by_category[category_name] = count

    return {
        'total': total,
        'enabled': enabled_count,
        'disabled': total - enabled_count,
        'by_category': by_category
    }
