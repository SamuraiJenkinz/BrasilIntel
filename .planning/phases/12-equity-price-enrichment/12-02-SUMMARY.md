---
phase: 12-equity-price-enrichment
plan: 02
subsystem: admin-ui
completed: 2026-02-19
duration: 3 min
tags: [admin, crud, ui, equity, b3]

tech-stack:
  added: []
  patterns: [fastapi-form-crud, jinja2-templates, bootstrap-admin]

key-files:
  created:
    - app/templates/admin/equity.html
  modified:
    - app/routers/admin.py
    - app/templates/admin/base.html

dependencies:
  requires:
    - app/models/equity_ticker.py (Plan 09-02)
    - app/templates/admin/base.html (Pre-existing)
  provides:
    - Admin UI for managing insurer-to-ticker mappings
    - Seed functionality for 5 default Brazilian insurers
  affects:
    - Plan 12-03: Admin will use this UI to configure tickers before equity enrichment

decisions:
  - key: "BVMF default in UI"
    choice: "Form pre-fills exchange field with 'BVMF'"
    rationale: "BrasilIntel targets Brazilian market — B3 (BVMF) is the primary exchange"
    alternatives: ["NYSE default", "Empty field"]

  - key: "Edit form in same page"
    choice: "equity.html handles both list and edit modes via edit_ticker parameter"
    rationale: "Follows existing BrasilIntel admin pattern (insurers.html uses similar approach)"
    alternatives: ["Separate equity_edit.html template (MDInsights pattern)"]

  - key: "Seed defaults as separate card"
    choice: "Dedicated card at bottom with explicit button vs inline table action"
    rationale: "One-time bulk operation deserves prominent UI treatment, not table row action"
    alternatives: ["Button in header", "Hidden admin-only route"]

file-interactions:
  - from: admin.py
    to: equity_ticker.py
    via: SQLAlchemy CRUD (query, add, update, delete)
    pattern: EquityTicker

  - from: equity.html
    to: base.html
    via: Jinja2 extends directive
    pattern: "{% extends 'admin/base.html' %}"

  - from: base.html sidebar
    to: admin.py
    via: url_for('admin_equity')
    pattern: Navigation link
---

# Phase 12 Plan 02: Admin Equity Ticker UI Summary

**One-liner:** Admin dashboard for managing insurer-to-ticker mappings with seed defaults for 5 Brazilian insurers.

## What Was Built

Built full CRUD admin interface for managing `EquityTicker` mappings:

1. **Six admin routes** (app/routers/admin.py):
   - GET /admin/equity — List all ticker mappings
   - POST /admin/equity — Add new mapping
   - GET /admin/equity/edit/{id} — Edit form (pre-filled)
   - POST /admin/equity/edit/{id} — Update mapping
   - POST /admin/equity/delete/{id} — Delete mapping
   - POST /admin/equity/seed — Seed 5 default Brazilian insurers

2. **Admin template** (app/templates/admin/equity.html):
   - List table: Insurer Name, Ticker, Exchange, Enabled, Updated, Actions
   - Add/Edit form: entity_name, ticker, exchange (default BVMF), enabled checkbox
   - Empty state: "No ticker mappings yet" with graph-up icon
   - Seed defaults card: Shows 5 insurers (BBSE3, SULA11, PSSA3, IRBR3, CXSE3)
   - Delete confirmation: JavaScript confirm dialog
   - Flash messages: Success (green) and error (red) alerts

3. **Sidebar navigation** (app/templates/admin/base.html):
   - Added "Equity Tickers" link with bi-graph-up icon
   - Positioned after Settings in sidebar
   - Active state highlighting when on equity pages

## Validation Results

All success criteria met:

