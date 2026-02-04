---
phase: 02-vertical-slice-validation
plan: 01
subsystem: data-persistence
tags: [sqlalchemy, orm, models, schemas, database]

requires:
  - "01-01-PLAN: Database infrastructure and Base model"
  - "01-02-PLAN: Insurer ORM model with relationships"

provides:
  - Run model for tracking scraping execution history
  - NewsItem model for storing scraped news with classification
  - Bidirectional ORM relationships (Insurer→NewsItem, Run→NewsItem)
  - Pydantic schemas for API request/response validation

affects:
  - "02-02-PLAN: Configuration will reference these models"
  - "02-03-PLAN: Scraper service will create Run and NewsItem records"
  - "02-04-PLAN: Classifier service will update NewsItem classification fields"
  - "02-05-PLAN: Report service will query NewsItem with joins"

tech-stack:
  added:
    - "SQLAlchemy relationships (ForeignKey, relationship, back_populates)"
    - "Pydantic enums for status, sentiment, and trigger types"
  patterns:
    - "Separate ORM models (app/models) and Pydantic schemas (app/schemas)"
    - "Foreign key relationships with bidirectional navigation"
    - "Enum-based status tracking for type safety"

key-files:
  created:
    - app/models/run.py
    - app/models/news_item.py
    - app/schemas/run.py
    - app/schemas/news.py
  modified:
    - app/models/insurer.py
    - app/models/__init__.py
    - app/schemas/__init__.py
    - app/main.py

decisions:
  - slug: run-category-field
    title: Run model tracks category (Health/Dental/Group Life)
    rationale: Enables targeted scraping per insurance category with independent scheduling
    impact: Each category can have separate scheduled jobs with isolated failure domains
    alternatives: Single run for all categories (would create coupling and harder error recovery)

  - slug: classification-nullable-fields
    title: NewsItem classification fields (status, sentiment, summary) are nullable
    rationale: News items are created by scraper before classification by Azure OpenAI
    impact: Two-phase workflow - scrape then classify. Classification service updates existing records
    alternatives: Combined scrape+classify (would slow scraping and complicate error handling)

  - slug: trigger-type-enum
    title: Run trigger_type enum with 'scheduled' and 'manual' values
    rationale: Differentiates automatic scheduled runs from manual admin-triggered runs
    impact: Enables analytics on automation vs. manual intervention, useful for monitoring
    alternatives: Boolean field (less extensible for future trigger types like API-triggered)

metrics:
  tasks: 3
  duration: "~2.5 minutes"
  files_created: 4
  files_modified: 4
  commits: 4
  completed: "2026-02-04"
---

# Phase 02 Plan 01: Database Models Summary

**One-liner:** Created Run and NewsItem ORM models with bidirectional relationships, Pydantic schemas, and status enums for scraping pipeline persistence.

## What Was Built

### Core ORM Models

**Run Model (`app/models/run.py`):**
- Tracks scraping execution history with status lifecycle
- Fields: id, category, trigger_type, status, timestamps, counts, error_message
- Relationship: `news_items` (one-to-many to NewsItem)
- Status enum: pending, running, completed, failed
- Trigger enum: scheduled, manual

**NewsItem Model (`app/models/news_item.py`):**
- Stores scraped news with classification results
- Content fields: title, description, source_url, source_name, published_at
- Classification fields: status (Critical/Watch/Monitor/Stable), sentiment, summary
- Foreign keys: run_id, insurer_id
- Relationships: `run` (many-to-one), `insurer` (many-to-one)

**Insurer Model Enhancement:**
- Added `news_items` relationship (one-to-many to NewsItem)
- Enables bidirectional navigation: `insurer.news_items` and `news_item.insurer`

### Pydantic Schemas

**Run Schemas (`app/schemas/run.py`):**
- `RunBase`: Common fields (category, trigger_type)
- `RunCreate`: Request schema for creating runs
- `RunRead`: Response schema with full run details
- Enums: `RunStatus`, `TriggerType`

**NewsItem Schemas (`app/schemas/news.py`):**
- `NewsItemBase`: Common content fields
- `NewsItemCreate`: Request schema with foreign keys
- `NewsItemRead`: Response schema without classification
- `NewsItemWithClassification`: Full response with Azure OpenAI results
- Enums: `InsurerStatus`, `Sentiment`

### Database Integration

**Table Creation:**
- Updated `app/main.py` to import new models for SQLAlchemy registration
- Tables created on application startup via `Base.metadata.create_all()`
- Verified table schemas and foreign key constraints in SQLite

