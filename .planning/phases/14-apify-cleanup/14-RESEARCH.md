# Phase 14: Apify Cleanup - Research Findings

**Research Date**: 2026-02-20
**Project**: BrasilIntel
**Phase**: 14 - Apify Cleanup
**Researcher**: GSD Phase Researcher Agent

## Executive Summary

Phase 14 is a **pure removal/cleanup phase** with no new functionality. The Factiva pipeline is fully operational (Phases 10-11 complete), making all Apify infrastructure obsolete. This research identifies all Apify-related files, references, and integration points across the BrasilIntel codebase.

**Key Findings**:
- 8 source class files exist in `app/services/sources/` (base + 7 sources)
- ScraperService is referenced in 4 files (scraper.py, runs.py, __init__.py, batch_processor.py)
- Apify logic is NOT currently used in pipeline (Factiva-only since Phase 11)
- Legacy ApifyScraperService class exists for backward compatibility but is NOT used
- Admin UI has NO source management pages (already removed in earlier phases)
- APIFY_TOKEN in .env.example, config.py
- 2 dependencies: apify-client, feedparser

---

## 1. Files in `app/services/sources/` Directory

**Location**: `C:\BrasilIntel\app\services\sources\`

### Complete File List
```
__init__.py         (870 bytes)  - Package exports and imports
base.py            (4,669 bytes) - NewsSource abstract base, ScrapedNewsItem, SourceRegistry
google_news.py     (8,525 bytes) - GoogleNewsSource (Apify Google News actor)
valor.py           (8,061 bytes) - ValorSource (Valor Economico scraper)
cqcs.py            (8,525 bytes) - CQCSSource (CQCS news scraper)
infomoney.py       (728 bytes)   - InfoMoneySource (InfoMoney scraper)
estadao.py         (887 bytes)   - EstadaoSource (Estadao scraper)
ans.py             (641 bytes)   - ANSSource (ANS news scraper)
rss_source.py      (5,985 bytes) - RSSNewsSource (RSS feed parser)
```

**Total**: 8 files (1 base + 7 source implementations)

### `__init__.py` Exports
```python
from app.services.sources.base import NewsSource, ScrapedNewsItem, SourceRegistry
from app.services.sources.google_news import GoogleNewsSource
from app.services.sources.rss_source import RSSNewsSource
from app.services.sources.infomoney import InfoMoneySource
from app.services.sources.estadao import EstadaoSource
from app.services.sources.ans import ANSSource
from app.services.sources.valor import ValorSource
from app.services.sources.cqcs import CQCSSource