- ✅ Admin can view all existing ticker mappings on /admin/equity
- ✅ Admin can add a new insurer-to-ticker mapping via the form
- ✅ Admin can edit an existing ticker mapping (pre-filled form)
- ✅ Admin can delete a ticker mapping with JavaScript confirmation
- ✅ Duplicate entity_name is rejected with error message (case-insensitive)
- ✅ Sidebar navigation includes an Equity Tickers link with graph icon
- ✅ 5 major Brazilian insurer tickers can be seeded (BBSE3, SULA11, PSSA3, IRBR3, CXSE3)
- ✅ All routes require admin authentication via verify_admin dependency
- ✅ Follows existing BrasilIntel admin patterns (form POST + redirect + flash messages)

## Technical Approach

**Pattern Porting:**
- Base structure ported from MDInsights admin/equity.html
- Adapted to BrasilIntel patterns: single-page edit (vs separate template), BVMF default (vs NYSE)
- Followed existing admin CRUD patterns from insurers/recipients/schedules routes

**Form Handling:**
- Standard HTML form POST (NOT HTMX) with RedirectResponse
- Flash messages via URL query params (?success=, ?error=)
- status_code=303 for all POST redirects (See Other pattern)
- Checkbox handling: "on" value when checked, "off" when unchecked

**Validation:**
- Required fields: entity_name, ticker (non-empty after strip)
- Uniqueness: Case-insensitive query via func.lower(EquityTicker.entity_name)
- Exclusion for updates: id != ticker_id when checking uniqueness
- Defaults: exchange="BVMF", enabled=True

**Seed Defaults:**
- 5 Brazilian insurers: BB Seguridade, SulAmerica, Porto Seguro, IRB Brasil, Caixa Seguridade
- Skip existing: Only insert if entity_name doesn't exist (case-insensitive)
- Count returned: Shows how many were actually added (0-5)

## Deviations from Plan

**Auto-fixed Issues:**

None. Plan executed exactly as written.

**Clarifications:**

1. **Edit form location**: Plan said "GET /admin/equity/edit/{ticker_id}" would render equity.html with edit_ticker parameter. Implemented as specified — MDInsights uses separate equity_edit.html template, but BrasilIntel pattern (insurers.html) uses same-page editing.

2. **Cancel button**: Added cancel link in edit mode that returns to /admin/equity (not specified in plan but improves UX).

## Performance Metrics

- **Duration**: 3 minutes
- **Tasks**: 2/2 completed
- **Commits**: 2 (one per task)
  - c1359e5: Add equity ticker CRUD routes
  - becf448: Create equity admin template and add sidebar nav
- **Files Modified**: 3
  - app/routers/admin.py (+326 lines)
  - app/templates/admin/equity.html (new file, 250 lines)
  - app/templates/admin/base.html (+3 lines sidebar nav)

## Next Phase Readiness

**Phase 12 Plan 03: Pipeline Integration**

Ready to integrate equity enrichment into the pipeline flow. This admin UI enables:

1. **Pre-configuration**: Admins can seed default tickers or add custom mappings before first run
2. **Maintenance**: Ongoing ticker management as new insurers are tracked
3. **Verification**: View all mappings to confirm enrichment will work for specific insurers

**Integration Point:** Plan 12-03 will call EquityPriceClient (12-01) using mappings configured via this UI (12-02).

**No blockers.** Admin interface is fully functional and ready for use.

## Lessons Learned

1. **Pattern consistency matters**: Following existing BrasilIntel admin patterns (form POST + redirect) made implementation straightforward — no need to introduce new patterns for this feature.

2. **MDInsights porting efficiency**: Reference to MDInsights equity.html saved significant time — 80% of template structure reused with minor adaptations (BVMF default, same-page editing).

3. **Seed defaults UX**: Dedicated card with bullet list of tickers provides clear preview before seeding — better than hidden admin action.

4. **Case-insensitive uniqueness**: Using func.lower() for entity_name matching prevents duplicate entries with different capitalization (e.g., "SulAmerica" vs "SULAMERICA").

## Artifacts Delivered

1. Admin CRUD routes for EquityTicker (6 routes)
2. Equity management template with list table, add/edit form, seed defaults
3. Sidebar navigation link with graph-up icon
4. JavaScript confirmation for delete operations
5. Flash message system for success/error feedback

**All plan requirements met. Phase 12 Plan 02 complete.**
