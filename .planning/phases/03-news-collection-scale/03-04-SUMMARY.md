---
phase: 03-news-collection-scale
plan: 04
subsystem: scraping
tags: [batch-processing, asyncio, rate-limiting, concurrency]
depends_on:
  requires: ["03-01", "03-02", "03-03"]
  provides: ["BatchProcessor", "BatchProgress", "InsurerResult"]
  affects: ["03-06"]
tech-stack:
  added: []
  patterns: ["semaphore-concurrency", "batch-delay-rate-limiting", "progress-callback"]
key-files:
  created:
    - app/services/batch_processor.py
    - tests/__init__.py
    - tests/test_batch_processor.py
  modified: []
decisions:
  - id: "03-04-01"
    choice: "Semaphore-based concurrency control"
    why: "asyncio.Semaphore provides lightweight concurrency limiting without thread pool overhead"
  - id: "03-04-02"
    choice: "Batch + delay pattern for rate limiting"
    why: "Configurable batch_size and delay_seconds allow tuning for different source limits"
  - id: "03-04-03"
    choice: "Custom search_terms support"
    why: "Insurer model has search_terms field (DATA-03) for customized queries"
metrics:
  duration: ~4 minutes
  completed: 2026-02-04
---

# Phase 03 Plan 04: Batch Processor Summary

**One-liner:** Semaphore-controlled batch processor for 897 insurers with configurable rate limiting and progress tracking.

## What Was Built

### BatchProcessor Service (`app/services/batch_processor.py`)

Core orchestration service for processing multiple insurers:

```python
class BatchProcessor:
    def __init__(
        self,
        batch_size: int | None = None,      # Default 30 from settings
        max_concurrent: int | None = None,   # Default 3 from settings
        delay_seconds: float | None = None,  # Default 2.0 from settings
        sources: list[NewsSource] | None = None,  # All registered sources
    ): ...

    async def process_insurers(
        self,
        insurers: list[Insurer],
        run: Run | None = None,
        db: Session | None = None,
        progress_callback: Callable[[BatchProgress], Awaitable[None]] | None = None,
    ) -> BatchProgress: ...

    async def process_category(
        self,
        category: str,
        db: Session,
        run: Run | None = None,
        enabled_only: bool = True,
    ) -> BatchProgress: ...
```

### Data Classes

**BatchProgress** - Tracks processing statistics:
- `total_insurers`, `processed_insurers`, `total_items_found`
- `errors` list for per-insurer failures
- `percent_complete` property for progress percentage
- `elapsed_seconds` property for timing

**InsurerResult** - Per-insurer scraping result:
- `insurer_id`, `insurer_name`, `items`, `error`
- `success` property returns `error is None`

### Key Features

1. **Semaphore-based concurrency:** `asyncio.Semaphore(self.max_concurrent)` limits parallel scraping
2. **Batch processing:** Processes insurers in configurable batches (default 30)
3. **Rate limiting:** Configurable delay between batches (default 2.0 seconds)
4. **Graceful error handling:** One insurer failure doesn't stop the batch
5. **Custom search terms:** Uses `insurer.search_terms` if available, else `"{name}" OR "ANS {code}"`
6. **Progress persistence:** Optional Run/DB integration updates `insurers_processed`, `items_found`
7. **Progress callbacks:** Async callback after each batch for real-time updates

## Test Coverage

Created `tests/test_batch_processor.py` with 15 tests:
- BatchProgress: percent calculation, elapsed time, error tracking
- InsurerResult: success/error detection, default items list
- BatchProcessor: initialization, empty list handling, no sources error
- Async tests with mocked sources
- Custom search terms verification

All tests pass: `pytest tests/test_batch_processor.py -v`

## Integration Points

### Uses From Previous Plans
- `SourceRegistry.get_all()` from 03-01 (6 registered sources)
- `Settings.batch_size`, `max_concurrent_sources`, `batch_delay_seconds` from 03-03
- `Insurer`, `Run`, `NewsItem` models from 02-01

### Provides For Future Plans
- `BatchProcessor` for 03-06 integration
- `BatchProgress` for run status updates
- `process_category()` for category-based pipeline execution

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**03-05 (Relevance Scorer):** Ready
- BatchProcessor provides items for scoring
- No blockers identified

**03-06 (Integration):** Ready
- BatchProcessor integrates with Run orchestration
- process_category() provides entry point for pipeline

## Verification Evidence

```
batch_size: 30
max_concurrent: 3
sources: 6
percent: 50.0%
Progress: 75.0% complete, 500 items
Empty process: 0 processed
Async functionality: OK
15 tests passed
```

## Commits

| Commit | Description |
|--------|-------------|
| cc3b64f | feat(03-04): add batch processor for 897 insurers |
| 3515ff5 | test(03-04): add unit tests for batch processor |
