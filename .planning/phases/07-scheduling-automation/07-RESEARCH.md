# Phase 7: Scheduling & Automation - Research

**Researched:** 2026-02-04
**Domain:** Task scheduling, APScheduler, timezone handling, job persistence
**Confidence:** HIGH

## Summary

This phase implements automated scheduling for the three product category runs (Health, Dental, Group Life) using APScheduler integrated with FastAPI. Research confirms APScheduler 3.10+ as the standard choice for Python application-level scheduling, with AsyncIOScheduler for async FastAPI apps.

The existing codebase already has run orchestration endpoints (`POST /api/runs/execute` and `POST /api/runs/execute/category`) with full tracking. This phase adds:
1. Scheduler service wrapping APScheduler with job management
2. Schedule configuration model and persistence
3. Admin API endpoints for job control
4. Dashboard UI for viewing/modifying schedules

**Primary recommendation:** Use APScheduler's AsyncIOScheduler with SQLAlchemyJobStore for job persistence, CronTrigger with explicit `America/Sao_Paulo` timezone, and FastAPI lifespan events for graceful startup/shutdown.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.10.4 | Job scheduling | Production-ready, cron triggers, persistence support, async-compatible. The Python standard for in-app scheduling. |
| zoneinfo | stdlib (3.9+) | Timezone handling | Python stdlib since 3.9, uses IANA database, no pytz issues |
| tzdata | 2024.2+ | Timezone data (Windows) | Required on Windows where system tz data may be missing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy (existing) | 2.0+ | Job store persistence | Already in project; APScheduler uses SQLAlchemyJobStore |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | Celery + Redis | Celery requires Redis/RabbitMQ infrastructure, overkill for single-server |
| APScheduler | Windows Task Scheduler only | Less flexibility, no in-app control, no job persistence across restarts |
| APScheduler | schedule library | No persistence, no async, stops if app crashes |

**Installation:**
```bash
# APScheduler already in requirements.txt from Phase 1
# Verify tzdata for Windows compatibility
pip install APScheduler==3.10.4 tzdata>=2024.2
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── services/
│   └── scheduler_service.py   # APScheduler wrapper with job management
├── models/
│   └── schedule.py            # Schedule configuration model
├── schemas/
│   └── schedule.py            # Pydantic schemas for schedule API
├── routers/
│   └── schedules.py           # Schedule management endpoints
└── main.py                    # Lifespan events for scheduler start/stop
```

### Pattern 1: Scheduler Service Singleton
**What:** Single scheduler instance managed through a service class
**When to use:** Always - prevents multiple scheduler instances
**Example:**
```python
# Source: APScheduler official docs + FastAPI best practices
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Singleton service managing APScheduler for category runs.

    Handles job persistence, timezone configuration, and
    provides API for job management (pause/resume/modify).
    """
    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

    # Default schedules per category
    DEFAULT_SCHEDULES = {
        "Health": {"hour": 6, "minute": 0},
        "Dental": {"hour": 7, "minute": 0},
        "Group Life": {"hour": 8, "minute": 0},
    }

    def __new__(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            jobstores = {
                'default': SQLAlchemyJobStore(
                    url='sqlite:///./data/brasilintel.db',
                    tablename='apscheduler_jobs'
                )
            }
            job_defaults = {
                'coalesce': True,           # Combine missed runs into one
                'max_instances': 1,         # Prevent overlapping runs
                'misfire_grace_time': 3600  # 1 hour grace for missed jobs
            }
            self._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                job_defaults=job_defaults,
                timezone=self.SAO_PAULO_TZ
            )

    def start(self) -> None:
        """Start scheduler and initialize default jobs if needed."""
        if not self._scheduler.running:
            self._scheduler.start()
            self._ensure_default_jobs()
            logger.info("Scheduler started with São Paulo timezone")

    def shutdown(self, wait: bool = False) -> None:
        """Gracefully shutdown scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown complete")
```

### Pattern 2: FastAPI Lifespan Integration
**What:** Start scheduler on app startup, shutdown gracefully on app close
**When to use:** Always - ensures clean lifecycle management
**Example:**
```python
# Source: FastAPI official docs
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.scheduler_service import SchedulerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler_service = SchedulerService()
    scheduler_service.start()
    yield
    # Shutdown
    scheduler_service.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
```

