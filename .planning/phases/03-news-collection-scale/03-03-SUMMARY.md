---
phase: 03-news-collection-scale
plan: 03
subsystem: news-sources
tags: [apify, web-crawler, valor, cqcs, batch-processing]

dependency-graph:
  requires: ["03-01"]
  provides: ["ValorSource", "CQCSSource", "batch_config"]
  affects: ["03-04", "03-06"]

tech-stack:
  added: []  # Uses existing apify-client
  patterns: ["website-content-crawler", "playwright-firefox"]

file-tracking:
  key-files:
    created:
      - app/services/sources/valor.py
      - app/services/sources/cqcs.py
    modified:
      - app/config.py
      - app/services/sources/__init__.py

decisions:
  - id: valor-cheerio
    choice: "cheerio crawler for Valor"
    reason: "Faster HTML-only parsing, no anti-bot protection needed"
  - id: cqcs-playwright
    choice: "playwright:firefox for CQCS"
    reason: "Browser-based rendering for anti-bot compatibility"
  - id: cqcs-concurrency
    choice: "max_concurrency=2 for CQCS"
    reason: "Avoid rate limiting on CQCS portal"
  - id: over-fetch-filter
    choice: "Over-fetch then filter results"
    reason: "Website crawlers return mixed content, need post-filtering"

metrics:
  duration: ~4 minutes
  completed: 2026-02-04
---

# Phase 3 Plan 3: Crawler Sources Summary

Website crawler sources for Valor Economico and CQCS using Apify Website Content Crawler, plus batch processing configuration.

## One-Liner

Apify website crawlers for Valor (cheerio) and CQCS (playwright:firefox) with configurable batch processing settings.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend configuration | 33acc1f | app/config.py |
| 2 | Valor Economico source | 74da41f | app/services/sources/valor.py |
| 3 | CQCS source | 4702086 | app/services/sources/cqcs.py, __init__.py |

## Key Deliverables

### 1. Batch Processing Configuration

Extended `app/config.py` with NEWS-07 batch processing settings:

```python
batch_size: int = 30  # Insurers per batch (30-50 recommended)
batch_delay_seconds: float = 2.0  # Delay between batches
max_concurrent_sources: int = 3  # Max parallel sources
scrape_timeout_seconds: int = 60  # Default timeout
scrape_max_results: int = 10  # Results per insurer per source
source_timeout_valor: int = 120  # Valor needs longer
source_timeout_cqcs: int = 120  # CQCS needs longer
```

Plus `get_source_timeout(source_name)` helper for source-specific timeouts.

### 2. Valor Economico Source (NEWS-02)

```python
class ValorSource(NewsSource):
    SOURCE_NAME = "valor"
    CRAWLER_ACTOR_ID = "apify/website-content-crawler"
```

Features:
- Uses `cheerio` crawler for fast HTML parsing
- Filters non-article pages (video, podcast, author)
- Extracts dates from URL patterns `/YYYY/MM/DD/`
- Configurable timeout (default 120s)
- Auto-registers with SourceRegistry

### 3. CQCS Source (NEWS-04)

```python
class CQCSSource(NewsSource):
    SOURCE_NAME = "cqcs"
    CRAWLER_ACTOR_ID = "apify/website-content-crawler"
```

Features:
- Uses `playwright:firefox` for anti-bot compatibility
- Lower concurrency (2) to avoid rate limiting
- 3 retries for resilience
- Filters by query keywords after crawling
- Auto-registers with SourceRegistry

### 4. All 6 Sources Now Registered

```
Registered sources: ['google_news', 'infomoney', 'estadao', 'ans', 'valor', 'cqcs']
```

## Verification Results

```
batch_size: 30
batch_delay_seconds: 2.0
max_concurrent_sources: 3
source_timeout_valor: 120
source_timeout_cqcs: 120
get_source_timeout(valor): 120
get_source_timeout(unknown): 60  # Falls back to default

Registered sources: ['google_news', 'infomoney', 'estadao', 'ans', 'valor', 'cqcs']
```

## Deviations from Plan

None - plan executed exactly as written.

## Architecture Notes

### Crawler Type Selection

| Source | Crawler Type | Reason |
|--------|-------------|--------|
| Valor | cheerio | No anti-bot, faster HTML parsing |
| CQCS | playwright:firefox | Anti-bot protection (403 errors on direct access) |

### Over-fetch Strategy

Website crawlers return mixed content (listing pages, articles, etc.). Both sources over-fetch (3-5x max_results) then filter:

1. ValorSource: Excludes `/video/`, `/podcast/`, `/autor/` patterns
2. CQCSSource: Filters by query keywords in title/description/URL

### Timeout Strategy

Website crawlers need longer timeouts than API-based sources:
- Default sources: 60 seconds
- Valor/CQCS: 120 seconds (configurable)

## Next Phase Readiness

Ready for:
- **03-04 Batch Processor**: Has batch_size, batch_delay_seconds, max_concurrent_sources
- **03-06 Integration**: All 6 sources available via SourceRegistry

## Files Changed

```
app/config.py                         # +27 lines (batch config)
app/services/sources/valor.py         # +246 lines (new file)
app/services/sources/cqcs.py          # +245 lines (new file)
app/services/sources/__init__.py      # +4 lines (exports)
```
