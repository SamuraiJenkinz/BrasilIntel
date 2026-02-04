"""
HTML report generation service using Jinja2 templates.

Transforms classified insurer news into professional HTML reports suitable
for email delivery. Groups insurers by status priority with executive summary.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.insurer import Insurer
from app.models.news_item import NewsItem
from app.models.run import Run


@dataclass
class ReportData:
    """
    Container for report generation data.

    Organizes insurers and metadata for template rendering.
    """
    category: str
    insurers: list[Insurer]
    report_date: datetime
    company_name: str = "Marsh Brasil"


class ReportService:
    """
    Service for generating HTML reports using Jinja2 templates.

    Generates professional HTML reports with:
    - Executive summary with status counts
    - Insurers grouped by status (Critical first)
    - News items with summaries and sentiment
    """

    def __init__(self):
        """Initialize Jinja2 environment with template loader."""
        self.settings = get_settings()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def get_insurers_by_status(self, insurers: list[Insurer]) -> dict[str, list[Insurer]]:
        """
        Group insurers by status priority.

        Returns dict with keys: Critical, Watch, Monitor, Stable
        Each containing list of insurers with that status.
        Order ensures Critical appears first in reports.
        """
        status_priority = ["Critical", "Watch", "Monitor", "Stable"]
        grouped = {status: [] for status in status_priority}

        for insurer in insurers:
            # Determine insurer status from their news items
            if not insurer.news_items:
                continue

            # Use the most severe status from any news item
            statuses = [news.status for news in insurer.news_items if news.status]
            if not statuses:
                continue

            # Find most critical status
            for status in status_priority:
                if status in statuses:
                    grouped[status].append(insurer)
                    break

        return grouped

    def get_status_counts(self, insurers_by_status: dict[str, list[Insurer]]) -> dict[str, int]:
        """
        Calculate count of insurers in each status.

        Returns dict with status names as keys and counts as values.
        """
        return {
            status: len(insurers)
            for status, insurers in insurers_by_status.items()
        }

    def generate_report(
        self,
        category: str,
        insurers: list[Insurer],
        report_date: Optional[datetime] = None
    ) -> str:
        """
        Generate HTML report for a category of insurers.

        Args:
            category: Insurer category (Health, Dental, Group Life)
            insurers: List of Insurer objects with loaded news_items
            report_date: Date for report (defaults to now)

        Returns:
            Rendered HTML report as string
        """
        if report_date is None:
            report_date = datetime.now()

        # Group insurers by status
        insurers_by_status = self.get_insurers_by_status(insurers)
        status_counts = self.get_status_counts(insurers_by_status)

        # Load and render template
        template = self.env.get_template("report_basic.html")

        return template.render(
            company_name=self.settings.company_name,
            category=category,
            report_date=report_date.strftime("%d/%m/%Y"),
            generation_timestamp=datetime.now().strftime("%d/%m/%Y às %H:%M"),
            total_insurers=len(insurers),
            insurers_by_status=insurers_by_status,
            status_counts=status_counts
        )

    def generate_report_from_db(
        self,
        db: Session,
        run_id: int,
        category: str
    ) -> str:
        """
        Generate report for a specific run from database.

        Loads insurers and their news items for the specified run,
        then generates the HTML report.

        Args:
            db: Database session
            run_id: Run ID to generate report for
            category: Insurer category to filter by

        Returns:
            Rendered HTML report as string

        Raises:
            ValueError: If run not found
        """
        # Verify run exists
        run = db.query(Run).filter(Run.id == run_id).first()
        if not run:
            raise ValueError(f"Run {run_id} not found")

        # Load insurers with their news items for this run
        insurers = (
            db.query(Insurer)
            .filter(
                Insurer.category == category,
                Insurer.enabled == True
            )
            .join(NewsItem, NewsItem.insurer_id == Insurer.id)
            .filter(NewsItem.run_id == run_id)
            .distinct()
            .all()
        )

        # Load news items for each insurer
        for insurer in insurers:
            insurer.news_items = (
                db.query(NewsItem)
                .filter(
                    NewsItem.insurer_id == insurer.id,
                    NewsItem.run_id == run_id
                )
                .all()
            )

        return self.generate_report(
            category=category,
            insurers=insurers,
            report_date=run.started_at
        )

    def preview_template(self) -> str:
        """
        Generate a preview report with sample data for testing.

        Creates mock insurers and news items to demonstrate
        the report template layout and styling.

        Returns:
            Rendered HTML report with sample data
        """
        # Create mock insurers with news
        critical_insurer = Insurer(
            id=1,
            ans_code="123456",
            name="Seguradora XYZ",
            cnpj="12.345.678/0001-90",
            category="Health",
            status="Critical"
        )
        critical_insurer.news_items = [
            NewsItem(
                id=1,
                title="Seguradora enfrenta problemas financeiros graves",
                source_name="Folha de S.Paulo",
                source_url="https://example.com/news1",
                published_at=datetime(2024, 1, 15),
                status="Critical",
                sentiment="negative",
                summary="• Prejuízo de R$ 50 milhões no último trimestre\n• Inadimplência cresceu 15%\n• ANS abriu processo de fiscalização"
            )
        ]

        watch_insurer = Insurer(
            id=2,
            ans_code="234567",
            name="Plano Saúde ABC",
            cnpj="23.456.789/0001-01",
            category="Health",
            status="Watch"
        )
        watch_insurer.news_items = [
            NewsItem(
                id=2,
                title="Reclamações aumentam no Reclame Aqui",
                source_name="Portal da Saúde",
                source_url="https://example.com/news2",
                published_at=datetime(2024, 1, 14),
                status="Watch",
                sentiment="neutral",
                summary="• Aumento de 25% nas reclamações\n• Demora na autorização de procedimentos\n• Empresa divulgou nota oficial"
            )
        ]

        stable_insurer = Insurer(
            id=3,
            ans_code="345678",
            name="Saúde Vida Seguros",
            cnpj="34.567.890/0001-12",
            category="Health",
            status="Stable"
        )
        stable_insurer.news_items = [
            NewsItem(
                id=3,
                title="Empresa lança novo produto para PMEs",
                source_name="Valor Econômico",
                source_url="https://example.com/news3",
                published_at=datetime(2024, 1, 13),
                status="Stable",
                sentiment="positive",
                summary="• Novo plano com cobertura ampliada\n• Foco em pequenas e médias empresas\n• Expectativa de crescer 10% no segmento"
            )
        ]

        mock_insurers = [critical_insurer, watch_insurer, stable_insurer]

        return self.generate_report(
            category="Health",
            insurers=mock_insurers,
            report_date=datetime.now()
        )