__all__ = [
    "NewsSource",
    "ScrapedNewsItem",
    "SourceRegistry",
    "GoogleNewsSource",
    "RSSNewsSource",
    "InfoMoneySource",
    "EstadaoSource",
    "ANSSource",
    "ValorSource",
    "CQCSSource",
]
```

---

## 2. ScraperService Import/Reference Analysis

### Files Importing ScraperService

#### `app/services/scraper.py` (347 lines)
**Purpose**: Contains BOTH ApifyScraperService and ScraperService classes

**ScraperService Class** (Lines 147-346):
- Multi-source scraper using SourceRegistry
- Imports from `app.services.sources` (SourceRegistry, ScrapedNewsItem, GoogleNewsSource)
- Uses `self.sources = SourceRegistry.get_all()` or specific sources
- Methods: `scrape_insurer()`, `process_category()`, `process_insurers()`, `health_check()`
- **STATUS**: NOT used in current pipeline (Factiva-only)

**ApifyScraperService Class** (Lines 30-144):
- Legacy backward compatibility wrapper
- Delegates to GoogleNewsSource internally
- Methods: `search_google_news()`, `search_insurer()`, `health_check()`
- **STATUS**: Exists for backward compat but NOT used

**Exports**: `__all__ = ["ScrapedNewsItem", "ApifyScraperService", "ScraperService"]`

#### `app/services/__init__.py` (7 lines)
```python
from app.services.scraper import ApifyScraperService
```
**STATUS**: Exports ApifyScraperService for backward compatibility

#### `app/routers/runs.py` (841 lines)
**Import**: Line 386 - `scraper = ScraperService()`

**Functions Using ScraperService**:
1. `_execute_single_insurer_run()` (Lines 364-470)
   - **STATUS**: DEPRECATED - not used in current pipeline
   - Creates `ScraperService()`, calls `scraper.scrape_insurer()`
   - Phase 2 compatibility mode only

2. `_execute_category_run()` (Lines 473-564)
   - **STATUS**: DEPRECATED - not used in current pipeline
   - Creates `ScraperService()`, calls `scraper.process_category()`
   - Phase 3 compatibility mode only

**Current Active Pipeline**: `_execute_factiva_pipeline()` (Lines 189-361)
- **NO ScraperService usage** - uses FactivaCollector directly
- This is the ONLY pipeline path used since Phase 11

#### `app/services/batch_processor.py` (100+ lines)
**Imports**: Line 19 - `from app.services.sources import SourceRegistry, ScrapedNewsItem, NewsSource`

**Usage**:
- Line 96: `self.sources = sources if sources is not None else SourceRegistry.get_all()`
- Used by ScraperService but NOT used in Factiva pipeline

**STATUS**: Dead code - batch processor is only called by ScraperService, which is not used

---

## 3. Pipeline Apify Branching Logic

### Current State: NO Apify Branching

**File**: `app/routers/runs.py`

**Entry Point**: `/api/runs/execute` (Line 71)
- Calls `_execute_factiva_pipeline()` directly (Line 100)
- No conditional logic or fallback to Apify

**Entry Point 2**: `/api/runs/execute/category` (Line 627)
- Also calls `_execute_factiva_pipeline()` directly (Line 655)

**Legacy Functions** (NOT in active path):
- `_execute_single_insurer_run()` - Phase 2 single insurer mode
- `_execute_category_run()` - Phase 3 category batch mode

**CONCLUSION**: Pipeline is 100% Factiva. No branching exists. The two legacy functions remain but are unreachable from API endpoints.

---

## 4. Admin Routes: Source CRUD Operations

### Research Finding: NO SOURCE MANAGEMENT ROUTES EXIST

**File**: `app/routers/admin.py` (1,300+ lines)

**Search Results**:
- Searched for "sources" (case-insensitive): Only 1 match on line 1145
- Match is `"max_concurrent_sources": settings.max_concurrent_sources` (settings display)
- **NO routes** for source CRUD operations
- **NO template** for source management

**Admin Routes Present** (from sidebar in `app/templates/admin/base.html`):
1. Dashboard (`/admin/dashboard`)
2. Insurers (`/admin/insurers`)
3. Import (`/admin/import`)
4. Recipients (`/admin/recipients`)
5. Schedules (`/admin/schedules`)
6. Settings (`/admin/settings`)
7. Equity Tickers (`/admin/equity`)
8. Factiva Config (`/admin/factiva`)
9. Enterprise Config (`/admin/enterprise_config`)

**CONCLUSION**: Source management was likely never implemented or was already removed. No cleanup needed in admin routes.

---

## 5. APIFY_TOKEN References

### `.env.example` (Line 50-53)
```bash
# ============================================
# Apify Configuration (for web scraping)
# ============================================
# Your Apify API token from https://console.apify.com/settings/integrations
APIFY_TOKEN=your-apify-token-here
```

### `app/config.py` (Line 42-43)
```python
# Apify (for web scraping)
apify_token: str = ""
```

**Helper Method** (Lines 173-175):
```python
def is_apify_configured(self) -> bool:
    """Check if Apify is configured."""
    return bool(self.apify_token)
