---
phase: 14-apify-cleanup
plan: 02
subsystem: pipeline-infrastructure
tags: [cleanup, config, admin-ui, documentation]

requires:
  - "14-01: Apify file deletion"
provides:
  - "Complete Apify removal from config, pipeline, and UI"
  - "Clean environment template and documentation"
  - "Zero Apify remnants in application code"
affects:
  - "None - Phase 14 concludes with complete cleanup"

tech-stack:
  added: []
  removed:
    - "apify_token config field"
    - "scraping batch settings (batch_size, scrape_timeout, etc.)"
    - "relevance scoring config (use_ai_relevance_scoring, etc.)"
    - "_execute_single_insurer_run() function"
    - "_execute_category_run() function"
    - "is_apify_configured() method"
    - "get_source_timeout() method"
    - "Apify admin UI elements"
  patterns: []

key-files:
  created: []
  modified:
    - path: "app/config.py"
      purpose: "Remove Apify and scraping config fields"
    - path: "app/routers/runs.py"
      purpose: "Remove legacy Apify pipeline functions"
    - path: "app/routers/admin.py"
      purpose: "Remove Apify health check and scraping config"
    - path: "app/templates/admin/settings.html"
      purpose: "Remove scraping config and relevance scoring UI"
    - path: "app/templates/admin/dashboard.html"
      purpose: "Remove Apify service status display"
    - path: ".env.example"
      purpose: "Remove APIFY_TOKEN section"
    - path: "docs/USER_GUIDE.md"
      purpose: "Update to reflect complete Apify removal"
    - path: "app/main.py"
      purpose: "Remove Apify from health check"
    - path: "app/collectors/factiva.py"
      purpose: "Clean Apify fallback comments"
    - path: "app/models/api_event.py"
      purpose: "Update NEWS_FALLBACK description"

decisions: []

metrics:
  duration: "13 min"
  completed: "2026-02-20"
---

# Phase 14 Plan 02: Config & UI Cleanup Summary

**Removed all remaining Apify references from config, pipeline functions, admin UI, environment template, and documentation — completing the Apify cleanup phase**

## Accomplishments

**Configuration Cleanup:**
- Removed `apify_token` field from Settings class
- Removed `is_apify_configured()` method
- Removed scraping batch processing settings (batch_size, batch_delay_seconds, max_concurrent_sources, scrape_timeout_seconds, scrape_max_results)
- Removed source-specific timeout settings (source_timeout_valor, source_timeout_cqcs)
- Removed `get_source_timeout()` method
- Removed relevance scoring settings (use_ai_relevance_scoring, relevance_keyword_threshold, relevance_ai_batch_size) — tied to deleted RelevanceScorer service

**Pipeline Cleanup:**
- Deleted `_execute_single_insurer_run()` function (Phase 2 legacy Apify code)
- Deleted `_execute_category_run()` function (Phase 3 legacy Apify code)
- Updated module docstring to reflect Factiva-only pipeline
- Preserved all active Factiva pipeline code and MMC Core API configuration

**Admin UI Cleanup:**
- Removed scraping configuration section from settings page
- Removed Apify health check from dashboard
- Removed Apify from API keys display
- Removed relevance scoring settings from AI configuration section
- Removed Apify service status badge from dashboard
- Cleaned environment variable reference table

**Documentation & Environment:**
- Removed APIFY_TOKEN section from .env.example
- Updated USER_GUIDE.md note to reflect complete Apify removal
- Cleaned Apify fallback comments from factiva.py
- Updated NEWS_FALLBACK description in api_event.py
- Removed Apify from main.py health endpoint

## Validation

**Boot Check:**
```bash
python -c "from app.main import app; print('OK')"
# Output: OK
```

**Remnant Scan:**
```bash
grep -ri "apify\|ScraperService\|BatchProcessor\|SourceRegistry\|RelevanceScorer" app/ --include="*.py" --include="*.html"
# Output: No matches
```

**Phase Success Criteria:**
- ✅ CLNP-01: app/services/sources/ directory removed (14-01)
- ✅ CLNP-02: apify-client and feedparser removed from requirements.txt (14-01)
- ✅ CLNP-03: Only Factiva pipeline remains in runs.py
- ✅ CLNP-04: No APIFY_TOKEN in .env.example, MMC Core API section preserved
- ✅ FastAPI app boots successfully
- ✅ Zero Apify remnants in application code

## Files Modified

| File | Lines Removed | Changes |
|------|--------------|---------|
| app/config.py | 33 | Removed apify_token, scraping settings, relevance scoring, is_apify_configured(), get_source_timeout() |
| app/routers/runs.py | 210 | Removed _execute_single_insurer_run(), _execute_category_run(), updated docstring |
| app/routers/admin.py | 19 | Removed scraping_config, relevance_config, Apify health check |
| app/templates/admin/settings.html | 44 | Removed scraping config card, relevance scoring display, Apify references |
| app/templates/admin/dashboard.html | 2 | Removed Apify service badge |
| .env.example | 5 | Removed Apify configuration section |
| docs/USER_GUIDE.md | 1 | Updated note to reflect complete removal |
| app/main.py | 3 | Removed Apify from health check |
| app/collectors/factiva.py | 2 | Cleaned Apify fallback comments |
| app/models/api_event.py | 1 | Updated NEWS_FALLBACK description |

**Total removed:** ~320 lines of legacy Apify infrastructure

## Commits

1. **e957ab0** - `refactor(14-02): remove Apify config and legacy pipeline functions`
   - config.py: Removed apify_token, scraping settings, relevance scoring config
   - runs.py: Deleted _execute_single_insurer_run() and _execute_category_run()

2. **268abd3** - `docs(14-02): clean admin UI and update documentation for Apify removal`
   - admin.py/settings.html: Removed scraping config and Apify health check
   - .env.example: Removed APIFY_TOKEN section
   - USER_GUIDE.md: Updated to reflect complete Apify removal
   - Code comments: Cleaned all Apify fallback references

## Next Phase Readiness

**Phase 14 Complete:**
- All Apify source files deleted (14-01: 14 files, 2,584 lines)
- All Apify config and UI references removed (14-02: 10 files, ~320 lines)
- Total cleanup: **24 files removed/modified, ~2,900 lines deleted**
- BrasilIntel now runs exclusively on Factiva via MMC Core API

**Production Readiness:**
- ✅ App boots successfully without any Apify dependencies
- ✅ Zero import errors or dead code references
- ✅ Admin dashboard reflects Factiva-only architecture
- ✅ Environment template guides users to MMC Core API credentials
- ✅ Documentation accurately reflects current pipeline

**v1.1 Enterprise API Integration: COMPLETE**
- Phase 9: Enterprise API Foundation ✅
- Phase 10: Factiva News Collection ✅
- Phase 11: Insurer Matching Pipeline ✅
- Phase 12: Equity Price Enrichment ✅
- Phase 13: Admin Dashboard Extensions ✅
- Phase 14: Apify Cleanup ✅

BrasilIntel is now a fully enterprise-integrated intelligence platform with no legacy Apify infrastructure.
