"""
Critical alert service for immediate notification of Critical status insurers.

Detects Critical status insurers from a run and sends focused alert emails
with [CRITICAL ALERT] subject prefix. Separate from daily digest workflow.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.insurer import Insurer
from app.models.news_item import NewsItem
from app.models.run import Run
from app.services.emailer import GraphEmailService
from app.services.reporter import ReportService

logger = logging.getLogger(__name__)


class CriticalAlertService:
    """
    Service for detecting and sending critical alerts.

    Monitors for Critical status insurers and sends immediate
    alert emails separate from the daily digest workflow.

    Features:
    - Queries for Critical status insurers from a run
    - Sends alert with [CRITICAL ALERT] subject prefix
    - Tracks alert status in Run model
    - Uses dedicated alert template for focused presentation
    """

    def __init__(self):
        """Initialize services and template environment."""
        self.settings = get_settings()
        self.email_service = GraphEmailService()

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Register indicator label filter from ReportService
        self.env.filters['indicator_label'] = ReportService.get_indicator_label

    def find_critical_insurers(
        self,
        run_id: int,
        db_session: Session
    ) -> list[Insurer]:
        """
        Find insurers with Critical status news items from a run.

        Queries the database for insurers that have at least one
        news item with Critical status in the specified run.

        Args:
            run_id: Run ID to search
            db_session: Database session

        Returns:
            List of Insurer objects with Critical status news items loaded
        """
        # Find insurers with Critical news items in this run
        critical_insurers = (
            db_session.query(Insurer)
            .join(NewsItem, NewsItem.insurer_id == Insurer.id)
            .filter(
                NewsItem.run_id == run_id,
                NewsItem.status == "Critical"
            )
            .distinct()
            .all()
        )

        # Load the Critical news items for each insurer
        # Expunge insurers first to avoid ORM relationship side effects
        for insurer in critical_insurers:
            db_session.expunge(insurer)
            insurer.news_items = (
                db_session.query(NewsItem)
                .filter(
                    NewsItem.insurer_id == insurer.id,
                    NewsItem.run_id == run_id,
                    NewsItem.status == "Critical"
                )
                .all()
            )

        logger.info(f"Found {len(critical_insurers)} critical insurers for run {run_id}")
        return critical_insurers

    def _build_alert_html(
        self,
        category: str,
        critical_insurers: list[Insurer],
        timestamp: Optional[datetime] = None
    ) -> str:
        """
        Render critical alert HTML from template.

        Args:
            category: Insurer category (Health, Dental, Group Life)
            critical_insurers: List of insurers with Critical status
            timestamp: Alert generation timestamp (defaults to now)

        Returns:
            Rendered HTML alert content
        """
        if timestamp is None:
            timestamp = datetime.now()

        template = self.env.get_template("alert_critical.html")

        return template.render(
            company_name=self.settings.company_name,
            category=category,
            critical_count=len(critical_insurers),
            critical_insurers=critical_insurers,
            timestamp=timestamp.strftime("%d/%m/%Y as %H:%M")
        )

    async def check_and_send_alert(
        self,
        run_id: int,
        category: str,
        db_session: Session,
        send_email: bool = True
    ) -> dict:
        """
        Check for Critical insurers and send alert if found.

        Main entry point for critical alert workflow. Checks if there
        are Critical status insurers, and if so, sends an immediate
        alert email with [CRITICAL ALERT] prefix.

        Args:
            run_id: Run ID to check
            category: Category for recipient lookup
            db_session: Database session
            send_email: Whether to actually send email (for testing)

        Returns:
            dict with status, critical_count, and any error message
        """
        # Get the run
        run = db_session.query(Run).filter(Run.id == run_id).first()
        if not run:
            return {"status": "error", "message": f"Run {run_id} not found"}

        # Check if alert already sent
        if run.critical_alert_sent:
            logger.info(f"Critical alert already sent for run {run_id}")
            return {
                "status": "skipped",
                "message": "Alert already sent",
                "critical_count": run.critical_insurers_count
            }

        # Find critical insurers
        critical_insurers = self.find_critical_insurers(run_id, db_session)

        # Update run with critical count
        run.critical_insurers_count = len(critical_insurers)

        if not critical_insurers:
            logger.info(f"No critical insurers found for run {run_id}")
            db_session.commit()
            return {
                "status": "ok",
                "message": "No critical insurers found",
                "critical_count": 0
            }

        # Build alert HTML
        alert_html = self._build_alert_html(
            category=category,
            critical_insurers=critical_insurers,
            timestamp=run.started_at
        )

        if not send_email:
            logger.info(f"Email sending disabled - would send alert for {len(critical_insurers)} critical insurers")
            return {
                "status": "ok",
                "message": "Alert generated (email disabled)",
                "critical_count": len(critical_insurers),
                "html_length": len(alert_html)
            }

        # Get recipients for category
        recipients = self.settings.get_email_recipients(category)

        if not recipients.has_recipients:
            logger.warning(f"No recipients configured for {category} alerts")
            return {
                "status": "skipped",
                "message": f"No recipients configured for {category}",
                "critical_count": len(critical_insurers)
            }

        # Build subject with [CRITICAL ALERT] prefix
        alert_date = run.started_at.strftime("%d/%m/%Y")
        subject = f"[CRITICAL ALERT] {category} - {len(critical_insurers)} Seguradora(s) em Status Critico - {alert_date}"

        # Send the alert email
        try:
            result = await self.email_service.send_email(
                to_addresses=recipients.to,
                cc_addresses=recipients.cc if recipients.cc else None,
                bcc_addresses=recipients.bcc if recipients.bcc else None,
                subject=subject,
                html_body=alert_html
            )

            if result.get("status") == "ok":
                # Update run tracking
                run.critical_alert_sent = True
                run.critical_alert_sent_at = datetime.utcnow()
                db_session.commit()

                logger.info(f"Critical alert sent for run {run_id} with {len(critical_insurers)} critical insurers")
                return {
                    "status": "ok",
                    "message": "Critical alert sent",
                    "critical_count": len(critical_insurers),
                    "recipients": result.get("recipients", 0)
                }
            else:
                logger.error(f"Failed to send critical alert: {result.get('message')}")
                return {
                    "status": "error",
                    "message": result.get("message", "Unknown error"),
                    "critical_count": len(critical_insurers)
                }

        except Exception as e:
            logger.error(f"Exception sending critical alert: {e}")
            return {
                "status": "error",
                "message": str(e),
                "critical_count": len(critical_insurers)
            }

    def preview_alert(self, category: str = "Health") -> str:
        """
        Generate a preview alert with mock data.

        Creates sample critical insurers to demonstrate
        the alert template layout and styling.

        Args:
            category: Category for preview

        Returns:
            Rendered HTML alert with mock data
        """
        # Create mock critical insurers
        mock_insurer1 = Insurer(
            id=1,
            ans_code="123456",
            name="Seguradora XYZ",
            cnpj="12.345.678/0001-90",
            category=category,
            status="Critical"
        )
        mock_insurer1.news_items = [
            NewsItem(
                id=1,
                title="Seguradora enfrenta problemas financeiros graves",
                source_name="Valor Economico",
                source_url="https://example.com/news1",
                published_at=datetime(2024, 1, 15),
                status="Critical",
                sentiment="negative",
                summary="Prejuizo de R$ 50 milhoes no ultimo trimestre\nInadimplencia cresceu 15%\nANS abriu processo de fiscalizacao",
                category_indicators="financial_health,regulatory_compliance"
            )
        ]

        mock_insurer2 = Insurer(
            id=2,
            ans_code="234567",
            name="Plano Saude ABC",
            cnpj="23.456.789/0001-01",
            category=category,
            status="Critical"
        )
        mock_insurer2.news_items = [
            NewsItem(
                id=2,
                title="ANS determina intervencao em operadora",
                source_name="CQCS",
                source_url="https://example.com/news2",
                published_at=datetime(2024, 1, 14),
                status="Critical",
                sentiment="negative",
                summary="ANS determinou regime de direcao fiscal\nOperadora tem 30 dias para regularizar situacao\nClientes podem ser transferidos",
                category_indicators="regulatory_compliance,legal_issues"
            )
        ]

        mock_insurers = [mock_insurer1, mock_insurer2]

        return self._build_alert_html(
            category=category,
            critical_insurers=mock_insurers,
            timestamp=datetime.now()
        )
