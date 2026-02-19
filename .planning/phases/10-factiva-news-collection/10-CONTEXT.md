# Phase 10: Factiva News Collection - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

The pipeline collects a batch of Brazilian insurance news from Factiva via MMC Core API, fetches full article bodies, deduplicates, and normalizes articles into BrasilIntel's NewsItem schema. This phase does NOT handle insurer matching (Phase 11), does NOT replace Apify yet (Phase 11 switches over), and does NOT add admin UI for query config (Phase 14).

</domain>

<decisions>
## Implementation Decisions

### Query scope & keywords
- **Industry codes**: Sub-sector specific — target insurance sub-sectors (life, P&C, reinsurance, health plans) rather than broad "all insurance"
- **Keywords**: Claude's discretion — researcher determines optimal Portuguese search terms for Brazilian insurance market
- **Geographic scope**: Claude's discretion — researcher determines best geographic filter (Brazil-only vs Brazil + international coverage)
- **Publications**: No preference — let Factiva return whatever matches the query, no source-level filtering

### Batch size & date window
- **Date window**: Last 48 hours with dedup handling cross-run overlap — catches late-indexed articles while deduplicator prevents double-processing
- **Volume cap**: Claude's discretion — researcher determines sensible default based on Factiva typical volumes
- **Volume metrics**: Claude's discretion — researcher/planner determine appropriate logging granularity
- **Empty batch handling**: Claude's discretion — researcher/planner determine appropriate zero-result behavior

### Claude's Discretion
- **Body fetch failures**: All decisions — partial article handling, retry strategy, sequential vs parallel fetching, partial body flagging
- **Dedup tuning**: All decisions — URL dedup strategy, semantic similarity threshold, dedup logging, survivor selection when duplicates span wire services and local outlets
- MDInsights ArticleDeduplicator (0.85 threshold, sentence-transformers) is the proven baseline — adapt as needed for Factiva's wire-service-heavy content

</decisions>

<specifics>
## Specific Ideas

- MDInsights already has a working ArticleDeduplicator in `app/services/deduplicator.py` — port and adapt for Factiva batch characteristics
- The existing decision "Batch Factiva query with post-hoc AI insurer matching (not per-insurer queries)" means this phase builds a single broad query, not 897 individual queries
- v1.0 Apify sources (Valor, CQCS, Estadao, InfoMoney, Google News) provide baseline context for what "Brazilian insurance news" looks like — Factiva should capture equivalent or better coverage
- Pipeline runs daily at 06:00 — 48-hour window with dedup means each run overlaps with the previous day's fetch

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-factiva-news-collection*
*Context gathered: 2026-02-19*
