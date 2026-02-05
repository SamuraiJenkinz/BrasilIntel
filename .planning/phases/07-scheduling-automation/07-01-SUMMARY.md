---
phase: 07-scheduling-automation
plan: 01
subsystem: scheduling
tags: [apscheduler, timezone, singleton, automation]
requires:
  - 06-05 (delivery integration)
provides:
  - SchedulerService singleton
  - SQLite job persistence
  - Sao Paulo timezone scheduling
affects:
  - 07-02 (schedule schemas)
  - 07-03 (schedule endpoints)
tech-stack:
  added:
    - APScheduler>=3.10.4
    - tzdata>=2024.2
  patterns:
    - Singleton with class variables
    - AsyncIOScheduler for FastAPI
    - Internal HTTP job execution
key-files:
  created:
    - app/services/scheduler_service.py
    - tests/test_scheduler_service.py
  modified:
    - requirements.txt
    - app/config.py
decisions:
  - SQLAlchemyJobStore for SQLite persistence
  - Internal HTTP call for job execution
  - ZoneInfo for Sao Paulo timezone
metrics:
  duration: ~4 minutes
  completed: 2026-02-05
---

# Phase 7 Plan 1: SchedulerService Core Summary

APScheduler singleton with Sao Paulo timezone and SQLite persistence for automated category runs.

## What Was Built

### 1. Dependencies (requirements.txt)
- Added APScheduler>=3.10.4 for job scheduling
- Added tzdata>=2024.2 for Windows timezone support

### 2. Schedule Configuration (app/config.py)
Extended Settings class with scheduler settings:
- `scheduler_enabled`: Global on/off toggle
- `schedule_health_cron`: "0 6 * * *" (6:00 AM)
- `schedule_dental_cron`: "0 7 * * *" (7:00 AM)
- `schedule_group_life_cron`: "0 8 * * *" (8:00 AM)
- `schedule_*_enabled`: Per-category enable flags
- `scheduler_misfire_grace_time`: 3600 seconds (1 hour)
- `scheduler_coalesce`: True (combine missed runs)
- `scheduler_max_instances`: 1 (prevent overlap)

Added `get_schedule_config(category)` helper method.

### 3. SchedulerService (app/services/scheduler_service.py)
416-line singleton service with:

**Core Features:**
- Singleton pattern via `__new__` and class variables
- AsyncIOScheduler with Sao Paulo timezone (ZoneInfo)
- SQLAlchemyJobStore pointing to brasilintel.db
- Event listeners for job execution logging

**Job Management Methods:**
- `get_job_id(category)`: Convert category to job ID slug
- `start()`: Start scheduler, create default jobs
- `shutdown(wait)`: Graceful shutdown
- `_ensure_default_jobs()`: Create 3 category jobs on startup
- `_execute_category_run(category)`: HTTP POST to /api/runs/execute/category

**Schedule Control Methods:**
- `get_schedule(category)`: Get job info (next_run, trigger, paused)
- `get_all_schedules()`: All 3 category schedules
- `update_schedule(category, hour, minute, cron_expression)`: Reschedule
- `pause_job(category)`: Pause scheduled job
- `resume_job(category)`: Resume paused job
- `trigger_now(category)`: Immediate execution

### 4. Unit Tests (tests/test_scheduler_service.py)
16 tests covering:
- Singleton pattern (2 tests)
- Job ID generation (4 tests)
- Timezone configuration (2 tests)
- Scheduler initialization (4 tests)
- Schedule retrieval (2 tests)
- Instance reset (2 tests)

## Key Patterns

### Job ID Convention
```python
category_run_{category_slug}
# Health -> category_run_health
# Group Life -> category_run_group_life
```

### Job Execution via Internal HTTP
```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/runs/execute/category",
        json={"category": category, "send_email": True, "enabled_only": True},
        timeout=1800.0  # 30 minutes
    )
```

### Timezone-Aware Cron Triggers
```python
trigger = CronTrigger.from_crontab(
    config["cron"],
    timezone=self.SAO_PAULO_TZ
)
```

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 45965e8 | chore | Add APScheduler dependencies and schedule config |
| f95f013 | feat | Create SchedulerService singleton with APScheduler |
| 0050392 | test | Add SchedulerService unit tests |

## Verification Results

All verification criteria met:
- pip install succeeds with new dependencies
- SchedulerService initializes correctly
- get_settings().schedule_health_cron returns "0 6 * * *"
- 16/16 tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 07-02: Schedule Schemas & Run Model Enhancement
- SchedulerService singleton available for import
- Schedule configuration accessible via get_settings()
- Job ID pattern established for API endpoints
