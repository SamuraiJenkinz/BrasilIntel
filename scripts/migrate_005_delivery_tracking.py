"""
Migration 005: Add delivery tracking columns to runs table.

Adds columns for tracking email delivery status, PDF generation,
and critical alert notifications (Phase 6).

Run with: python scripts/migrate_005_delivery_tracking.py
"""
import sqlite3
import sys
from pathlib import Path


# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "brasilintel.db"


def get_existing_columns(cursor, table_name: str) -> set[str]:
    """Get set of existing column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def migrate():
    """Run the migration."""
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at {DB_PATH}")
        print("Database will be created automatically when the application first runs.")
        sys.exit(0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        existing = get_existing_columns(cursor, "runs")
        print(f"[INFO] Existing columns in runs: {len(existing)}")

        # Columns to add with their definitions
        new_columns = [
            ("email_status", "VARCHAR(20)"),
            ("email_sent_at", "DATETIME"),
            ("email_recipients_count", "INTEGER DEFAULT 0"),
            ("email_error_message", "TEXT"),
            ("pdf_generated", "BOOLEAN DEFAULT 0"),
            ("pdf_size_bytes", "INTEGER"),
            ("critical_alert_sent", "BOOLEAN DEFAULT 0"),
            ("critical_alert_sent_at", "DATETIME"),
            ("critical_insurers_count", "INTEGER DEFAULT 0"),
        ]

        added = 0
        skipped = 0

        for col_name, col_def in new_columns:
            if col_name in existing:
                print(f"[SKIP] Column '{col_name}' already exists")
                skipped += 1
            else:
                print(f"[ADD] Adding column '{col_name}'...")
                cursor.execute(f"ALTER TABLE runs ADD COLUMN {col_name} {col_def}")
                added += 1

        conn.commit()

        print()
        print(f"[DONE] Migration complete")
        print(f"       Added: {added} columns")
        print(f"       Skipped: {skipped} columns (already exist)")

        # Verify
        final_cols = get_existing_columns(cursor, "runs")
        print(f"       Total columns in runs: {len(final_cols)}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Migration 005: Delivery Tracking Columns")
    print("=" * 60)
    migrate()
