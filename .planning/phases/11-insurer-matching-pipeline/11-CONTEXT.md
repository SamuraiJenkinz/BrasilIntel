# Phase 11: Insurer Matching Pipeline - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Every Factiva article is matched to one or more of the 897 tracked insurers and Factiva becomes the sole active news collection path in the pipeline. Apify is removed from the active pipeline flow (dead code files cleaned up in Phase 15).

</domain>

<decisions>
## Implementation Decisions

### Matching strictness
- **Claude's Discretion**: Full flexibility on deterministic matching strategy
- Claude decides: whether to match on `name`, `search_term`, or both
- Claude decides: case/accent normalization approach for Portuguese text
- Claude decides: whole-word boundary vs substring matching rules
- Claude decides: handling of short/ambiguous insurer names (minimum length threshold, AI routing for short names, context-window matching, etc.)

### Unmatched articles
- **Keep in general pool**: Articles that match no insurer are NOT discarded — store as "unmatched" for industry-wide intelligence value
- Claude decides: whether industry-wide news (regulation, market trends) gets a special category or just sits in the unmatched pool
- Claude decides: AI confidence handling (single attempt vs retry with broader context)
- Claude decides: whether to log/track unmatched articles for matcher tuning

### Multi-insurer articles
- **Claude's Discretion**: Full flexibility on multi-insurer handling
- Claude decides: report display (once per insurer section, or once with multiple tags)
- Claude decides: match cap (if any) to distinguish insurer-specific from industry articles
- Claude decides: database storage model (JSON array, junction table, or per-insurer records) — check existing schema first
- Note: User doesn't remember if schema uses direct insurer_id column or junction table — Claude must inspect actual DB models

### Pipeline switchover
- **Hard cut**: Factiva replaces Apify as sole collection path — cost-driven, no parallel run period
- **Remove Apify from pipeline now**: Phase 11 removes the Apify code path from the active pipeline flow. Phase 15 deletes the dead source class files.
- Claude decides: whether to keep or archive existing Apify-sourced articles in the database
- Claude decides: Factiva-down failure handling (fail run vs skip collection)
- Claude decides: whether a one-time historical backfill is needed to bridge the Apify-to-Factiva gap

### Claude's Discretion
- Deterministic matching algorithm design (fields, normalization, boundaries, short-name handling)
- AI disambiguation prompt design and confidence thresholds
- Multi-insurer storage and display strategy
- Factiva failure handling and historical backfill decisions
- Industry-wide news categorization

</decisions>

<specifics>
## Specific Ideas

- "Cost issue and we own Factiva" — the switchover is cost-motivated, not quality-motivated. Apify costs money; Factiva is already paid for through MMC enterprise licensing.
- The 897 insurers have `name` and `search_term` fields available for matching
- Portuguese text normalization is important — accented characters (Sul America vs Sul America vs SULAMERICA) are common in Brazilian insurance company names

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-insurer-matching-pipeline*
*Context gathered: 2026-02-19*
