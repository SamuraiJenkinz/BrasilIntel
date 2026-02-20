---
phase: 12-equity-price-enrichment
plan: 01
subsystem: pipeline-enrichment
tags: [equity-prices, mmc-api, b3-exchange, data-enrichment]
requires:
  - phase: 09
    plan: 02
    artifact: EquityTicker model and ApiEvent.EQUITY_FETCH type
  - phase: 11
    plan: 03
    artifact: Factiva pipeline with insurer matching
provides:
  - artifact: EquityPriceClient service
    path: app/services/equity_client.py
    capability: Fetch B3 equity prices from MMC Core API
  - artifact: Pipeline equity enrichment
    path: app/routers/runs.py
    capability: Attach price data to insurers with ticker mappings
affects:
  - phase: 12
    plan: 02
    reason: Equity data now available for admin dashboard display
  - phase: 12
    plan: 03
    reason: Equity data ready for integration into report templates
tech-stack:
  added:
    - httpx (HTTP client with retry support)
    - tenacity (retry decorator for resilient API calls)
  patterns:
    - Direct port from MDInsights with minimal adaptation
    - Per-run caching to avoid duplicate ticker lookups
    - Graceful degradation when MMC API unconfigured
    - ApiEvent logging for all equity fetch outcomes
key-files:
  created:
    - app/services/equity_client.py
  modified:
    - app/routers/runs.py
decisions:
  - decision: Default exchange BVMF not NYSE
    rationale: BrasilIntel targets Brazilian insurers on B3 exchange
    impact: All equity lookups default to Brazilian market unless explicitly overridden
    phase: 12-01
  - decision: Direct port pattern from MDInsights
    rationale: EquityPriceClient proven stable in production MDInsights since Phase 11
    impact: Zero new logic — only docstrings and default exchange changed
    phase: 12-01
  - decision: Per-run ticker caching
    rationale: Same insurer may appear in multiple NewsItems per run
    impact: Prevents duplicate API calls for same ticker within a pipeline run
    phase: 12-01
  - decision: Graceful degradation for unconfigured MMC API
    rationale: Dev environments won't have staging credentials
    impact: Pipeline continues normally, equity enrichment returns empty dict
    phase: 12-01
  - decision: equity_data threaded through to reporter
    rationale: Phase 12-03 will render equity prices in report templates
    impact: Reporter receives equity_data now, will use in next plan
    phase: 12-01
metrics:
  duration: 24 minutes
  completed: 2026-02-20
---

# Phase 12 Plan 01: Equity Price Enrichment Infrastructure

**One-liner:** Port EquityPriceClient from MDInsights and integrate equity price enrichment into BrasilIntel Factiva pipeline with B3 exchange default

## Objective

Establish the infrastructure for real-time equity price data enrichment during pipeline runs, porting the proven EquityPriceClient from MDInsights and integrating it into the BrasilIntel Factiva batch collection workflow.

## Execution Summary

Successfully ported EquityPriceClient from MDInsights and integrated equity enrichment as a new pipeline step between classification and report generation. The enrichment matches insurer names against enabled EquityTicker mappings and fetches current B3 prices via the MMC Core API, with per-run caching to prevent duplicate lookups.

## Tasks Completed

### Task 1: Port EquityPriceClient from MDInsights
**Status:** ✅ Complete
**Commit:** ddc7711
**Files:** app/services/equity_client.py (created, 283 lines)

Created app/services/equity_client.py by porting the complete EquityPriceClient class from C:\BrasilIntel\mdinsights\app\collectors\equity.py with these adaptations:

**Ported patterns (unchanged):**
- httpx HTTP client with tenacity retry (2 attempts, exponential backoff)
- X-Api-Key header authentication via get_settings()
- Response field name fallbacks (price/lastPrice/last, change/priceChange/netChange, changePct/percentChange/pctChange)
- _record_event() with isolated SessionLocal for ApiEvent logging
- Returns None on any failure, never raises exceptions
- is_configured() guard checking base_url and api_key presence

**Adaptations:**
- Docstrings updated: "MDInsights" → "BrasilIntel", phase references to Phase 12
- Default exchange changed from "NYSE" to "BVMF" (Brazilian B3 exchange)
- Usage examples updated to show Brazilian tickers (BBSE3, PSSA3)

**Import verification:** ✅ `python -c "from app.services.equity_client import EquityPriceClient; print('OK')"` succeeded

### Task 2: Integrate equity enrichment into Factiva pipeline
**Status:** ✅ Complete
**Commit:** 457cb6f
**Files:** app/routers/runs.py (modified, +93 lines)