### Pattern 3: CronTrigger with Explicit Timezone
**What:** Configure cron triggers with explicit timezone to avoid DST issues
**When to use:** All scheduled jobs
**Example:**
```python
# Source: APScheduler CronTrigger docs
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

# Create trigger with explicit timezone
trigger = CronTrigger(
    hour=6,
    minute=0,
    timezone=ZoneInfo("America/Sao_Paulo")
)

# Or from crontab string (always specify timezone!)
trigger = CronTrigger.from_crontab(
    "0 6 * * *",  # 6:00 AM daily
    timezone=ZoneInfo("America/Sao_Paulo")
)
```

### Pattern 4: Job ID Convention
**What:** Use predictable job IDs for management
**When to use:** All scheduled jobs
**Example:**
```python
# Job IDs follow pattern: category_run_{category_slug}
JOB_ID_PATTERN = "category_run_{category}"

def get_job_id(category: str) -> str:
    return JOB_ID_PATTERN.format(category=category.lower().replace(" ", "_"))
    # "Health" -> "category_run_health"
    # "Group Life" -> "category_run_group_life"
```

### Anti-Patterns to Avoid
- **Creating scheduler per request:** Creates multiple schedulers, duplicate jobs. Use singleton pattern.
- **Relying on scheduler default timezone:** Always explicitly set timezone on scheduler AND triggers.
- **Using pytz directly with datetime constructor:** Known bug returns wrong offset for São Paulo. Use zoneinfo instead.
- **Missing replace_existing=True:** Causes duplicate jobs on app restart.
- **Not handling Gunicorn multi-worker:** If using multiple workers, jobs run multiple times. Use single worker or external coordination.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron expression parsing | Custom regex parser | `CronTrigger.from_crontab()` | Edge cases (weekdays, last day of month), DST handling |
| Timezone conversion | Manual offset math | `zoneinfo.ZoneInfo` | DST transitions, historical changes, IANA database |
| Job persistence | Custom DB schema | `SQLAlchemyJobStore` | Handles serialization, updates, queries automatically |
| Missed job handling | Custom tracking | `misfire_grace_time` + `coalesce` | APScheduler handles automatically |
| Next run calculation | DateTime arithmetic | `job.next_run_time` | Accounts for DST, cron complexity |

**Key insight:** Timezone and scheduling edge cases are notoriously complex (DST transitions, leap years, month-end dates). APScheduler has battle-tested implementations.

## Common Pitfalls

### Pitfall 1: Multiple Scheduler Instances
**What goes wrong:** Jobs run 2-4x times, duplicate processing, race conditions
**Why it happens:** Each Gunicorn worker or app restart creates new scheduler
**How to avoid:**
- Singleton pattern for scheduler service
- `replace_existing=True` when adding jobs
- For multi-worker: single worker or external job store coordination
**Warning signs:** Logs show same job running multiple times simultaneously

### Pitfall 2: Wrong Timezone for São Paulo
**What goes wrong:** Jobs run at wrong time (3 hours off from UTC, or wrong during DST)
**Why it happens:** Using system timezone, pytz bug with constructor, missing explicit timezone
**How to avoid:**
- Always use `zoneinfo.ZoneInfo("America/Sao_Paulo")`
- Set timezone on both scheduler AND individual triggers
- Never use `pytz.timezone()` directly in datetime constructor
**Warning signs:** Jobs run at UTC time instead of São Paulo time

### Pitfall 3: Lost Jobs After Restart
**What goes wrong:** Scheduled jobs disappear when app restarts
**Why it happens:** Default `MemoryJobStore` doesn't persist
**How to avoid:**
- Use `SQLAlchemyJobStore` with existing database
- Explicit job IDs for identification
- `replace_existing=True` to update rather than fail on restart
**Warning signs:** Jobs visible before restart, gone after

### Pitfall 4: Jobs Never Fire (Misfire)
**What goes wrong:** Jobs scheduled during app downtime never run
**Why it happens:** Default `misfire_grace_time` is 1 second, job considered too old
**How to avoid:**
- Set `misfire_grace_time=3600` (1 hour) or appropriate value
- Enable `coalesce=True` to combine missed runs
**Warning signs:** Jobs show in scheduler but never execute