**Schema Verification:**
```
runs table: 9 columns (id, category, trigger_type, status, timestamps, counts, error_message)
news_items table: 12 columns (id, foreign keys, content fields, classification fields, timestamp)
Foreign keys: news_items.run_id → runs.id, news_items.insurer_id → insurers.id
```

## Technical Implementation

### SQLAlchemy Relationship Pattern

Used bidirectional relationships with explicit `back_populates`:

```python
# In NewsItem model
run = relationship("Run", back_populates="news_items")
insurer = relationship("Insurer", back_populates="news_items")

# In Run model
news_items = relationship("NewsItem", back_populates="run")

# In Insurer model (added)
news_items = relationship("NewsItem", back_populates="insurer")
```

Benefits:
- Navigation in both directions (parent.children, child.parent)
- SQLAlchemy maintains referential integrity
- Lazy loading by default (queries only when accessed)

### Pydantic Configuration

Used `ConfigDict(from_attributes=True)` for ORM compatibility:

```python
class RunRead(RunBase):
    model_config = ConfigDict(from_attributes=True)
    # ... fields
```

This enables Pydantic to read from SQLAlchemy models directly, avoiding manual conversion.

### Enum-Based Type Safety

All status and type fields use enums:
- `RunStatus`: PENDING, RUNNING, COMPLETED, FAILED
- `TriggerType`: SCHEDULED, MANUAL
- `InsurerStatus`: CRITICAL, WATCH, MONITOR, STABLE
- `Sentiment`: POSITIVE, NEGATIVE, NEUTRAL

Benefits:
- Type safety at API and database level
- FastAPI auto-generates enum documentation
- Invalid values rejected at validation layer

## Decisions Made

### 1. Classification Fields Nullable

**Decision:** NewsItem classification fields (status, sentiment, summary) are nullable.

**Rationale:**
- Scraper creates NewsItem records immediately upon discovery
- Azure OpenAI classification runs as separate async process
- Two-phase workflow: scrape → classify → update

**Impact:**
- Services can be deployed and tested independently
- Classification failures don't block news ingestion
- Enables progress tracking (how many items awaiting classification)

**Alternative Considered:** Combined scrape+classify in single operation
- **Rejected:** Would couple services, slow scraping, complicate error handling

### 2. Run Model Per-Category Tracking

**Decision:** Run model has `category` field (Health, Dental, Group Life).

