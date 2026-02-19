# Phase 9: Enterprise API Foundation - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

The system can authenticate with the MMC Core API platform and all API activity is observable through a persistent event log. This phase creates the database tables (api_events, FactivaConfig, EquityTicker), the OAuth2 token manager, and the config expansion that Phases 10-14 all depend on.

</domain>

<decisions>
## Implementation Decisions

### Port-from-MDInsights Strategy
- **Copy and adapt** from MDInsights — start from the working MDInsights code, change only what's domain-specific (insurer names, B3 tickers, Portuguese keywords)
- MDInsights modules to port for Phase 9:
  - `app/auth/token_manager.py` → TokenManager (OAuth2 client credentials, proactive refresh, event logging)
  - `app/models/api_event.py` → ApiEvent model + full ApiEventType enum (all 9 event types)
  - `app/models/factiva_config.py` → FactivaConfig model (single-row admin-configurable query params)
  - `app/models/equity_ticker.py` → EquityTicker model (adapted for BrasilIntel's insurer/B3 domain)
  - `app/config.py` additions → MMC credential settings (Pydantic Settings fields)
- **NOT ported in Phase 9** (later phases): FactivaCollector, EquityPriceClient, EnterpriseEmailClient

### Event Types — All 9 Upfront
- Create the full ApiEventType enum in Phase 9 migration, even though Phases 10-13 aren't built yet
- Event types: TOKEN_ACQUIRED, TOKEN_REFRESHED, TOKEN_FAILED, NEWS_FETCH, NEWS_FALLBACK, EQUITY_FETCH, EQUITY_FALLBACK, EMAIL_SENT, EMAIL_FALLBACK
- Avoids per-phase enum migrations; matches MDInsights exactly

### Credential Storage
- **Env vars now, DB page later** — Phase 9 reads MMC credentials from .env via Pydantic Settings (MMC_API_BASE_URL, MMC_API_CLIENT_ID, MMC_API_CLIENT_SECRET, MMC_API_KEY)
- Phase 14 later adds the admin credentials settings page with DB persistence
- Same progression as MDInsights

### FactivaConfig Defaults
- Use identical defaults to MDInsights: industry codes `i82,i832`, keywords `insurance reinsurance`
- Admin can adjust through Phase 14 UI later
- No need for Portuguese-specific defaults at migration time

### Validation Script
- Include a `scripts/test_auth.py` script (ported from MDInsights) to confirm credentials work end-to-end
- Proves the auth flow before Phase 10 depends on it
- Shared staging credentials with MDInsights (same Apigee host) — should already work

### Claude's Discretion
- **Module layout** — whether TokenManager lives in `app/auth/` (like MDInsights) or `app/services/auth.py` (flat, like current BrasilIntel). Pick what's easiest to maintain.
- **Ticker mapping key** — whether EquityTicker uses insurer_id FK (clean, enforced at DB level) or entity_name string match (like MDInsights). Pick based on BrasilIntel's data model and admin CRUD simplicity.
- **Retry approach** — whether to keep tenacity decorators from MDInsights or adapt to BrasilIntel's existing @retry patterns. Pick whichever is more robust.

</decisions>

<specifics>
## Specific Ideas

- MDInsights's `_record_event()` pattern is identical across TokenManager, EnterpriseEmailClient, FactivaCollector, and EquityPriceClient — each opens its own DB session so event recording never interferes with the caller's flow. Port this pattern consistently.
- MDInsights's TokenManager uses 5-minute refresh margin (`REFRESH_MARGIN_SECONDS = 300`) — keep the same value.
- The `test_auth.py` script should exercise both initial token acquisition and force_refresh cycle.
- BrasilIntel shares the same Apigee staging host as MDInsights — credentials should work without re-provisioning.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-enterprise-api-foundation*
*Context gathered: 2026-02-19*