### Pitfall 5: Job Overlap During Long Runs
**What goes wrong:** Next scheduled run starts while previous still running
**Why it happens:** Category run takes 30+ minutes, next trigger fires
**How to avoid:**
- Set `max_instances=1` in job defaults
- APScheduler skips execution if instance already running
**Warning signs:** Multiple runs for same category at same time

### Pitfall 6: DST Transition Issues
**What goes wrong:** Job runs twice or not at all on DST change dates
**Why it happens:** Clock moves forward/backward, scheduled time becomes ambiguous
**How to avoid:**
- Schedule jobs at times unlikely to overlap DST (not 2-3 AM)
- Accept that DST dates may have slight timing variations
- São Paulo DST ends in February, starts in October/November
**Warning signs:** Double runs in March/November

## Code Examples

### Complete Scheduler Service
```python
# Source: APScheduler docs + project patterns
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from zoneinfo import ZoneInfo
from datetime import datetime
from typing import Optional, Any
import logging
import httpx

logger = logging.getLogger(__name__)

class SchedulerService:
    """Manages scheduled category runs."""

    _instance: Optional["SchedulerService"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")

    DEFAULT_SCHEDULES = {
        "Health": {"hour": 6, "minute": 0, "enabled": True},
        "Dental": {"hour": 7, "minute": 0, "enabled": True},
        "Group Life": {"hour": 8, "minute": 0, "enabled": True},
    }

    def __new__(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self._init_scheduler()

    def _init_scheduler(self) -> None:
        """Initialize APScheduler with SQLite job store."""
        jobstores = {
            'default': SQLAlchemyJobStore(
                url='sqlite:///./data/brasilintel.db',
                tablename='apscheduler_jobs'
            )
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 3600,
        }
        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=self.SAO_PAULO_TZ
        )
        # Add event listeners for tracking
        self._scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

    def _job_listener(self, event) -> None:
        """Log job execution results."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} completed successfully")

    @staticmethod
    def get_job_id(category: str) -> str:
        """Generate job ID from category name."""
        return f"category_run_{category.lower().replace(' ', '_')}"

    async def _execute_category_run(self, category: str) -> None:
        """
        Job function that triggers category run via internal API.

        Uses httpx to call the existing /api/runs/execute/category endpoint.
        """
        logger.info(f"Scheduled run starting for category: {category}")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/runs/execute/category",
                    json={
                        "category": category,
                        "send_email": True,
                        "enabled_only": True
                    },
                    timeout=1800.0  # 30 minute timeout for full category
                )
                response.raise_for_status()
                result = response.json()
                logger.info(
                    f"Scheduled run completed for {category}: "
                    f"{result.get('insurers_processed', 0)} insurers, "
                    f"{result.get('items_found', 0)} items"
                )
        except Exception as e:
            logger.error(f"Scheduled run failed for {category}: {e}")
            raise

    def start(self) -> None:
        """Start the scheduler and ensure default jobs exist."""
        if not self._scheduler.running:
            self._scheduler.start()
            self._ensure_default_jobs()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = False) -> None:
        """Shutdown the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")

    def _ensure_default_jobs(self) -> None:
        """Create default jobs if they don't exist."""
        for category, config in self.DEFAULT_SCHEDULES.items():
            job_id = self.get_job_id(category)
            existing = self._scheduler.get_job(job_id)

            if existing is None:
                trigger = CronTrigger(
                    hour=config["hour"],
                    minute=config["minute"],
                    timezone=self.SAO_PAULO_TZ
                )
                self._scheduler.add_job(
                    self._execute_category_run,
                    trigger=trigger,
                    args=[category],
                    id=job_id,
                    name=f"{category} Daily Run",
                    replace_existing=True
                )
                logger.info(f"Created default job for {category} at {config['hour']:02d}:{config['minute']:02d}")

    def get_schedule(self, category: str) -> Optional[dict]:
        """Get schedule info for a category."""
        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if job is None:
            return None

        return {
            "category": category,
            "job_id": job_id,
            "enabled": job.next_run_time is not None,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }

    def get_all_schedules(self) -> list[dict]:
        """Get all category schedules."""
        schedules = []
        for category in self.DEFAULT_SCHEDULES:
            schedule = self.get_schedule(category)
            if schedule:
                schedules.append(schedule)
        return schedules

    def update_schedule(
        self,
        category: str,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        cron_expression: Optional[str] = None
    ) -> dict:
        """
        Update schedule for a category.

        Can specify hour/minute OR a full cron expression.
        """
        job_id = self.get_job_id(category)

        if cron_expression:
            trigger = CronTrigger.from_crontab(
                cron_expression,
                timezone=self.SAO_PAULO_TZ
            )
        else:
            job = self._scheduler.get_job(job_id)
            current_hour = hour if hour is not None else 6
            current_minute = minute if minute is not None else 0

            trigger = CronTrigger(
                hour=current_hour,
                minute=current_minute,
                timezone=self.SAO_PAULO_TZ
            )

        self._scheduler.reschedule_job(
            job_id,
            trigger=trigger
        )

        return self.get_schedule(category)

    def pause_job(self, category: str) -> dict:
        """Pause a category's scheduled job."""
        job_id = self.get_job_id(category)
        self._scheduler.pause_job(job_id)
        logger.info(f"Paused job for {category}")
        return self.get_schedule(category)

    def resume_job(self, category: str) -> dict:
        """Resume a category's scheduled job."""
        job_id = self.get_job_id(category)
        self._scheduler.resume_job(job_id)
        logger.info(f"Resumed job for {category}")
        return self.get_schedule(category)

    def trigger_now(self, category: str) -> None:
        """Trigger immediate execution of a category run."""
        job_id = self.get_job_id(category)
        job = self._scheduler.get_job(job_id)

        if job:
            # Modify job to run now (next tick)
            self._scheduler.modify_job(
                job_id,
                next_run_time=datetime.now(self.SAO_PAULO_TZ)
            )
            logger.info(f"Triggered immediate run for {category}")
```

