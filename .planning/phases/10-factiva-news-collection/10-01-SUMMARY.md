---
phase: 10-factiva-news-collection
plan: 01
subsystem: news-collection
tags: [factiva, dow-jones, httpx, tenacity, structlog, api-client]

# Dependency graph
requires:
  - phase: 09-enterprise-api-foundation
    provides: Settings config guards (is_mmc_api_key_configured), ApiEvent model, FactivaConfig ORM
provides:
  - FactivaCollector API client with search, body fetch, normalization, and event recording
  - FactivaConfig seeded with Brazilian insurance industry codes and Portuguese keywords
  - 48-hour date window for cross-run deduplication overlap
affects: [10-02-pipeline-integration, 10-03-admin-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "X-Api-Key only authentication (no JWT for news endpoint)"
    - "48-hour date window with dedup handling cross-run overlap"
    - "Graceful fallback to snippet when article body fetch fails (4xx errors)"
    - "ApiEvent recording for all collection outcomes (success/failure)"
    - "Pagination follow for pageSize100 links (up to 100 articles per run)"

key-files:
  created:
    - app/collectors/__init__.py
    - app/collectors/factiva.py
    - scripts/seed_factiva_config.py
  modified: []

key-decisions:
  - "48-hour date window (not 24-hour) for cross-run overlap handling"
  - "source_url field name (BrasilIntel NewsItem schema, not MDInsights 'url')"
  - "No collector_source field (MDInsights-specific, not in BrasilIntel)"
  - "Brazilian insurance industry codes: i82, i8200, i82001, i82002, i82003"
  - "Portuguese insurance keywords: 9 terms covering insurance, insurer, reinsurance, health, pension, claims, policy, broker"
  - "page_size=50 (balance between coverage and API cost, max 100)"

patterns-established:
  - "FactivaCollector pattern: _search, _search_by_url, _fetch_article, _normalize_article, _record_event"
  - "Retry decorator on all HTTP methods (2 attempts, exponential backoff 2-10s, timeout/connect errors only)"
  - "Hard cap MAX_ARTICLES=100 to avoid excessive API calls per run"
  - "Idempotent seed scripts: update if exists, insert if not"

# Metrics
duration: 15min
completed: 2026-02-19
---

# Phase 10 Plan 01: Factiva API Client Summary

**FactivaCollector ported from MDInsights with 48-hour date window, BrasilIntel NewsItem schema normalization, and Brazilian insurance configuration seeded**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-19T20:42:44Z
- **Completed:** 2026-02-19T20:57:44Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- FactivaCollector class with all 7 methods (collect, _build_headers, _search, _search_by_url, _fetch_article, _normalize_article, _record_event)
- 48-hour date window for cross-run deduplication overlap (timedelta(days=2))
- Normalization to BrasilIntel NewsItem schema (source_url, not url; no collector_source)
- ApiEvent recording for all NEWS_FETCH operations (success/failure, article counts)
- Brazilian insurance industry configuration seeded (5 industry codes, 9 Portuguese keywords, page_size=50)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create FactivaCollector class** - `66f9d3e` (feat)
2. **Task 2: Create FactivaConfig seed script** - `024841e` (feat)

## Files Created/Modified
- `app/collectors/__init__.py` - Package init exporting FactivaCollector
- `app/collectors/factiva.py` - Complete Factiva API client (456 lines, 7 methods, X-Api-Key auth only)
- `scripts/seed_factiva_config.py` - Idempotent FactivaConfig seeder with Brazilian defaults

## Decisions Made

**1. 48-hour date window (not 24-hour)**
- MDInsights used 1-day, BrasilIntel uses 2-day for cross-run overlap handling
- Rationale: Deduplicator (10-02) needs overlap to catch articles appearing late in feed

**2. source_url field name (not url)**
- MDInsights NewsArticle model uses 'url', BrasilIntel NewsItem uses 'source_url'
- Normalization adapted to match BrasilIntel schema

**3. No collector_source field**
- MDInsights has collector_source for pipeline analytics
- BrasilIntel NewsItem doesn't have this field, omitted from normalization

**4. Brazilian insurance industry codes**
- i82 = Insurance (broad)
- i8200 = Full Line Insurance
- i82001 = Life Insurance
- i82002 = Property and Casualty
- i82003 = Reinsurance
- Rationale: Batch query for entire insurance sector, post-hoc AI matching to specific insurers (Phase 11)

**5. Portuguese insurance keywords**
- seguro, seguradora, resseguro, saude suplementar, plano de saude, previdencia, sinistro, apolice, corretora de seguros
- Rationale: Broad Portuguese insurance terms to maximize coverage, AI classifier (Phase 11) will filter for relevance

**6. page_size=50 (default)**
- Balance between coverage (higher = more articles) and API cost (Factiva charges per article)
- Hard cap MAX_ARTICLES=100 prevents runaway costs
- pageSize100 pagination link followed automatically if available

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**ACTION REQUIRED before Phase 10-02:** MMC API credentials must be added to .env for FactivaCollector to work:

```bash
# .env
MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
MMC_API_KEY=<your-staging-api-key>
```

Verification:
```bash
python -c "from app.collectors.factiva import FactivaCollector; c = FactivaCollector(); print('Configured:', c.is_configured())"
# Should print: Configured: True
```

No manual testing possible until credentials are added. Phase 10-02 pipeline integration will test end-to-end.

## Next Phase Readiness

**Ready for Phase 10-02 (Pipeline Integration):**
- FactivaCollector can be imported and instantiated
- is_configured() guards pipeline against missing credentials
- collect() accepts query_params dict and run_id (pipeline context)
- Returns normalized article dicts ready for ArticleDeduplicator (10-02)
- ApiEvent recording wired for dashboard visibility

**Blocker:**
- MMC API credentials MUST be added to .env before 10-02 pipeline testing
- Without credentials, is_configured() returns False and pipeline skips Factiva (falls back to Apify)

**Next steps:**
1. Add staging MMC credentials to .env
2. Run `python scripts/seed_factiva_config.py` to ensure Brazilian defaults are loaded
3. Proceed to Phase 10-02 for pipeline integration and end-to-end testing

---
*Phase: 10-factiva-news-collection*
*Completed: 2026-02-19*
