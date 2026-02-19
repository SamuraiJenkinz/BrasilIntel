---
phase: 09-enterprise-api-foundation
plan: 02
subsystem: database
tags: [sqlalchemy, sqlite, orm, factiva, equity, api-events, migration]

# Dependency graph
requires:
  - phase: 09-01
    provides: MMCAuthService JWT token authentication layer

provides:
  - ApiEvent ORM model with 9-value ApiEventType enum for API observability
  - FactivaConfig ORM model with seeded defaults (i82,i832 / MM / insurance reinsurance / 25)
  - EquityTicker ORM model with BVMF default exchange for Brazilian market
  - Migration 007 script creating all three tables (idempotent)
  - Models registered in __init__.py and main.py for auto-table creation

affects:
  - 09-03 (MMCAuthService uses ApiEvent logging)
  - 10 (FactivaCollector reads FactivaConfig row id=1)
  - 11 (EquityPriceClient reads EquityTicker mappings)
  - 12 (EmailEnterpriseService logs ApiEvent EMAIL_SENT/EMAIL_FALLBACK)
  - 13 (Admin dashboard reads api_events for API health display)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Port-from-MDInsights: verbatim copy with docstring rename + domain-specific default change (exchange=BVMF)"
    - "Migration pattern: raw sqlite3 with CREATE TABLE IF NOT EXISTS + INSERT OR IGNORE for idempotency"
    - "Model registration: import module-level noqa imports in main.py to register with Base.metadata"

key-files:
  created:
    - app/models/api_event.py
    - app/models/factiva_config.py
    - app/models/equity_ticker.py
    - scripts/migrate_007_enterprise_api_tables.py
  modified:
    - app/models/__init__.py
    - app/main.py

key-decisions:
  - "EquityTicker.exchange defaults to BVMF (not NYSE) — BrasilIntel targets Brazilian market (B3 exchange)"
  - "All three Phase 9-12 tables created in single migration 007 — avoids per-phase migration scripts"
  - "ApiEvent.run_id is nullable — supports out-of-pipeline calls (e.g. test scripts)"
  - "FactivaConfig seeded at migration time with INSERT OR IGNORE — row always present for FactivaCollector"

patterns-established:
  - "Phase 9+ model registration: add both named import to __init__.py AND module-level noqa import to main.py"
  - "MDInsights port pattern: change docstring project name, adapt domain-specific defaults (e.g. exchange), keep all logic verbatim"

# Metrics
duration: 2min
completed: 2026-02-19
---

# Phase 9 Plan 02: Enterprise API ORM Models and Migration Summary

**Three enterprise API tables (api_events, factiva_config, equity_tickers) created via ORM models ported from MDInsights with BVMF exchange default and seeded factiva_config row**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-19T18:45:11Z
- **Completed:** 2026-02-19T18:47:38Z
- **Tasks:** 2 of 2
- **Files modified:** 6

## Accomplishments

- Ported three enterprise API ORM models from MDInsights with BrasilIntel-specific adaptation (BVMF exchange default)
- ApiEventType enum has all 9 event types covering auth, news, equity, and email API interactions
- Migration 007 creates all three tables idempotently and seeds factiva_config row id=1 with correct defaults
- Models registered in both `__init__.py` (named exports) and `main.py` (module noqa imports for Base.metadata)
- App starts cleanly with new models registered; migration confirmed idempotent on second run

## Task Commits

Each task was committed atomically:

1. **Task 1: Port three ORM models from MDInsights** - `9026f0d` (feat)
2. **Task 2: Create and run migration 007 for enterprise API tables** - `0f8cb07` (feat)

## Files Created/Modified

- `app/models/api_event.py` - ApiEvent ORM model + ApiEventType enum (9 values: TOKEN_*, NEWS_*, EQUITY_*, EMAIL_*)
- `app/models/factiva_config.py` - FactivaConfig single-row config table (industry_codes, company_codes, keywords, page_size, enabled)
- `app/models/equity_ticker.py` - EquityTicker mapping table (entity_name, ticker, exchange=BVMF, enabled)
- `scripts/migrate_007_enterprise_api_tables.py` - Idempotent migration creating all 3 tables and seeding factiva_config
- `app/models/__init__.py` - Added ApiEvent, ApiEventType, FactivaConfig, EquityTicker to package exports
- `app/main.py` - Added module-level noqa imports for new models (ensures Base.metadata.create_all registers them)

## Decisions Made

- **BVMF as default exchange:** EquityTicker.exchange defaults to "BVMF" (B3, Brazilian exchange) rather than "NYSE" from the MDInsights original — BrasilIntel monitors Brazilian insurers whose parent companies trade on B3
- **Single migration for all three tables:** Rather than splitting across Phases 10, 11, 12, migration 007 creates all enterprise API tables upfront, avoiding per-phase migration complexity
- **ApiEvent.run_id nullable:** Out-of-pipeline calls (auth test scripts, manual triggers) can log events without a run context

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Tables are created automatically by migration and on app startup.

## Next Phase Readiness

- All three enterprise API tables exist in the database with correct schemas
- factiva_config row id=1 is seeded and ready for FactivaCollector (Phase 10)
- EquityTicker table ready for admin-managed ticker mappings (Phase 11)
- api_events table ready for MMCAuthService event logging (Phase 9-03)
- Plan 09-03 (MMCAuthService implementation) can proceed immediately

---
*Phase: 09-enterprise-api-foundation*
*Completed: 2026-02-19*