### Schedule Configuration Model
```python
# app/models/schedule.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.database import Base

class ScheduleConfig(Base):
    """
    Persistent schedule configuration per category.

    Stores user-configured schedules separate from APScheduler's
    internal job store for easier querying and admin UI.
    """
    __tablename__ = "schedule_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), unique=True, nullable=False)

    # Cron configuration
    cron_expression = Column(String(100), default="0 6 * * *")
    hour = Column(Integer, default=6)
    minute = Column(Integer, default=0)

    # Status
    enabled = Column(Boolean, default=True)

    # Tracking
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ScheduleConfig(category='{self.category}', enabled={self.enabled})>"
```

### Schedule API Endpoints
```python
# app/routers/schedules.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])

class ScheduleInfo(BaseModel):
    """Response model for schedule information."""
    category: str
    job_id: str
    enabled: bool
    next_run_time: Optional[str]
    trigger: str

class ScheduleUpdate(BaseModel):
    """Request model for updating a schedule."""
    hour: Optional[int] = Field(None, ge=0, le=23)
    minute: Optional[int] = Field(None, ge=0, le=59)
    cron_expression: Optional[str] = Field(None, description="Full cron expression (overrides hour/minute)")
    enabled: Optional[bool] = None

@router.get("", response_model=list[ScheduleInfo])
def list_schedules() -> list[dict]:
    """List all category schedules with next run times."""
    scheduler = SchedulerService()
    return scheduler.get_all_schedules()

@router.get("/{category}", response_model=ScheduleInfo)
def get_schedule(category: str) -> dict:
    """Get schedule for a specific category."""
    scheduler = SchedulerService()
    schedule = scheduler.get_schedule(category)
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule for {category}")
    return schedule

@router.put("/{category}", response_model=ScheduleInfo)
def update_schedule(category: str, update: ScheduleUpdate) -> dict:
    """Update schedule configuration for a category."""
    scheduler = SchedulerService()

    # Handle enable/disable
    if update.enabled is not None:
        if update.enabled:
            scheduler.resume_job(category)
        else:
            scheduler.pause_job(category)

    # Handle time changes
    if update.cron_expression or update.hour is not None or update.minute is not None:
        scheduler.update_schedule(
            category,
            hour=update.hour,
            minute=update.minute,
            cron_expression=update.cron_expression
        )

    return scheduler.get_schedule(category)

@router.post("/{category}/trigger")
def trigger_manual_run(category: str) -> dict:
    """Trigger an immediate run for a category."""
    scheduler = SchedulerService()
    scheduler.trigger_now(category)
    return {"status": "triggered", "category": category}

@router.post("/{category}/pause", response_model=ScheduleInfo)
def pause_schedule(category: str) -> dict:
    """Pause scheduled runs for a category."""
    scheduler = SchedulerService()
    return scheduler.pause_job(category)

@router.post("/{category}/resume", response_model=ScheduleInfo)
def resume_schedule(category: str) -> dict:
    """Resume scheduled runs for a category."""
    scheduler = SchedulerService()
    return scheduler.resume_job(category)
```

