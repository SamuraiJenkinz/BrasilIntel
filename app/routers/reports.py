"""
Report archive browsing API endpoints.

Provides REST API for browsing and retrieving archived HTML reports.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.report_archiver import ReportArchiver

router = APIRouter(prefix="/reports", tags=["Reports"])


class ArchivedReport(BaseModel):
    """Schema for archived report metadata."""
    date: str
    category: str
    filename: str
    timestamp: str
    path: str
    size_kb: int


class ArchiveBrowseResponse(BaseModel):
    """Response schema for archive browsing."""
    total: int
    reports: list[ArchivedReport]


class AvailableDatesResponse(BaseModel):
    """Response schema for available dates."""
    dates: list[str]


@router.get("/archive", response_model=ArchiveBrowseResponse)
async def browse_archived_reports(
    start_date: Optional[str] = Query(
        None,
        description="Filter from date (YYYY-MM-DD)",
        example="2026-02-01"
    ),
    end_date: Optional[str] = Query(
        None,
        description="Filter until date (YYYY-MM-DD)",
        example="2026-02-28"
    ),
    category: Optional[str] = Query(
        None,
        description="Filter by category",
        example="Health"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum reports to return"
    )
) -> ArchiveBrowseResponse:
    """
    Browse archived reports with optional filtering.

    Returns list of reports sorted by date descending (newest first).

    - **start_date**: Filter reports from this date (inclusive)
    - **end_date**: Filter reports until this date (inclusive)
    - **category**: Filter by category (Health, Dental, Group Life)
    - **limit**: Maximum number of reports to return (1-200)
    """
    archiver = ReportArchiver()

    # Parse date strings
    start = None
    end = None

    if start_date:
        try:
            start = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid start_date format: {start_date}. Use YYYY-MM-DD."
            )

    if end_date:
        try:
            end = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid end_date format: {end_date}. Use YYYY-MM-DD."
            )

    reports = archiver.browse_reports(
        start_date=start,
        end_date=end,
        category=category,
        limit=limit
    )

    return ArchiveBrowseResponse(
        total=len(reports),
        reports=[ArchivedReport(**r) for r in reports]
    )


@router.get("/archive/dates", response_model=AvailableDatesResponse)
async def get_available_dates(
    category: Optional[str] = Query(
        None,
        description="Filter by category",
        example="Health"
    ),
    limit: int = Query(
        30,
        ge=1,
        le=90,
        description="Maximum dates to return"
    )
) -> AvailableDatesResponse:
    """
    Get list of dates that have archived reports.

    Useful for calendar-based browsing UI.

    - **category**: Filter by category (optional)
    - **limit**: Maximum dates to return (1-90)
    """
    archiver = ReportArchiver()

    dates = archiver.get_dates_with_reports(
        category=category,
        limit=limit
    )

    return AvailableDatesResponse(dates=dates)


@router.get(
    "/archive/{date}/{filename}",
    response_class=HTMLResponse,
    responses={
        200: {
            "content": {"text/html": {}},
            "description": "HTML report content"
        },
        404: {
            "description": "Report not found"
        }
    }
)
async def get_archived_report(
    date: str,
    filename: str
) -> HTMLResponse:
    """
    Retrieve a specific archived report.

    - **date**: Report date in YYYY-MM-DD format
    - **filename**: Report filename (e.g., health_14-30-00.html)

    Returns the raw HTML content of the report.
    """
    # Validate date format
    try:
        datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: {date}. Use YYYY-MM-DD."
        )

    archiver = ReportArchiver()

    html = archiver.get_report(date=date, filename=filename)

    if html is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report not found: {date}/{filename}"
        )

    return HTMLResponse(content=html)


@router.get("/preview", response_class=HTMLResponse)
async def preview_professional_report() -> HTMLResponse:
    """
    Generate a preview of the professional report template with sample data.

    Useful for testing template rendering without database data.
    """
    from app.services.reporter import ReportService
    from app.models.insurer import Insurer
    from app.models.news_item import NewsItem

    service = ReportService()

    # Create mock insurers with news for preview
    critical_insurer = Insurer(
        id=1,
        ans_code="123456",
        name="Seguradora Exemplo Critica",
        cnpj="12.345.678/0001-90",
        category="Health",
        status="Critical"
    )
    critical_insurer.news_items = [
        NewsItem(
            id=1,
            title="Seguradora enfrenta problemas financeiros graves",
            source_name="Valor Economico",
            source_url="https://example.com/news1",
            published_at=datetime.now(),
            status="Critical",
            sentiment="negative",
            summary="Prejuizo significativo no ultimo trimestre. ANS abriu processo de fiscalizacao.",
            category_indicators="financial_health,regulatory_compliance"
        )
    ]

    watch_insurer = Insurer(
        id=2,
        ans_code="234567",
        name="Plano Saude Monitor",
        cnpj="23.456.789/0001-01",
        category="Health",
        status="Watch"
    )
    watch_insurer.news_items = [
        NewsItem(
            id=2,
            title="Reclamacoes aumentam no periodo",
            source_name="CQCS",
            source_url="https://example.com/news2",
            published_at=datetime.now(),
            status="Watch",
            sentiment="neutral",
            summary="Aumento de reclamacoes de clientes sobre autorizacoes.",
            category_indicators="customer_satisfaction"
        )
    ]

    stable_insurer = Insurer(
        id=3,
        ans_code="345678",
        name="Seguradora Estavel SA",
        cnpj="34.567.890/0001-12",
        category="Health",
        status="Stable"
    )
    stable_insurer.news_items = [
        NewsItem(
            id=3,
            title="Empresa anuncia expansao de rede",
            source_name="InfoMoney",
            source_url="https://example.com/news3",
            published_at=datetime.now(),
            status="Stable",
            sentiment="positive",
            summary="Nova parceria amplia rede credenciada em SP e RJ.",
            category_indicators="market_share_change,partnership"
        )
    ]

    mock_insurers = [critical_insurer, watch_insurer, stable_insurer]

    # Generate professional report without archiving
    html, _ = service.generate_professional_report(
        category="Health",
        insurers=mock_insurers,
        archive_report=False,
        use_ai_summary=False  # Use basic summary for preview
    )

    return HTMLResponse(content=html)
