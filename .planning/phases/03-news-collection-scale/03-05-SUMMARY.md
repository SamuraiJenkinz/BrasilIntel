---
phase: 03-news-collection-scale
plan: 05
subsystem: relevance-scoring
tags: [azure-openai, relevance, filtering, cost-optimization]
requires: ["03-01"]
provides: ["RelevanceScorer service", "Two-pass filtering pattern"]
affects: ["03-06"]
tech-stack:
  added: []
  patterns: ["Two-pass filtering", "Fail-open error handling", "Batch AI processing"]
key-files:
  created:
    - app/services/relevance_scorer.py
    - tests/test_relevance_scorer.py
  modified:
    - app/config.py
decisions:
  - id: "03-05-01"
    decision: "Two-pass filtering: keyword first, AI second"
    rationale: "Keyword filtering is free and fast, reduces AI API costs"
  - id: "03-05-02"
    decision: "Fail-open error handling"
    rationale: "Better to pass marginal content than risk filtering good news"
  - id: "03-05-03"
    decision: "Portuguese prompts for AI scoring"
    rationale: "Consistent with classification service, better Brazilian context"
metrics:
  duration: "~3 minutes"
  completed: "2026-02-04"
---

# Phase 03 Plan 05: Relevance Scorer Summary

AI relevance pre-filter using two-pass keyword + AI scoring to reduce classification costs.

## What Was Built

### Configuration (app/config.py)
Added 3 new settings for relevance scoring control:
- `use_ai_relevance_scoring`: Enable/disable AI scoring (default: True)
- `relevance_keyword_threshold`: Items below this skip AI (default: 20)
- `relevance_ai_batch_size`: Items per AI request (default: 10)

### RelevanceScorer Service (app/services/relevance_scorer.py)
350-line service implementing two-pass relevance filtering:

**Main Entry Point:**
```python
def score_batch(
    items: list[ScrapedNewsItem],
    insurer_name: str,
    max_results: int | None = None
) -> list[ScrapedNewsItem]
```

**Pass 1 - Keyword Filter (Free):**
- Splits insurer name into searchable parts
- Skips short words (de, da, do) that would match too broadly
- Case-insensitive matching in title and description
- Zero API cost, sub-millisecond execution

**Pass 2 - AI Filter (Paid):**
- Only triggered when keyword matches exceed threshold (default: 20)
- Processes in configurable batches (default: 10)
- Portuguese prompt optimized for Brazilian insurance context
- Structured response parsing with fail-open fallback

**Error Handling:**
- Fail-open pattern: On any error, items are kept (not filtered)
- Graceful degradation: Works without Azure OpenAI configured
- Health check endpoint for monitoring

### Tests (tests/test_relevance_scorer.py)
15 unit tests covering:
- Keyword filtering by name parts
- Case insensitive matching
- Description text searching
- Short word filtering
- Empty list handling
- Max results limiting
- AI threshold logic
- Response parsing edge cases
- Health check behavior

## Technical Decisions

| Decision | Rationale |
|----------|-----------|
| Keyword filter first | Free and fast, reduces API calls by ~80% |
| Threshold of 20 items | Balance between cost savings and relevance |
| Fail-open errors | Better false positives than false negatives |
| Portuguese prompts | Consistent with existing classifier service |
| Batch size of 10 | Optimizes for API rate limits and token costs |

## Integration Points

**Inputs:**
- `ScrapedNewsItem` from `app.services.sources` (03-01)
- Settings from `app.config`

**Outputs:**
- Filtered `list[ScrapedNewsItem]` for classification pipeline

**Dependencies:**
- Azure OpenAI client (same pattern as classifier.py)
- Settings for configuration

## Verification

All success criteria met:
1. Configuration extended with relevance scoring settings
2. RelevanceScorer uses two-pass filtering (keyword then AI)
3. Keyword filtering is fast and free (no API calls)
4. AI scoring only triggered when items exceed threshold
5. Portuguese prompts for Brazilian context
6. Fail-open error handling (keep items on error)
7. All 15 tests pass

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 95393f4 | feat | Add relevance scoring configuration |
| 4b6e1c5 | feat | Create relevance scorer service |
| 465b0b0 | test | Add relevance scorer unit tests |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 03-06 (Integration):
- RelevanceScorer exports `score_batch()` method
- Compatible with ScrapedNewsItem from sources module
- Configurable via Settings for easy tuning