Added equity price enrichment to the _execute_factiva_pipeline function with full graceful degradation:

**New imports:**
- `from app.models.equity_ticker import EquityTicker`
- `from app.services.equity_client import EquityPriceClient`

**New helper function: _enrich_equity_data()**
- **Parameters:** news_items (list[NewsItem]), run_id (int), db (Session)
- **Returns:** dict[int, list[dict]] mapping insurer_id → equity price dicts
- **Implementation:**
  1. Load all enabled EquityTicker rows from DB
  2. Build ticker_map (case-insensitive entity_name.lower() → EquityTicker row)
  3. Early exit if no tickers configured (returns empty dict)
  4. Check EquityPriceClient.is_configured(), return empty dict if unconfigured
  5. Extract unique insurer_ids from news_items
  6. For each insurer_id:
     - Query Insurer.name from DB
     - Case-insensitive match against ticker_map
     - Check cache first (fetched_prices dict keyed by "TICKER:EXCHANGE")
     - Fetch price via EquityPriceClient.get_price() if not cached
     - Store in equity_data dict and cache for subsequent lookups
  7. Return equity_data dict

**Pipeline integration:**
- Called after db.commit() of NewsItems (line 318)
- Before critical alerts check (line 320)
- Loads all NewsItems for run_id to enrich
- Passes equity_data through to _generate_and_send_report()

**Reporter threading:**
- Added equity_data parameter to _generate_and_send_report() signature (default: None)
- Passes equity_data to report_service.generate_professional_report_from_db() as keyword arg
- Reporter will consume equity_data in Plan 12-03 (for now just threads through)

**Graceful degradation:**
- No tickers configured → returns empty dict, logs message, pipeline continues
- MMC API unconfigured → returns empty dict, logs warning, pipeline continues
- Individual price fetch fails → returns None, logs event, continues to next insurer
- Expected state for dev environments without staging credentials

**Import verification:** ✅ `python -c "from app.routers.runs import router; print('OK')"` succeeded

## Deviations from Plan

None — plan executed exactly as written.

## Technical Implementation

### EquityPriceClient Architecture

**API contract:**
```
GET {mmc_api_base_url}/coreapi/equity-price/v1/price
Headers: X-Api-Key: {mmc_api_key}
Params:  ticker={ticker}&exchange={exchange}
Returns: {"price": float, "change": float, "changePct": float}
```

**Retry strategy:**
- 2 attempts with exponential backoff (min 2s, max 10s)
- Retries on httpx.TimeoutException and httpx.ConnectError only
- 4xx client errors → log warning, return None (no retry)
- 5xx server errors → raise httpx.HTTPStatusError (triggers retry)

**Error handling:**
- Never raises exceptions to callers
- All failures return None
- All outcomes recorded as ApiEvent(type=EQUITY_FETCH) with success flag
- DB event recording failures swallowed (never crash price fetch flow)

**Response field normalization:**
- `price`: tries "price" → "lastPrice" → "last"
- `change`: tries "change" → "priceChange" → "netChange"
- `change_pct`: tries "changePct" → "percentChange" → "pctChange"
- Handles API contract variability without breaking caller

### Pipeline Enrichment Flow

**Execution order:**
1. Factiva collection (batch query with industry codes + keywords)
2. URL deduplication (fast inline check)
3. Semantic deduplication (embedding-based)
4. Insurer matching (deterministic + AI)
5. Classification (AI sentiment + summary)
6. **db.commit() — NewsItems persisted**
7. **Equity enrichment ← NEW (Phase 12)**
8. Critical alerts check
9. Report generation (equity_data passed through)
10. Email delivery

**Enrichment algorithm:**
```python
ticker_rows = db.query(EquityTicker).filter(enabled=True).all()
ticker_map = {row.entity_name.lower(): row for row in ticker_rows}

for insurer_id in unique_insurer_ids:
    insurer = db.query(Insurer).get(insurer_id)
    ticker_row = ticker_map.get(insurer.name.lower())

    cache_key = f"{ticker_row.ticker}:{ticker_row.exchange}"
    if cache_key in fetched_prices:
        equity_data[insurer_id] = [fetched_prices[cache_key]]
        continue

    price_dict = equity_client.get_price(ticker_row.ticker, ticker_row.exchange, run_id)
    if price_dict:
        fetched_prices[cache_key] = price_dict
        equity_data[insurer_id] = [price_dict]
```

