---
phase: 12-equity-price-enrichment
plan: 03
subsystem: report-display
tags: [equity-prices, report-template, email-compatible, ui]
requires:
  - phase: 12
    plan: 01
    artifact: equity_data dict passed through pipeline
  - phase: 12
    plan: 02
    artifact: Admin UI for ticker mappings
provides:
  - artifact: Equity chip display in reports
    path: app/templates/report_professional.html
    capability: Show real-time B3 stock prices in browser and email reports
  - artifact: Reporter equity data threading
    path: app/services/reporter.py
    capability: Pass equity data from pipeline to template rendering
affects:
  - phase: 13
    plan: any
    reason: Equity chips now visible to senior management in daily reports
tech-stack:
  added: []
  patterns:
    - Email-compatible inline styles (no external CSS)
    - HTML entities for cross-client compatibility
    - Graceful degradation when equity data unavailable
    - Progressive enhancement with CSS class
key-files:
  created: []
  modified:
    - app/services/reporter.py
    - app/templates/report_professional.html
decisions:
  - decision: Inline styles only (no external CSS or style blocks)
    rationale: BrasilIntel has ONE template for both browser and email — GraphEmailService sends report_professional.html directly as html_body
    impact: All equity chip styles must be inline for Outlook/Gmail compatibility
    phase: 12-03
  - decision: HTML entities for arrows (&#9650; &#9660;)
    rationale: Unicode arrows may not render correctly in Outlook's Word rendering engine
    impact: Safer cross-client display, universally supported entities
    phase: 12-03
  - decision: R$ Brazilian Real currency format
    rationale: BrasilIntel targets Brazilian insurers on B3 exchange
    impact: Matches local currency expectations, not USD
    phase: 12-03
  - decision: Inline-block spans (not table layout)
    rationale: Single equity chip per insurer is simple enough for inline-block
    impact: Cleaner markup, email-safe, easier to maintain
    phase: 12-03
  - decision: Insert between h2 and insurer-codes div
    rationale: Equity price data is insurer-level context, belongs next to name
    impact: Visual hierarchy: Name → Price → Codes → News
    phase: 12-03
metrics:
  duration: 2 minutes
  completed: 2026-02-20
---

# Phase 12 Plan 03: Equity Price Chip Display Summary

**One-liner:** Email-compatible equity price chips in professional reports show B3 stock data (ticker, R$ price, change%) next to insurer names

## Objective

Add equity price chip display to the professional report template, visible in both browser rendering and email delivery, completing the user-facing equity enrichment feature for senior management.

## Execution Summary

Successfully threaded equity_data through the reporter service to the template and added email-compatible equity chip markup with inline styles for Outlook/Gmail compatibility. Chips show ticker symbol, Brazilian Real price, and colored change percentage using HTML entities for arrows.

## Tasks Completed

### Task 1: Thread equity data through reporter service to template
**Status:** ✅ Complete
**Commit:** aa3c476
**Files:** app/services/reporter.py (+15 lines, -4 lines)

Updated app/services/reporter.py to accept and pass equity data to the report template:

**Method signature updates:**
- `generate_professional_report()`: Added `equity_data: dict = None` parameter
- `generate_professional_report_from_db()`: Added `equity_data: dict = None` parameter
- Both methods default to empty dict if None for backward compatibility
- Pass `equity_by_insurer=equity_data` to `template.render()` call

**Docstring updates:**
- Added equity_data parameter documentation
- Added "Equity price chips (optional)" to feature list
- Clarified equity_data format: dict mapping insurer_id to list of price dicts

**Data flow:**
```
runs.py:_enrich_equity_data()
  → equity_data dict {insurer_id: [price_dict, ...]}
  → _generate_and_send_report(equity_data=equity_data)
  → reporter.generate_professional_report_from_db(equity_data=equity_data)
  → reporter.generate_professional_report(equity_data=equity_data)
  → template.render(equity_by_insurer=equity_data)
  → Jinja2 template uses equity_by_insurer
```

**Backward compatibility:**
- Default `equity_data = None` in both methods
- Convert None to empty dict `{}` immediately after entry
- Template conditionals: `{% if equity_by_insurer and equity_by_insurer.get(insurer.id) %}`
- Reports render exactly as before when equity_data is empty or not provided

**Import verification:** ✅ `python -c "from app.services.reporter import ReportService; print('OK')"` succeeded

### Task 2: Add email-compatible equity chips to professional report template
**Status:** ✅ Complete
**Commit:** 7ecf055
**Files:** app/templates/report_professional.html (+26 lines)

Added equity price chip display to app/templates/report_professional.html inside each insurer section:

**Placement:**
- Inside `.insurer-header` div
- Between `<h2>{{ insurer.name }}</h2>` and `<div class="insurer-codes">`
- Visual hierarchy: Name → Equity chips → Code badges → Status badge

**Markup structure:**
```html
{% if equity_by_insurer and equity_by_insurer.get(insurer.id) %}
<div class="equity-chip-container" style="margin-top: 6px; margin-bottom: 8px;">
    {% for eq in equity_by_insurer.get(insurer.id, []) %}
    <span style="display: inline-block; background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 4px 10px; border-radius: 4px; font-size: 0.75em; font-weight: 600; margin-right: 6px; margin-bottom: 4px; vertical-align: middle;">
        <span style="color: #00263e;">{{ eq.ticker }}</span>
        {% if eq.price is not none %}
        <span style="color: #495057; margin-left: 4px;">R$&nbsp;{{ "%.2f"|format(eq.price) }}</span>
        {% endif %}
        {% if eq.change_pct is not none %}
        {% if eq.change_pct > 0 %}
        <span style="color: #198754; margin-left: 4px;">&#9650;&nbsp;{{ "%.2f"|format(eq.change_pct) }}%</span>
        {% elif eq.change_pct < 0 %}
        <span style="color: #dc3545; margin-left: 4px;">&#9660;&nbsp;{{ "%.2f"|format(eq.change_pct|abs) }}%</span>
        {% else %}
        <span style="color: #6c757d; margin-left: 4px;">&mdash;</span>
        {% endif %}
        {% endif %}
    </span>
    {% endfor %}
</div>
{% endif %}
```

**Email compatibility design:**
- **ALL styles are inline** — no external CSS, no class references for core display
- **display: inline-block** (not flex or grid) — Outlook Word engine compatible
- **HTML entities for arrows** — &#9650; (up triangle) and &#9660; (down triangle) instead of Unicode chars
- **&nbsp; for spacing** — non-breaking space between currency and amount
- **Marsh brand colors:**
  - `#00263e` — ticker symbol (Marsh blue)
  - `#198754` — positive change (green)
  - `#dc3545` — negative change (red)
  - `#6c757d` — neutral/zero change (grey)
- **R$ currency format** — Brazilian Real (not $USD)
- **Font size 0.75em** — compact chip next to h2 heading

**Progressive enhancement:**
- Added CSS class `.equity-chip-container` in `<style>` block (lines 321-324)
- Browsers use class styles, emails strip and use inline styles
- Class added alongside inline styles: `class="equity-chip-container" style="..."`

**Graceful absence:**
- `{% if equity_by_insurer and equity_by_insurer.get(insurer.id) %}`
- No markup output when equity_by_insurer is empty dict, None, or insurer has no ticker
- `{% if eq.price is not none %}` — price display only when available
- `{% if eq.change_pct is not none %}` — change% display only when available

**Jinja2 filter usage:**
- `|format()` — built-in string formatting for price/change_pct decimals
- `|abs` — absolute value filter for negative change_pct display (Jinja2 3.0+ native)

**Template verification:** ✅ `rs.env.get_template('report_professional.html')` loads without errors

## Deviations from Plan

None — plan executed exactly as written.

## Technical Implementation

### Equity Data Flow (Complete Pipeline)

**Phase 12-01 (EquityPriceClient):**
```python
equity_client = EquityPriceClient()
price_dict = equity_client.get_price("BBSE3", "BVMF", run_id)
# Returns: {"ticker": "BBSE3", "exchange": "BVMF", "price": 45.50, "change": 1.25, "change_pct": 2.82}
```

**Phase 12-01 (Pipeline Enrichment):**
```python
equity_data = _enrich_equity_data(news_items, run_id, db)
# Returns: {5: [price_dict], 12: [price_dict], ...}
# Keys are insurer_id, values are lists of price dicts (one ticker per insurer currently)
```

**Phase 12-03 (Reporter Threading — THIS PLAN):**
```python
# runs.py
delivery_result = await _generate_and_send_report(
    request.category, run.id, db, request.send_email, equity_data
)

# _generate_and_send_report()
html_report, archive_path = report_service.generate_professional_report_from_db(
    category=request.category,
    run_id=run.id,
    db_session=db,
    equity_data=equity_data,  # ← NEW
)

# reporter.py
html = template.render(
    ...
    equity_by_insurer=equity_data,  # ← NEW
)
```

**Phase 12-03 (Template Rendering — THIS PLAN):**
```jinja2
{% if equity_by_insurer and equity_by_insurer.get(insurer.id) %}
    {% for eq in equity_by_insurer.get(insurer.id, []) %}
        TICKER: {{ eq.ticker }}
        PRICE: R$ {{ "%.2f"|format(eq.price) }}
        CHANGE: ↑ {{ "%.2f"|format(eq.change_pct) }}%
    {% endfor %}
{% endif %}
```

### Email Compatibility Strategy

**Problem:** BrasilIntel uses ONE template for both browser display AND email body
**Solution:** All styles must be inline for Outlook/Gmail compatibility

**Why inline styles?**
- GraphEmailService (Phase 8) sends `report_professional.html` directly as `html_body`
- No separate email template like MDInsights has (role_email.html)
- Outlook uses Word rendering engine — strips external CSS and style blocks
- Gmail strips style blocks, only processes inline styles

**Email client compatibility matrix:**

| Feature | Outlook | Gmail | Apple Mail | Thunderbird |
|---------|---------|-------|------------|-------------|
| Inline styles | ✅ | ✅ | ✅ | ✅ |
| Style blocks | ❌ | ❌ | ✅ | ✅ |
| External CSS | ❌ | ❌ | ❌ | ❌ |
| Flexbox | ❌ | ⚠️ | ✅ | ✅ |
| Grid | ❌ | ❌ | ✅ | ✅ |
| inline-block | ✅ | ✅ | ✅ | ✅ |
| HTML entities | ✅ | ✅ | ✅ | ✅ |
| Unicode arrows | ⚠️ | ✅ | ✅ | ✅ |

**Design decisions for maximum compatibility:**
1. **Inline styles only** — `style="..."` attributes on every element
2. **display: inline-block** — not flex or grid (Outlook doesn't support)
3. **HTML entities** — `&#9650;` and `&#9660;` instead of Unicode ▲▼ (safer)
4. **No nested tables** — simple span structure for single chips per insurer
5. **Non-breaking spaces** — `&nbsp;` for currency/price spacing
6. **Fixed colors** — hex codes not CSS variables (Outlook strips vars)

### Visual Design

**Equity chip appearance:**
```
┌─────────────────────────────────────┐
│ BBSE3  R$ 45.50  ▲ 2.82%           │
└─────────────────────────────────────┘
 ^^^^^^  ^^^^^^^^  ^^^^^^^^^
 Ticker  Price     Change% (colored)
 #00263e #495057   #198754 (green)
```

**Insurer section layout (updated):**
```
┌─────────────────────────────────────────────────┐
│ Seguradora XYZ                         [Status] │
│ BBSE3  R$ 45.50  ▲ 2.82%                       │  ← NEW
│ ANS: 123456  MM: ABC123  CNPJ: 12.345.678/0001 │
├─────────────────────────────────────────────────┤
│ News items...                                   │
└─────────────────────────────────────────────────┘
```

**Color meanings:**
- **Green ▲** — positive performance, good news for insurer
- **Red ▼** — negative performance, potential concern
- **Grey —** — no change, stability

**Currency format:**
- `R$ 45.50` — Brazilian Real with two decimal places
- Non-breaking space between R$ and amount
- Matches local market expectations (B3 is Brazilian exchange)

### Integration Points

**Phase 12-01 Used:**
- `equity_data` dict format from `_enrich_equity_data()`
- price_dict structure: `{ticker, exchange, price, change, change_pct}`
- Per-run caching ensures same ticker fetched once per run

**Phase 12-02 Enabled:**
- Admin UI allows configuring ticker mappings before runs
- Seed defaults (BBSE3, SULA11, PSSA3, IRBR3, CXSE3) ready to use
- Enabled tickers automatically matched during enrichment

**Phase 8 Email Delivery:**
- GraphEmailService sends `report_professional.html` as html_body
- No template transformation — what you see in browser is what you get in email
- Inline styles essential for this single-template approach

**Phase 5 Report Generation:**
- ReportService.generate_professional_report() now equity-aware
- Backward compatible — empty dict when equity_data not provided
- Archive includes equity chips (visual snapshot of market at report time)

## Testing Evidence

**Import verification:**
```bash
$ python -c "from app.services.reporter import ReportService; print('OK')"
OK

$ python -c "from app.services.reporter import ReportService; rs = ReportService(); tmpl = rs.env.get_template('report_professional.html'); print('Template loads: OK')"
Template loads: OK
```

**Markup verification:**
```bash
$ grep -n "equity-chip-container" app/templates/report_professional.html
321:        .equity-chip-container {
809:                        <div class="equity-chip-container" style="margin-top: 6px; margin-bottom: 8px;">

$ grep -n "&#9650;" app/templates/report_professional.html
818:                                <span style="color: #198754; margin-left: 4px;">&#9650;&nbsp;{{ "%.2f"|format(eq.change_pct) }}%</span>

$ grep -n "&#9660;" app/templates/report_professional.html
820:                                <span style="color: #dc3545; margin-left: 4px;">&#9660;&nbsp;{{ "%.2f"|format(eq.change_pct|abs) }}%</span>

$ grep -n "R\\\$" app/templates/report_professional.html
814:                                <span style="color: #495057; margin-left: 4px;">R$&nbsp;{{ "%.2f"|format(eq.price) }}</span>
```

**Conditional rendering verification:**
- ✅ `{% if equity_by_insurer and equity_by_insurer.get(insurer.id) %}` — checks both existence and insurer-specific data
- ✅ `{% if eq.price is not none %}` — price display only when available
- ✅ `{% if eq.change_pct is not none %}` — change% display only when available
- ✅ `{% if eq.change_pct > 0 %}` — green up arrow for positive
- ✅ `{% elif eq.change_pct < 0 %}` — red down arrow for negative
- ✅ `{% else %}` — grey dash for zero change

**Inline style verification:**
- ✅ All core equity chip styles are inline (no class dependencies)
- ✅ display: inline-block used (not flex or grid)
- ✅ HTML entities used for arrows (not Unicode)
- ✅ &nbsp; used for spacing (non-breaking)
- ✅ R$ currency format (Brazilian Real)

## Known Limitations

1. **Single ticker per insurer:** Current implementation assumes one equity mapping per insurer (ticker_map uses entity_name as key, not ID). Phase 12-02 UI allows multiple tickers per entity theoretically, but enrichment only uses first match. Future enhancement: support multiple tickers (e.g., preferred + common shares).

2. **No fallback icon when ticker missing:** If insurer has no ticker configured, no chip appears (graceful absence). Could add placeholder icon in future (e.g., "No ticker configured" badge).

3. **Equity data not cached across runs:** Each run fetches fresh prices. Archive reports show equity snapshot at time of generation, not current prices. Expected behavior, but worth documenting.

4. **Email client testing needed:** While markup follows email-safe patterns, real Outlook/Gmail testing recommended before production deployment. Inline styles should work, but visual QA needed.

## Next Phase Readiness

**Phase 12 Complete:**
- ✅ Plan 12-01: EquityPriceClient ported and integrated
- ✅ Plan 12-02: Admin UI for ticker mappings with seed defaults
- ✅ Plan 12-03: Equity chips visible in reports (THIS PLAN)

**Production deployment prerequisites:**
1. MMC API staging credentials must be added to .env
2. Validate with `python scripts/test_auth.py` (Phase 9)
3. Admin creates/seeds EquityTicker mappings via /admin/equity (Phase 12-02)
4. First Factiva pipeline run will enrich equity data (Phase 12-01)
5. Reports will show equity chips for insurers with configured tickers (Phase 12-03)
6. Email delivery will include equity chips in html_body (Phase 8 + 12-03)

**Phase 13 (Email Configuration):**
- Equity chips now visible in reports
- Senior management will see real-time B3 stock prices alongside insurer news
- GraphEmailService delivers full visual report with equity context
- No changes needed in Phase 13 for equity display

**Visual QA testing recommended:**
1. Generate test report with equity_data (via preview_professional_template or actual run)
2. View in browser (should see equity chips with colors)
3. Send test email to Outlook account (verify inline styles render)
4. Send test email to Gmail account (verify inline styles render)
5. Check mobile email clients (iOS Mail, Gmail app)
6. Validate color contrast for accessibility

## Commits

- **aa3c476:** feat(12-03): thread equity data through reporter to template
- **7ecf055:** feat(12-03): add email-compatible equity chips to report template

**Total changes:** +41 lines, -4 lines, 2 files modified

---
*Completed: 2026-02-20 | Duration: 2 minutes | Executor: GSD Plan Executor*
