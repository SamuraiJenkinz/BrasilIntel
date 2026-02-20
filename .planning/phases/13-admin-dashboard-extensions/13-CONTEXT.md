# Phase 13: Admin Dashboard Extensions - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend the existing Bootstrap 5 + HTMX admin dashboard with enterprise API health visibility, credential/query configuration pages, and Factiva source badges on article listings. No new data collection, no new pipeline logic, no email changes. Dashboard-only.

</domain>

<decisions>
## Implementation Decisions

### Health Panel Layout
- Summary widget on dashboard home page (traffic light dots) + dedicated health detail page in sidebar
- Three services tracked: Auth (TokenManager), Factiva (FactivaCollector), Equity (EquityPriceClient)
- Traffic light dots (green/yellow/red) next to each service name — minimal and scannable
- Default view shows cached status from api_events table (last known state) — fast page load
- "Check Now" button triggers live API health check and updates status inline (HTMX partial)
- Detailed health page shows timestamps of last successful and last failed request per service

### Credential Management
- "Test Connection" button on settings page — validates saved credentials against live API, shows success/error inline
- Immediate save to persistent storage — next pipeline run picks up new credentials automatically

### Claude's Discretion
- Whether DB overrides .env or another config approach — pick best fit for existing config.py pattern
- Whether to mask saved credentials (show last 4 chars) or show full values — balance security vs usability for internal tool
- Whether credentials and Factiva config live on one sectioned page or separate sidebar pages — match existing admin nav patterns

### Factiva Query Editor
- Industry codes and keywords: Claude decides UI format (chips, comma-separated, textarea) — match existing admin patterns
- Date range: preset dropdown options (Last 24h, Last 48h, Last 7d) — matches pipeline's current 48h default
- Changes take effect immediately on save — next pipeline run reads fresh config from DB, no restart needed

### Article Source Badges
- Colored pill badges (like GitHub labels) next to article title in listings
- Factiva articles get a badge; legacy articles also get badges showing their original source name
- Source filter dropdown above article list — All / Factiva / legacy source names
- Badge color scheme: Claude decides, but must ensure text is clearly visible against any background color
- Filter uses HTMX partial update for seamless experience

</decisions>

<specifics>
## Specific Ideas

- Health panel should be the first thing admin sees on dashboard home — operational awareness at a glance
- Source badges should look like GitHub issue labels — colored pills with readable text
- Date range presets should include the current 48h default as an option so existing behavior is preserved
- "Check Now" button gives admin confidence that credentials are working without waiting for next scheduled run

</specifics>

<deferred>
## Deferred Ideas

- Azure OpenAI health tracking — could be added to health panel later but out of scope for Phase 13
- Sentinel insurer filtering/hiding in admin — noted in STATE.md concerns, separate feature

</deferred>

---

*Phase: 13-admin-dashboard-extensions*
*Context gathered: 2026-02-19*