```

**CONCLUSION**: Simple removals - delete from .env.example, config.py class, and helper method.

---

## 6. Codebase-Wide Apify References

### Search: `apify` (case-insensitive)

**Code Files** (11 files):
1. `app/routers/admin.py` - Settings display only (max_concurrent_sources)
2. `app/collectors/factiva.py` - Comment/documentation only
3. `app/templates/admin/dashboard.html` - No matches (false positive)
4. `app/main.py` - No direct matches
5. `app/models/api_event.py` - No matches (false positive)
6. `app/config.py` - APIFY_TOKEN field + helper method
7. `app/services/sources/google_news.py` - Uses Apify client
8. `app/services/sources/cqcs.py` - Uses Apify client
9. `app/services/sources/valor.py` - Uses Apify client
10. `app/templates/admin/settings.html` - No matches (false positive)
11. `app/services/scraper.py` - ApifyScraperService class, GOOGLE_NEWS_ACTOR constant

**Documentation Files** (54 .md files):
- Planning docs, research docs, phase summaries referencing Apify migration
- `docs/USER_GUIDE.md` - Note about v1.0 → v1.1 Apify → Factiva transition
- `docs/BACKLOG.md` - Historical references

**CONCLUSION**: Code references limited to sources directory and config. Documentation is historical context only.

---

## 7. requirements.txt Dependencies

**File**: `C:\BrasilIntel\requirements.txt`

### Apify-Related Dependencies

**Line 20-21** (Phase 2 comment block):
```
# Phase 2 - Vertical Slice
# Web scraping
apify-client>=1.8.0
```

**Line 43** (Phase 3 comment block):
```
# Phase 3 - News Collection Scale
feedparser>=6.0.0
```

**Other Dependencies**:
- `aiohttp>=3.9.0` (Line 44) - Used by sources but also by FactivaCollector, so **DO NOT REMOVE**

**CONCLUSION**: Remove `apify-client>=1.8.0` and `feedparser>=6.0.0` only.

---

## 8. Admin Sidebar Navigation

**File**: `app/templates/admin/base.html` (Lines 217-247)

```html
<div class="sidebar">
    <nav class="nav flex-column">
        <a class="nav-link" href="{{ url_for('admin_dashboard') }}">
            <i class="bi bi-speedometer2"></i>Dashboard
        </a>
        <a class="nav-link" href="{{ url_for('admin_insurers') }}">
            <i class="bi bi-building"></i>Insurers
        </a>
        <a class="nav-link" href="{{ url_for('admin_import') }}">
            <i class="bi bi-upload"></i>Import
        </a>
        <a class="nav-link" href="{{ url_for('admin_recipients') }}">
            <i class="bi bi-people"></i>Recipients
        </a>
        <a class="nav-link" href="{{ url_for('admin_schedules') }}">
            <i class="bi bi-calendar-check"></i>Schedules
        </a>
        <a class="nav-link" href="{{ url_for('admin_settings') }}">
            <i class="bi bi-gear"></i>Settings
        </a>
        <a class="nav-link" href="{{ url_for('admin_equity') }}">
            <i class="bi bi-graph-up"></i>Equity Tickers
        </a>
        <a class="nav-link" href="{{ url_for('admin_factiva') }}">
            <i class="bi bi-newspaper"></i>Factiva Config
        </a>
        <a class="nav-link" href="{{ url_for('admin_enterprise_config') }}">
            <i class="bi bi-shield-lock"></i>Enterprise Config
        </a>
    </nav>
</div>
```

**CONCLUSION**: NO "Sources" link exists. No cleanup needed.

---

## 9. Test Files, Scripts, Documentation

### Test Files with Apify References

**No test files found** that directly test Apify sources. Test files focus on:
- `tests/test_batch_processor.py` - Tests batch processor (uses SourceRegistry)
- `tests/test_relevance_scorer.py` - Tests relevance scoring
- `tests/test_classifier.py` - Tests classification
- Other tests unrelated to scraping

### Scripts

**`scripts/test_factiva.py`**:
- **NO Apify references**
- Tests Factiva collection end-to-end
- Imports: FactivaCollector, ArticleDeduplicator
- **STATUS**: Keep as-is

### Documentation

**`docs/USER_GUIDE.md`** (Line 702):
```markdown
> **Note:** In v1.0, news was collected from 7 Apify-based sources (Google News, Valor Economico, InfoMoney, CQCS, ANS, Estadao, RSS). v1.1 replaced all sources with Factiva via MMC Core API. Legacy Apify source code remains in the codebase but is not used in the active pipeline.
```

**CONCLUSION**: Update USER_GUIDE.md to reflect removal completion.

---

## 10. Collector Service Intertwining

### Current Collector Architecture

**File**: `app/routers/runs.py`

**Active Pipeline**: `_execute_factiva_pipeline()` (Lines 189-361)

**Collection Logic** (Lines 210-220):
```python
# Collect articles from Factiva
collector = FactivaCollector()
if not collector.is_configured():
    raise HTTPException(
        status_code=503,
        detail="MMC API key not configured — cannot collect from Factiva"
    )

