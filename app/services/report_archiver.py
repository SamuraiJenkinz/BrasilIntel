"""
File-based report archival system with date hierarchy.

Stores generated HTML reports in YYYY/MM/DD directory structure with
metadata.json index for efficient browsing and retrieval.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()


class ReportArchiver:
    """
    Service for archiving and retrieving generated reports.

    Organizes reports in date-based hierarchy:
    storage/reports/YYYY/MM/DD/category_HH-MM-SS.html

    Each day directory contains metadata.json for browsing.
    """

    def __init__(self, archive_root: Optional[Path] = None):
        """
        Initialize archiver with archive root directory.

        Args:
            archive_root: Custom archive root (defaults to app/storage/reports/)
        """
        if archive_root:
            self.archive_root = archive_root
        else:
            self.archive_root = Path(__file__).parent.parent / "storage" / "reports"

        # Ensure archive root exists
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def save_report(
        self,
        html: str,
        category: str,
        report_date: Optional[datetime] = None
    ) -> Path:
        """
        Save HTML report to date-based archive.

        Creates directory structure: YYYY/MM/DD/
        Filename format: category_HH-MM-SS.html

        Args:
            html: Rendered HTML report content
            category: Report category (Health, Dental, Group Life)
            report_date: Report timestamp (defaults to now)

        Returns:
            Full path to saved report file
        """
        if report_date is None:
            report_date = datetime.now()

        # Create date-based directory structure
        year_dir = self.archive_root / str(report_date.year)
        month_dir = year_dir / f"{report_date.month:02d}"
        day_dir = month_dir / f"{report_date.day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        time_suffix = report_date.strftime("%H-%M-%S")
        safe_category = category.lower().replace(" ", "_").replace(".", "")
        filename = f"{safe_category}_{time_suffix}.html"
        report_path = day_dir / filename

        # Write HTML report
        report_path.write_text(html, encoding='utf-8')

        # Update metadata index
        self._update_metadata(day_dir, category, filename, report_date, html)

        logger.info(
            "report_archived",
            category=category,
            path=str(report_path),
            size_kb=len(html) // 1024,
            date=report_date.isoformat()
        )

        return report_path

    def _update_metadata(
        self,
        day_dir: Path,
        category: str,
        filename: str,
        report_date: datetime,
        html: str
    ) -> None:
        """
        Update metadata.json index for the day's reports.

        Creates or updates the index with new report entry.

        Args:
            day_dir: Directory for the day
            category: Report category
            filename: Report filename
            report_date: Report timestamp
            html: HTML content (for size calculation)
        """
        metadata_path = day_dir / "metadata.json"

        # Load existing metadata or create new
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError:
                metadata = {"date": report_date.date().isoformat(), "reports": []}
        else:
            metadata = {"date": report_date.date().isoformat(), "reports": []}

        # Check if report already exists (same category and timestamp)
        existing_idx = None
        for idx, report in enumerate(metadata["reports"]):
            if report["filename"] == filename:
                existing_idx = idx
                break

        # Create report entry
        report_entry = {
            "category": category,
            "filename": filename,
            "timestamp": report_date.isoformat(),
            "size_kb": len(html) // 1024
        }

        # Update or append
        if existing_idx is not None:
            metadata["reports"][existing_idx] = report_entry
        else:
            metadata["reports"].append(report_entry)

        # Sort by timestamp (newest first)
        metadata["reports"].sort(key=lambda r: r["timestamp"], reverse=True)

        # Write updated metadata
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def browse_reports(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> list[dict]:
        """
        Browse archived reports with optional filtering.

        Returns reports sorted by date descending (newest first).

        Args:
            start_date: Filter reports from this date
            end_date: Filter reports until this date
            category: Filter by category (case-insensitive)
            limit: Maximum number of reports to return

        Returns:
            List of report metadata dicts with keys:
            - date: ISO date string
            - category: Report category
            - filename: Report filename
            - timestamp: Full ISO timestamp
            - path: Full path to report file
            - size_kb: File size in KB
        """
        reports = []

        # Walk date hierarchy in reverse order (newest first)
        if not self.archive_root.exists():
            return reports

        for year_dir in sorted(self.archive_root.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue

                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue

                    metadata_path = day_dir / "metadata.json"
                    if not metadata_path.exists():
                        continue

                    try:
                        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                    except (json.JSONDecodeError, IOError):
                        continue

                    # Parse date for filtering
                    try:
                        report_date = datetime.fromisoformat(metadata["date"] + "T00:00:00")
                    except (ValueError, KeyError):
                        continue

                    # Apply date filters
                    if start_date and report_date < start_date.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ):
                        continue
                    if end_date and report_date > end_date.replace(
                        hour=23, minute=59, second=59, microsecond=999999
                    ):
                        continue

                    # Process reports in this day
                    for report in metadata.get("reports", []):
                        # Apply category filter (case-insensitive)
                        if category:
                            if report.get("category", "").lower() != category.lower():
                                continue

                        reports.append({
                            "date": metadata["date"],
                            "category": report.get("category", ""),
                            "filename": report.get("filename", ""),
                            "timestamp": report.get("timestamp", ""),
                            "path": str(day_dir / report.get("filename", "")),
                            "size_kb": report.get("size_kb", 0)
                        })

                        # Check limit
                        if len(reports) >= limit:
                            return reports

        return reports

    def get_report(self, date: str, filename: str) -> Optional[str]:
        """
        Retrieve a specific archived report by date and filename.

        Args:
            date: Date string in YYYY-MM-DD format
            filename: Report filename

        Returns:
            HTML content as string, or None if not found
        """
        try:
            date_obj = datetime.fromisoformat(date)
        except ValueError:
            logger.error("invalid_date_format", date=date)
            return None

        report_path = (
            self.archive_root
            / str(date_obj.year)
            / f"{date_obj.month:02d}"
            / f"{date_obj.day:02d}"
            / filename
        )

        if not report_path.exists():
            logger.warning("report_not_found", path=str(report_path))
            return None

        return report_path.read_text(encoding='utf-8')

    def get_dates_with_reports(
        self,
        category: Optional[str] = None,
        limit: int = 30
    ) -> list[str]:
        """
        Get list of dates that have archived reports.

        Useful for calendar-based browsing UI.

        Args:
            category: Filter by category (optional)
            limit: Maximum dates to return

        Returns:
            List of date strings in YYYY-MM-DD format, newest first
        """
        dates = set()

        if not self.archive_root.exists():
            return []

        for year_dir in sorted(self.archive_root.iterdir(), reverse=True):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue

            for month_dir in sorted(year_dir.iterdir(), reverse=True):
                if not month_dir.is_dir() or not month_dir.name.isdigit():
                    continue

                for day_dir in sorted(month_dir.iterdir(), reverse=True):
                    if not day_dir.is_dir() or not day_dir.name.isdigit():
                        continue

                    metadata_path = day_dir / "metadata.json"
                    if not metadata_path.exists():
                        continue

                    # If category filter, check if reports exist for that category
                    if category:
                        try:
                            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                            has_category = any(
                                r.get("category", "").lower() == category.lower()
                                for r in metadata.get("reports", [])
                            )
                            if not has_category:
                                continue
                        except (json.JSONDecodeError, IOError):
                            continue

                    date_str = f"{year_dir.name}-{month_dir.name}-{day_dir.name}"
                    dates.add(date_str)

                    if len(dates) >= limit:
                        return sorted(dates, reverse=True)

        return sorted(dates, reverse=True)