### Run History Enhancement
```python
# Modify existing Run model to add scheduled tracking
# app/models/run.py additions

# Add to existing Run model:
scheduled_run_id = Column(String(100), nullable=True)  # APScheduler job ID
scheduled_time = Column(DateTime, nullable=True)  # Originally scheduled time
actual_start_delay_seconds = Column(Integer, nullable=True)  # Delay from scheduled
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pytz library | zoneinfo (stdlib) | Python 3.9 (2020) | No external dependency, correct DST handling |
| @app.on_event("startup") | lifespan context manager | FastAPI 0.93 (2023) | Cleaner resource management, no deprecation warnings |
| APScheduler 3.x | APScheduler 3.10.4+ | Ongoing | Async improvements, better SQLAlchemy 2.0 support |

**Deprecated/outdated:**
- `pytz.timezone()` with datetime constructor: Known bug returns LMT offset for São Paulo
- FastAPI `@app.on_event("startup/shutdown")`: Deprecated, use lifespan
- APScheduler `BackgroundScheduler` in async apps: Use `AsyncIOScheduler` instead

## Open Questions

1. **Multi-worker deployment**
   - What we know: APScheduler runs per-process, Gunicorn workers create duplicates
   - What's unclear: Whether Windows Scheduled Task deployment uses multiple workers
   - Recommendation: Single worker for scheduler process, or use Redis for coordination

2. **Job store table conflicts**
   - What we know: SQLAlchemyJobStore creates its own table
   - What's unclear: Whether to share connection pool with main app
   - Recommendation: Use separate table prefix, same database file is fine

3. **Manual trigger vs scheduled trigger distinction**
   - What we know: Both call same endpoint
   - What's unclear: Best way to track which triggered the run
   - Recommendation: Use `trigger_type` field already on Run model ("scheduled" vs "manual")

## Sources

### Primary (HIGH confidence)
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html) - Scheduler configuration, job stores, triggers
- [APScheduler CronTrigger Documentation](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html) - Cron expression syntax, timezone handling
- [APScheduler BaseScheduler API](https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/base.html) - Job management methods
- [Python zoneinfo Documentation](https://docs.python.org/3/library/zoneinfo.html) - Timezone handling
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) - Application lifecycle management

### Secondary (MEDIUM confidence)
- [Scheduled Jobs with FastAPI and APScheduler](https://ahaw021.medium.com/scheduled-jobs-with-fastapi-and-apscheduler-5a4c50580b0e) - Integration patterns
- [Running Scheduled Jobs in FastAPI](https://www.nashruddinamin.com/blog/running-scheduled-jobs-in-fastapi) - Best practices
- [Common Mistakes with APScheduler](https://sepgh.medium.com/common-mistakes-with-using-apscheduler-in-your-python-and-django-applications-100b289b812c) - Pitfalls

### Tertiary (LOW confidence)
- [FastAPI Scheduler Extension](https://github.com/amisadmin/fastapi-scheduler) - Alternative approach (not recommended for this project)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - APScheduler is well-documented, widely used
- Architecture: HIGH - Patterns verified against official docs and existing codebase
- Pitfalls: HIGH - Multiple sources confirm common issues
- Timezone handling: HIGH - zoneinfo is stdlib, DST issues well-documented

**Research date:** 2026-02-04
**Valid until:** 60 days (APScheduler 3.x is stable, patterns unlikely to change)