logger.info(f"Collecting articles from Factiva for category {request.category}...")
articles = collector.collect(query_params, run_id=run.id)
logger.info(f"Factiva returned {len(articles)} articles")
```

**NO Apify logic exists** in active pipeline. FactivaCollector is standalone.

**CONCLUSION**: Collector is cleanly separated. No intertwining. Apify code is dead code.

---

## Summary: Files to Delete/Modify

### Files to DELETE (9 total)

**Source Classes** (8 files):
1. `app/services/sources/__init__.py`
2. `app/services/sources/base.py`
3. `app/services/sources/google_news.py`
4. `app/services/sources/valor.py`
5. `app/services/sources/cqcs.py`
6. `app/services/sources/infomoney.py`
7. `app/services/sources/estadao.py`
8. `app/services/sources/ans.py`
9. `app/services/sources/rss_source.py`

**Action**: Delete entire `app/services/sources/` directory

### Files to MODIFY (6 total)

1. **`app/services/scraper.py`**
   - Delete ApifyScraperService class (Lines 30-144)
   - Delete ScraperService class (Lines 147-346)
   - Delete entire file OR leave comment explaining removal

2. **`app/services/__init__.py`**
   - Remove `from app.services.scraper import ApifyScraperService`

3. **`app/services/batch_processor.py`**
   - Remove imports: `SourceRegistry, ScrapedNewsItem, NewsSource`
   - Delete entire file OR leave comment (unused since Factiva)

4. **`requirements.txt`**
   - Remove `apify-client>=1.8.0`
   - Remove `feedparser>=6.0.0`

5. **`app/config.py`**
   - Remove `apify_token: str = ""` field (Line 43)
   - Remove `is_apify_configured()` method (Lines 173-175)

6. **`.env.example`**
   - Remove Apify Configuration section (Lines 50-53)
   - Add/update MMC Core API section (already exists Lines 104-124)

### Files to UPDATE (Documentation)

1. **`docs/USER_GUIDE.md`** (Line 702)
   - Update note: "Legacy Apify source code remains in the codebase" → "Apify infrastructure removed in v1.1"

2. **`README.md`** (if applicable)
   - Remove Apify references from architecture/features sections

---

## Validation Checkpoints

Based on CONTEXT.md decisions, validation should include:

### Boot Check Required
- Application must start without errors after cleanup
- No import errors from removed modules
- FactivaCollector pipeline must still function

### Test Coverage
- Add cleanup validation to `scripts/test_factiva.py`:
  - Assert `app/services/sources/` directory does not exist
  - Assert `apify-client` not in `pip list` output
  - Assert `feedparser` not in `pip list` output
  - Assert no `from app.services.scraper import ApifyScraperService` in codebase

### Database Integrity
- Existing NewsItem records with `source_name` from Apify sources remain untouched
- Existing Source model records remain untouched (no Source model found in research)

---

## Questions for Planner

1. **Delete vs Comment**: Should we delete `app/services/scraper.py` entirely or leave a comment explaining removal?
2. **Delete vs Comment**: Should we delete `app/services/batch_processor.py` entirely or leave it (even though unused)?
3. **Legacy Routes**: Should we delete `_execute_single_insurer_run()` and `_execute_category_run()` from runs.py?
4. **Documentation Sweep**: Should we update all planning docs to mark Apify cleanup as complete?

---

## Next Steps for Planner

1. Create two plans:
   - **14-01**: Remove source classes, dependencies, config
   - **14-02**: Scrub pipeline code, update documentation, add validation tests

2. Consider validation strategy:
   - Pre-cleanup snapshot of working state
   - Post-cleanup boot verification
   - Automated test for cleanup completeness

3. Determine rollback strategy if cleanup breaks pipeline
   - Git branch/commit structure
   - Emergency revert process

---

**End of Research** | Ready for Planning Phase
