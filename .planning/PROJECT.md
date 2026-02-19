# BrasilIntel

## What This Is

Automated competitive intelligence system for Marsh Brasil that monitors 897 Brazilian insurers across Health, Dental, and Group Life categories. The system scrapes news from 6 sources (Google News, Valor Economico, InfoMoney, CQCS, ANS, Estadao), uses Azure OpenAI to summarize and classify insurer status, and generates polished daily HTML reports with PDF attachments for senior management — replacing manual web searches and report compilation.

## Core Value

Senior management at Marsh Brasil receives actionable, professionally-formatted intelligence reports on their monitored insurers daily, with zero manual effort.

## Current Milestone: v1.1 Enterprise API Integration

**Goal:** Replace Apify web scraping with Factiva/Dow Jones as sole news source, add inline equity price data, and switch to MMC Core API enterprise email delivery — porting the proven enterprise integration from MDInsights into BrasilIntel.

**Target features:**
- Factiva news collection via MMC Core API (replaces all 6 Apify sources)
- Equity price enrichment for tracked Brazilian insurance companies
- Enterprise email delivery via MMC Core API (with Graph API fallback)
- OAuth2 client credentials token management
- Admin UI for Factiva config, equity tickers, enterprise credentials, API health

## Current State

**Version:** v1.0 MVP (shipped 2026-02-05)
**Codebase:** 11,057 lines of Python across 57 files, 16 HTML templates
**Tech Stack:** Python 3.11, FastAPI, SQLite, Apify SDK, Azure OpenAI, Microsoft Graph, WeasyPrint, APScheduler, HTMX

## Requirements

### Validated

- DATA-01 through DATA-08 — v1.0 (insurer database with Excel import/export)
- NEWS-01 through NEWS-10 — v1.0 (6 news sources with batch processing and AI relevance scoring)
- CLASS-01 through CLASS-06 — v1.0 (Azure OpenAI classification with sentiment)
- REPT-01 through REPT-13 — v1.0 (professional Marsh-branded reports with archival)
- DELV-01 through DELV-08 — v1.0 (email delivery with PDF and critical alerts)
- SCHD-01 through SCHD-07 — v1.0 (APScheduler automation)
- ADMN-01 through ADMN-16 — v1.0 (complete admin dashboard; ADMN-10/11 read-only by design)
- DEPL-01 through DEPL-09 — v1.0 (Docker and Windows deployment)

### Active

- Factiva/Dow Jones as primary (and only) news source via MMC Core API
- Equity price data inline with news stories via MMC Core API
- Enterprise email delivery via MMC Core API (with Graph API fallback)
- OAuth2 client credentials token management for API authentication
- Admin dashboard: enterprise API health, credential config, Factiva query config, equity ticker mappings
- Remove Apify scraping infrastructure (6 sources, apify-client dependency)

### Out of Scope

- Real-time notifications — daily batch reports sufficient for use case
- Mobile app — web dashboard accessible from any device
- Multi-tenant / SaaS — single deployment for Marsh Brasil
- Custom report designer — templates are fixed to Marsh branding
- Historical trend analysis — focus on current news, not analytics (v2 candidate)
- Portuguese language UI — English admin interface acceptable
- Editable recipients via UI — environment variable configuration acceptable for v1

## Context

**Business Context:**
- Previous state: Manual web searches and report compilation by DDH team
- Current state: Automated daily intelligence with zero manual effort
- Users: Senior management at Marsh Brasil (5-10 recipients per category)
- Data source: DDH partner database of 897 insurers

**Technical Environment:**
- Corporate M365 Exchange Online (Graph API for email)
- Azure AD for authentication
- Azure OpenAI (corporate LLM deployment)
- Apify account for web scraping (being replaced by Factiva in v1.1)
- MMC Core API platform (Apigee) — staging credentials available (shared with MDInsights)
- Windows Server on AWS (production)
- Windows 11 (development)

**Sister Project:**
- MDInsights (v1.1 shipped) provides the enterprise API integration patterns being ported to BrasilIntel. Same tech stack, same MMC Core API credentials.

**Key Identifiers:**
- ANS Code: Brazilian regulatory registration number
- Market Master: Marsh global system code (216 of 897 insurers have this)

## Constraints

- **Tech Stack**: Python 3.11+, FastAPI, SQLite, Apify SDK, Azure OpenAI SDK, Microsoft Graph SDK
- **Corporate Auth**: Azure AD app registration for Graph API and Azure OpenAI access
- **Deployment**: Docker (local dev) and Windows Scheduled Task (production)
- **Branding**: Reports must match Marsh visual identity
- **Data Volume**: 897 insurers, ~15-30 min scrape time per category
- **Timezone**: All schedules in America/Sao_Paulo

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python over Node.js | Better Azure SDK support, stronger data processing | Good |
| FastAPI over Flask | Modern async support, automatic OpenAPI docs | Good |
| SQLite over PostgreSQL | Zero config, portable, sufficient for single deployment | Good |
| Windows Scheduled Task over Service | Simpler deployment, matches existing patterns | Good |
| Apify over direct scraping | Proven infrastructure, handles rate limiting | Good |
| 3 separate scheduled jobs | Staggered runs, independent failures | Good |
| HTMX over React/Vue | SPA-like UX without frontend build complexity | Good |
| HTTP Basic auth | Simple, sufficient for internal tool | Good |
| Read-only recipients | Env var config acceptable for MVP scope | Acceptable |
| WeasyPrint for PDF | Native Python, good CSS support | Good |

| Factiva over Apify for news | Enterprise Dow Jones feed more reliable than web scraping; proven in MDInsights | -- Pending |
| Copy and adapt from MDInsights | Port enterprise modules directly, adapt for Brazilian context | -- Pending |
| Industry codes + keywords for Factiva | Query by Brazilian insurance industry codes, not per-insurer | -- Pending |

---
*Last updated: 2026-02-19 after v1.1 milestone start*
