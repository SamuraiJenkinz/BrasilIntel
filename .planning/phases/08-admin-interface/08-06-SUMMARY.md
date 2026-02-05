---
phase: 08-admin-interface
plan: 06
subsystem: admin
tags: [settings, api-keys, security, configuration, admin]
dependency-graph:
  requires: ["08-01"]
  provides: "Settings page with masked API keys and configuration display"
  affects: []
tech-stack:
  added: []
  patterns: ["password input masking", "reveal toggle", "read-only configuration display"]
key-files:
  created:
    - app/templates/admin/settings.html
  modified:
    - app/routers/admin.py
decisions:
  - id: "settings-readonly"
    choice: "Read-only display with env var reference"
    rationale: "Configuration via .env file is more secure than web UI editing"
  - id: "mask-key-helper"
    choice: "mask_key() helper with configurable visible characters"
    rationale: "Different secrets need different visibility (endpoints vs API keys)"
  - id: "reveal-toggle"
    choice: "JavaScript toggle with show/hide text"
    rationale: "User can verify configuration without exposing secrets constantly"
metrics:
  duration: "~5 minutes"
  completed: "2026-02-05"
---

# Phase 08 Plan 06: Settings Page Summary

Settings page with company branding, scraping config, and masked API keys with reveal toggle

## What Was Built

### 1. Settings Page Endpoint (app/routers/admin.py)

**mask_key() helper function:**
- Masks API keys showing only last N characters
- Configurable reveal length (default 4 chars, 8-10 for longer values)
- Returns "(not configured)" for empty values
- Protects short values by masking entirely

**Settings endpoint enhancements:**
- Company branding section (ADMN-14): company_name, classification level
- Scraping configuration (ADMN-15): batch_size, delays, timeouts, limits
- API keys with masked and unmasked values (ADMN-16)
- Relevance configuration: AI scoring settings
- LLM summary toggle display

### 2. Settings Page Template (app/templates/admin/settings.html)

**Company Branding Section:**
- Company name from COMPANY_NAME env var
- Classification level badge (CONFIDENTIAL)
- Environment variable reference

**Scraping Configuration Section:**
- Batch size (insurers per batch)
- Batch delay (seconds between batches)
- Max concurrent sources
- Scrape timeout (seconds)
- Max results per insurer
- All env var references listed

**AI Configuration Section:**
- LLM Summary enabled/disabled badge
- AI Relevance Scoring enabled/disabled badge
- Keyword threshold value
- AI batch size value

**API Keys Section:**
- 8 API keys/secrets displayed:
  - Azure OpenAI Endpoint (10 chars visible)
  - Azure OpenAI API Key (4 chars visible)
  - Azure OpenAI Deployment (not sensitive - full display)
  - Microsoft Tenant ID (8 chars visible)
  - Microsoft Client ID (8 chars visible)
  - Microsoft Client Secret (4 chars visible)
  - Apify Token (4 chars visible)
  - Sender Email (full display - not sensitive)
- Configured/Not configured badge per key
- Password input with reveal toggle
- Show/Hide button with icons

**Environment Variable Reference:**
- Table of all configuration categories
- Variables listed per category
- Note about restart requirement

**JavaScript toggle function:**
- toggleKeyVisibility(btn, inputId)
- Switches input type between password/text
- Updates button text (Show/Hide)

## Requirements Fulfilled

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| ADMN-14 | Company branding settings | Branding section with company_name and classification_level |
| ADMN-15 | Scraping configuration | Full scraping config display with env var references |
| ADMN-16 | Masked API keys | Password inputs with reveal toggle for 8 API keys |

## Technical Decisions

1. **Read-only configuration display**: Settings are not editable via UI - must be changed in .env file. This is more secure than allowing web-based config changes.

2. **mask_key() helper**: Configurable masking allows showing more characters for endpoints (which are less sensitive) while hiding most of API keys.

3. **JavaScript reveal toggle**: Simple client-side toggle without server requests. Values are present in HTML but hidden by default via password input type.

4. **Env var reference table**: Quick reference helps operators know which variables to set for each feature.

## Files Changed

| File | Change Type | Lines | Description |
|------|-------------|-------|-------------|
| app/routers/admin.py | Modified | +85 | mask_key() helper, settings endpoint with full config data |
| app/templates/admin/settings.html | Created | 200 | Complete settings page with 4 sections |

## Deviations from Plan

None - plan executed exactly as written.

## Phase 8 Completion

This plan completes Phase 8 - Admin Interface. All 6 plans are now complete:

| Plan | Name | Status |
|------|------|--------|
| 08-01 | Admin Foundation | DONE |
| 08-02 | Dashboard Content | DONE |
| 08-03 | Insurers Management | DONE |
| 08-04 | Import Page | DONE |
| 08-05 | Recipients & Schedules | DONE |
| 08-06 | Settings Page | DONE |

**All ADMN requirements addressed:**
- ADMN-01 through ADMN-16 complete

## Verification Evidence

```
# Settings endpoint exists
python -c "from app.routers.admin import router; print('settings' in str([r.path for r in router.routes]))"
# Output: True

# Template file exists
ls -la app/templates/admin/settings.html
# Output: -rw-r--r-- 8484 Feb  4 21:54 settings.html
```

## Next Steps

**Phase 8 Complete - Project Complete**

All 36 plans across 8 phases have been executed. BrasilIntel is feature-complete with:
- Insurer data management with Excel import/export
- Multi-source news scraping (Google News, RSS, web crawlers)
- AI-powered classification and relevance scoring
- Professional Marsh-branded reports with PDF generation
- Critical alert immediate notifications
- Scheduled automated runs
- Complete admin interface for operations