**Caching strategy:**
- Cache keyed by "TICKER:EXCHANGE" string (not insurer_id)
- Prevents duplicate API calls when same ticker mapped to multiple insurers
- Cache scoped to single pipeline run (not persisted across runs)
- Example: BB Seguridade (BBSE3) fetched once, reused for all NewsItems mentioning them

### Data Flow

**Input:** NewsItem records with insurer_id foreign keys
**Lookup:** EquityTicker mappings (entity_name → ticker + exchange)
**Fetch:** MMC Core API equity endpoint
**Cache:** Per-run dict to avoid duplicate API calls
**Output:** dict[insurer_id, list[price_dict]] for report rendering

**Example equity_data structure:**
```python
{
  5: [{"ticker": "BBSE3", "exchange": "BVMF", "price": 45.50, "change": 1.25, "change_pct": 2.82}],
  12: [{"ticker": "PSSA3", "exchange": "BVMF", "price": 32.10, "change": -0.45, "change_pct": -1.38}]
}
```

## Integration Points

### Phase 9 Infrastructure Used
- **EquityTicker model** (app/models/equity_ticker.py): entity_name, ticker, exchange, enabled
- **ApiEvent model** (app/models/api_event.py): ApiEventType.EQUITY_FETCH for logging
- **Config** (app/config.py): mmc_api_base_url, mmc_api_key, is_mmc_api_key_configured()
- **Database** (app/database.py): SessionLocal for isolated event recording

### Phase 11 Pipeline Used
- **Factiva pipeline** (app/routers/runs.py): _execute_factiva_pipeline provides enrichment insertion point
- **NewsItem records**: Enrichment reads all NewsItems for run_id to extract insurer_ids
- **Insurer model**: Enrichment queries Insurer.name for ticker mapping

### Enables Phase 12-02 and 12-03
- **Phase 12-02:** Equity data available for admin dashboard display (real-time price monitoring)
- **Phase 12-03:** equity_data dict ready for integration into report templates (price tables + change indicators)

## Testing Evidence

**Import verification:**
```bash
$ python -c "from app.services.equity_client import EquityPriceClient; print('OK')"
OK

$ python -c "from app.routers.runs import router; print('OK')"
OK
```

**Default exchange verification:**
```python
from app.services.equity_client import EquityPriceClient
client = EquityPriceClient()
print(client.get_price.__defaults__)  # ('BVMF', None)
```

**Configuration check:**
```python
client = EquityPriceClient()
print(client.is_configured())  # False (expected without MMC credentials)
```

**Method completeness:**
- Public: `get_price()`, `is_configured()`
- Private: `_fetch_price()`, `_build_headers()`, `_record_event()`
- All methods ported successfully from MDInsights

**Pattern verification:**
- ✅ EquityPriceClient import in runs.py
- ✅ EquityTicker query with `enabled == True` filter
- ✅ _enrich_equity_data function exists
- ✅ equity_data dict passed to reporter
- ✅ Per-run caching with "TICKER:EXCHANGE" keys
- ✅ Graceful degradation when MMC API unconfigured

## Known Limitations

1. **MMC API credentials required for production:** Dev environments will skip enrichment (expected)
2. **Insurer name must exactly match EquityTicker.entity_name:** Case-insensitive but requires exact string match (Phase 12-02 admin UI will help configure mappings)
3. **Equity data not yet rendered in reports:** Threading established, rendering will be implemented in Phase 12-03
4. **No fallback price source:** If MMC API fails, no equity data in reports (acceptable for v1.1)

## Next Phase Readiness

**Phase 12-02 (Equity Admin UI):**
- EquityTicker CRUD routes needed for admins to manage ticker mappings
- Current configuration requires manual DB inserts
- Admin UI will simplify mapping management

**Phase 12-03 (Report Integration):**
- equity_data dict now threaded through to reporter
- Reporter signature updated to accept equity_data parameter
- Next plan will add Jinja2 template rendering for price tables

**Production deployment prerequisites:**
1. MMC API staging credentials must be added to .env
2. Validate with `python scripts/test_auth.py` (Phase 9)
3. Admin creates EquityTicker mappings for tracked insurers (Phase 12-02)
4. First pipeline run will test equity enrichment end-to-end

## Commits

- **ddc7711:** feat(12-01): port EquityPriceClient from MDInsights
- **457cb6f:** feat(12-01): integrate equity enrichment into pipeline

**Total changes:** +376 lines, 2 files (1 created, 1 modified)

---
*Completed: 2026-02-20 | Duration: 24 minutes | Executor: GSD Plan Executor*
