---
phase: 14-apify-cleanup
plan: 01
subsystem: infrastructure
tags: [apify, cleanup, technical-debt, factiva]

# Dependency graph
requires:
  - phase: 11-insurer-matching-pipeline
    provides: Factiva-only collection pipeline operational
provides:
  - Complete removal of Apify infrastructure (9 source files, 3 dead services, 2 dependencies)
  - Clean services package with no Apify imports
affects: [Phase 14-02 (config cleanup), future maintenance]

# Tech tracking
tech-stack:
  removed: [apify-client>=1.8.0, feedparser>=6.0.0]
  patterns: [Factiva-only collection, dead code removal]

key-files:
  deleted:
    - app/services/sources/ (entire directory - 9 files)
    - app/services/scraper.py
    - app/services/batch_processor.py
    - app/services/relevance_scorer.py
    - tests/test_batch_processor.py
    - tests/test_relevance_scorer.py
  modified:
    - app/services/__init__.py
    - requirements.txt

key-decisions:
  - "Deleted entire sources/ directory containing all 9 Apify source class files"
  - "Removed scraper.py, batch_processor.py, relevance_scorer.py as dead code"
  - "Preserved aiohttp>=3.9.0 - used by FactivaCollector"
  - "Cleaned Phase 2/3 comments that only introduced removed dependencies"

patterns-established:
  - "Services package imports only active services (excel_service, classifier, emailer, reporter)"
  - "Dependencies reflect actual runtime requirements (no unused packages)"

# Metrics
duration: 2min
completed: 2026-02-20
---

# Phase 14 Plan 01: Apify Cleanup Summary

**Removed 14 files (9 Apify sources, 3 dead services, 2 tests) and 2 dependencies from the codebase, leaving only Factiva-based collection infrastructure**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-20T12:27:50Z
- **Completed:** 2026-02-20T12:29:34Z
- **Tasks:** 2
- **Files modified:** 2 (14 deleted)

## Accomplishments
- Deleted entire app/services/sources/ directory with 9 Apify source class files
- Removed 3 dead service files (scraper, batch_processor, relevance_scorer)
- Removed 2 dead test files (test_batch_processor, test_relevance_scorer)
- Removed apify-client and feedparser dependencies from requirements.txt
- Cleaned services __init__.py to remove ApifyScraperService import
- Preserved aiohttp (used by FactivaCollector) and all Factiva pipeline services

## Task Commits

Each task was committed atomically:

1. **Task 1: Delete Apify source directory and dead service files** - `4bf99c3` (chore)
   - 14 files deleted (9 source + 3 service + 2 test)
   - 2,584 lines of code removed

2. **Task 2: Clean services __init__ and remove dependencies** - `c7d482e` (chore)
   - Removed ApifyScraperService import
   - Removed apify-client and feedparser from requirements.txt
   - Cleaned orphaned Phase 2/3 comments

## Files Created/Modified

**Deleted:**
- `app/services/sources/__init__.py` - Sources package init
- `app/services/sources/base.py` - Base Apify source class
- `app/services/sources/google_news.py` - Google News Apify source
- `app/services/sources/valor.py` - Valor Econômico Apify source
- `app/services/sources/cqcs.py` - CQCS Apify source
- `app/services/sources/infomoney.py` - InfoMoney Apify source
- `app/services/sources/estadao.py` - Estadão Apify source
- `app/services/sources/ans.py` - ANS Apify source
- `app/services/sources/rss_source.py` - RSS feed Apify source
- `app/services/scraper.py` - ApifyScraperService and ScraperService (dead code)
- `app/services/batch_processor.py` - BatchProcessor (dead code)
- `app/services/relevance_scorer.py` - RelevanceScorer (dead code)
- `tests/test_batch_processor.py` - BatchProcessor tests (dead code)
- `tests/test_relevance_scorer.py` - RelevanceScorer tests (dead code)

**Modified:**
- `app/services/__init__.py` - Removed ApifyScraperService import
- `requirements.txt` - Removed apify-client, feedparser; cleaned orphaned comments

**Preserved (verified):**
- `app/services/classifier.py` - Factiva pipeline service
- `app/services/deduplicator.py` - Factiva pipeline service
- `app/services/insurer_matcher.py` - Factiva pipeline service

## Decisions Made

**1. Delete entire sources/ directory atomically**
- All 9 Apify source class files removed in one operation
- Prevents partial deletion state during execution

**2. Preserve aiohttp>=3.9.0**
- Used by FactivaCollector for async HTTP requests
- Not Apify-specific despite being added in Phase 3

**3. Clean orphaned comments**
- Removed "Phase 2 - Vertical Slice" and "# Web scraping" comments
- Changed "Phase 3 - News Collection Scale" to "# HTTP client (async)"
- Prevents misleading documentation about removed features

**4. Do NOT delete Factiva pipeline services**
- classifier.py, deduplicator.py, insurer_matcher.py preserved
- Explicit verification checks ensure correct files deleted

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all deletions and edits succeeded on first attempt.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for 14-02:** Config cleanup
- All Apify source files removed, ready to clean config references
- Services package imports only active services
- No Apify dependencies in requirements.txt

**Remaining technical debt:**
- Apify config references in database/env files (Phase 14-02)
- Dead Apify models/schemas may exist (to be identified in 14-02)

**Verification:**
- No import errors from remaining service files
- Services package imports only active services: ClassificationService, GraphEmailService, ReportService
- Factiva pipeline services intact and functional

---
*Phase: 14-apify-cleanup*
*Completed: 2026-02-20*