**Rationale:**
- Three separate scheduled jobs for staggered execution
- Independent failure domains (Dental scraper failure doesn't block Health)
- Category-specific monitoring and alerting

**Impact:**
- Windows Scheduled Task can trigger category-specific runs
- Reporting can show per-category execution history
- Resource usage can be analyzed by category

**Alternative Considered:** Single run for all categories
- **Rejected:** Creates coupling, harder error recovery, resource contention

### 3. Trigger Type Enum

**Decision:** Run has `trigger_type` enum with 'scheduled' and 'manual' values.

**Rationale:**
- Differentiates automatic scheduled runs from manual admin actions
- Useful for monitoring automation effectiveness
- Future extensibility (could add 'api-triggered', 'test', etc.)

**Impact:**
- Analytics can measure manual vs. automatic run ratio
- Alerts can differentiate scheduled failures (urgent) vs. manual test failures
- Audit trail shows who/what initiated runs

**Alternative Considered:** Boolean `is_scheduled` field
- **Rejected:** Less extensible, harder to add new trigger types later

## How It Works

### Creating a New Run

```python
from app.models import Run
from app.database import SessionLocal

# Scraper creates a run when starting
db = SessionLocal()
run = Run(
    category="Health",
    trigger_type="scheduled",
    status="running"
)
db.add(run)
db.commit()
db.refresh(run)  # Get assigned ID
```

### Creating News Items During Scraping

```python
from app.models import NewsItem

# For each news item found
news_item = NewsItem(
    run_id=run.id,
    insurer_id=insurer.id,
    title="Insurer X launches new product",
    source_url="https://example.com/news/123",
    published_at=datetime(2026, 2, 4, 12, 0)
    # classification fields remain NULL
)
db.add(news_item)
```

### Updating Classification Results

```python
# Azure OpenAI classification service updates existing records
news_item = db.query(NewsItem).filter_by(id=123).first()
news_item.status = "Critical"
news_item.sentiment = "negative"
news_item.summary = "• New regulation impacts pricing\n• Expected revenue decline"
db.commit()
```

### Querying with Relationships

```python
# Get all news for an insurer
insurer = db.query(Insurer).filter_by(ans_code="123456").first()
for news in insurer.news_items:
    print(f"{news.title} - {news.status}")

# Get all items from a run
run = db.query(Run).filter_by(id=1).first()
print(f"Found {len(run.news_items)} items in run {run.id}")
```

## Testing Performed

### Verification Checklist

✅ **Import Tests:**
- All models import without error: `from app.models import Insurer, Run, NewsItem`
- All schemas import without error: `from app.schemas.run import *; from app.schemas.news import *`

✅ **Database Creation:**
- Server starts successfully
- Tables created: runs, news_items, insurers
- Foreign keys configured correctly

✅ **Schema Validation:**
```
runs: 9 columns (id, category, trigger_type, status, started_at, completed_at,
                insurers_processed, items_found, error_message)
news_items: 12 columns (id, run_id, insurer_id, title, description, source_url,
                       source_name, published_at, status, sentiment, summary, created_at)
Foreign keys: news_items.run_id → runs.id, news_items.insurer_id → insurers.id
```

✅ **Relationship Verification:**
- Bidirectional relationships defined
- SQLAlchemy metadata registered
- Foreign key constraints created in SQLite

### Not Yet Tested

❌ **End-to-End Workflow:**
- Creating runs and news items via API endpoints (no endpoints yet)
- Classification field updates (no classification service yet)
- Relationship queries under load
- Cascade delete behavior

**Reason:** This plan focuses on model definition. API endpoints and services will be tested in subsequent plans.

## Files Changed

### Created (4 files)

| File | Lines | Purpose |
|------|-------|---------|
| `app/models/run.py` | 37 | Run ORM model with status tracking |
| `app/models/news_item.py` | 47 | NewsItem ORM model with foreign keys |
| `app/schemas/run.py` | 47 | Run Pydantic schemas and enums |
| `app/schemas/news.py` | 62 | NewsItem Pydantic schemas and enums |

### Modified (4 files)

| File | Changes | Purpose |
|------|---------|---------|
| `app/models/__init__.py` | +4 lines | Export Run and NewsItem |
| `app/models/insurer.py` | +3 lines | Add news_items relationship |
| `app/schemas/__init__.py` | +18 lines | Export new schemas and enums |
| `app/main.py` | +1 line | Import models for table registration |

### Total Impact

- **Lines added:** ~213
- **New models:** 2 (Run, NewsItem)
- **New schemas:** 6 (RunCreate, RunRead, NewsItemCreate, NewsItemRead, NewsItemWithClassification, plus 4 enums)
- **New relationships:** 3 (Run.news_items, NewsItem.run, Insurer.news_items)

## Deviations from Plan

None - plan executed exactly as written.

All tasks completed as specified:
1. ✅ Task 1: Run model created with all required fields and relationship
2. ✅ Task 2: NewsItem model created with foreign keys and bidirectional relationships
3. ✅ Task 3: Pydantic schemas created with enums and validation

## Next Phase Readiness

### Immediate Next Steps (Plan 02-02)

**Configuration Management Ready:**
- Models are ready to be referenced in Settings configuration
- Azure OpenAI API key storage needed for classification
- Apify API token storage needed for scraping

### Pipeline Dependencies

**For Scraper Service (Plan 02-03):**
- ✅ Run model available for execution tracking
- ✅ NewsItem model ready for news storage
- ✅ Foreign key relationships configured
- ⏳ API endpoints needed for creating runs and news items

**For Classifier Service (Plan 02-04):**
- ✅ NewsItem classification fields available (status, sentiment, summary)
- ✅ InsurerStatus and Sentiment enums defined
- ⏳ Azure OpenAI API configuration needed

**For Report Service (Plan 02-05):**
- ✅ NewsItem queries can join to Insurer and Run
- ✅ Classification data structure defined
- ⏳ Report generation logic needed

### Outstanding Items

None. All Phase 02 Plan 01 deliverables complete.

### Blockers/Concerns

None identified.

---

**Commits:**

- `97d9790`: feat(02-01): add Run model for tracking scraping runs
- `e25d5b2`: feat(02-01): add NewsItem model with foreign keys
- `699aee0`: feat(02-01): add Pydantic schemas for Run and NewsItem
- `00178c0`: feat(02-01): register new models for table creation

**Duration:** ~2.5 minutes
**Completed:** 2026-02-04
