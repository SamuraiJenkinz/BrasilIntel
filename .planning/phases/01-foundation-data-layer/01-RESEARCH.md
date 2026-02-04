# Phase 1: Foundation & Data Layer - Research

**Researched:** 2026-02-04
**Domain:** FastAPI + SQLAlchemy + SQLite + pandas/Excel
**Confidence:** HIGH

## Summary

This research covers implementing a data management layer for 897 Brazilian health insurers using FastAPI, SQLAlchemy with SQLite, Pydantic v2 validation, and pandas/openpyxl for Excel integration. The standard approach combines FastAPI's APIRouter pattern for modular organization, SQLAlchemy 2.x ORM with proper transaction handling, Pydantic v2 field validators for data validation, and pandas with openpyxl for Excel parsing and generation.

The critical technical considerations include: (1) SQLite's unique transaction mode requiring `autocommit=False` for Python 3.12+, (2) FastAPI's dependency injection with yield for session management and transaction control, (3) Pydantic v2's annotated pattern for reusable validators, and (4) pandas' openpyxl engine for modern .xlsx file handling with proper missing data management.

**Primary recommendation:** Use FastAPI's router-based modular structure with dependency-injected SQLAlchemy sessions, implement preview-before-commit via two-endpoint pattern (preview + commit), and leverage Pydantic v2 validators for field-level validation before database operations.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115+ | Web framework | Modern async framework with automatic OpenAPI docs, type safety, and Pydantic integration |
| SQLAlchemy | 2.0+ | ORM/database toolkit | Industry standard with mature ORM, query builder, and migration support via Alembic |
| Pydantic | 2.x | Data validation | Built into FastAPI, 5-50x faster than v1, type-safe validation with Rust core |
| pandas | 2.3+ | Excel parsing | De facto standard for tabular data with excellent Excel integration |
| openpyxl | 3.1+ | Excel engine | Default pandas engine for .xlsx files, full feature support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Jinja2 | 3.x | HTML templates | Admin UI rendering if not using frontend framework |
| fastapi-pagination | 0.15.9+ | Pagination utility | Search/filter results with large datasets (optional but recommended) |
| Alembic | 1.x | Database migrations | Schema versioning and evolution (recommended for production) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| openpyxl | xlsxwriter | xlsxwriter is write-only but faster for generation; openpyxl does read+write |
| pandas | openpyxl directly | Direct openpyxl gives more control but loses pandas' data manipulation capabilities |
| SQLAlchemy | Raw SQL | Raw SQL is simpler but loses type safety, migrations, and cross-database compatibility |

**Installation:**
```bash
pip install fastapi[standard] sqlalchemy pydantic pandas openpyxl jinja2
# Optional but recommended:
pip install alembic fastapi-pagination
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── main.py                 # FastAPI app initialization and router inclusion
├── database.py             # Database engine, SessionLocal, Base
├── dependencies.py         # Shared dependencies (get_db session)
├── models/
│   └── insurer.py         # SQLAlchemy ORM models
├── schemas/
│   └── insurer.py         # Pydantic models for request/response
├── routers/
│   └── insurers.py        # Insurer CRUD endpoints
├── services/
│   └── excel_service.py   # Excel parsing/generation logic
└── templates/             # Jinja2 templates for admin UI
    └── insurers.html
```

### Pattern 1: Database Session Dependency
**What:** Dependency injection for SQLAlchemy session management with automatic cleanup
**When to use:** Every database-accessing endpoint
**Example:**
```python
# Source: https://fastapi.tiangolo.com/tutorial/sql-databases/
# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./insurers.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "autocommit": False}  # SQLite specific
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# app/dependencies.py
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/routers/insurers.py
from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from ..dependencies import get_db

router = APIRouter(prefix="/insurers", tags=["insurers"])

@router.get("/")
def list_insurers(db: Session = Depends(get_db)):
    return db.query(Insurer).all()
```

### Pattern 2: Pydantic v2 Field Validators (Annotated Pattern)
**What:** Reusable validators using type annotations for ANS code and required fields
**When to use:** Cross-cutting validation rules that apply to multiple schemas
**Example:**
```python
# Source: https://docs.pydantic.dev/latest/concepts/validators/
from typing import Annotated
from pydantic import BaseModel, AfterValidator, field_validator

def validate_ans_code(value: str) -> str:
    """ANS codes must be numeric and 6 digits"""
    if not value.isdigit() or len(value) != 6:
        raise ValueError("ANS code must be 6 digits")
    return value

ANSCode = Annotated[str, AfterValidator(validate_ans_code)]

class InsurerCreate(BaseModel):
    ans_code: ANSCode
    name: str
    cnpj: str | None = None
    category: str  # Required: Health, Dental, or Group Life

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {'Health', 'Dental', 'Group Life'}
        if v not in allowed:
            raise ValueError(f"Category must be one of {allowed}")
        return v
```

### Pattern 3: Preview-Before-Commit Workflow
**What:** Two-endpoint pattern for import preview and commit using session state
**When to use:** Bulk operations where users need to review changes before applying
**Example:**
```python
# Source: Community pattern from FastAPI discussions
# app/routers/insurers.py
from fastapi import UploadFile, Depends, HTTPException
from typing import Dict, Any
import uuid

# In-memory storage for preview sessions (use Redis for production)
preview_sessions: Dict[str, list] = {}

@router.post("/import/preview")
async def preview_import(file: UploadFile, db: Session = Depends(get_db)):
    """Parse Excel and validate, return preview without committing"""
    # Parse Excel
    df = pd.read_excel(file.file, engine='openpyxl')

    # Validate all rows
    validated = []
    errors = []
    for idx, row in df.iterrows():
        try:
            insurer_data = InsurerCreate(
                ans_code=str(row['ANS Code']),
                name=row['Insurer Name'],
                category=row['Product']
            )
            validated.append(insurer_data.model_dump())
        except Exception as e:
            errors.append({"row": idx + 2, "error": str(e)})

    # Check for duplicates in DB
    existing_codes = {r[0] for r in db.query(Insurer.ans_code).all()}
    duplicates = [v for v in validated if v['ans_code'] in existing_codes]

    # Store preview session
    session_id = str(uuid.uuid4())
    preview_sessions[session_id] = validated

    return {
        "session_id": session_id,
        "total_rows": len(validated),
        "errors": errors,
        "duplicates": duplicates,
        "preview": validated[:10]  # First 10 for display
    }

@router.post("/import/commit/{session_id}")
async def commit_import(session_id: str, db: Session = Depends(get_db)):
    """Commit previewed import to database"""
    if session_id not in preview_sessions:
        raise HTTPException(status_code=404, detail="Preview session not found")

    validated_data = preview_sessions[session_id]

    try:
        # Bulk insert
        insurers = [Insurer(**data) for data in validated_data]
        db.bulk_save_objects(insurers)
        db.commit()

        # Clean up session
        del preview_sessions[session_id]

        return {"imported": len(insurers)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
```

### Pattern 4: Search and Filter with SQLAlchemy
**What:** Dynamic query building with filter chaining
**When to use:** Search endpoints with multiple optional filters
**Example:**
```python
# Source: SQLAlchemy 2.x documentation patterns
from sqlalchemy import or_

@router.get("/search")
def search_insurers(
    query: str | None = None,
    category: str | None = None,
    enabled: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Search insurers with optional filters"""
    stmt = db.query(Insurer)

    # Text search on name and ANS code
    if query:
        stmt = stmt.filter(
            or_(
                Insurer.name.ilike(f"%{query}%"),
                Insurer.ans_code.contains(query)
            )
        )

    # Category filter
    if category:
        stmt = stmt.filter(Insurer.category == category)

    # Enabled filter
    if enabled is not None:
        stmt = stmt.filter(Insurer.enabled == enabled)

    # Pagination
    total = stmt.count()
    results = stmt.offset(skip).limit(limit).all()

    return {"total": total, "results": results}
```

### Pattern 5: Excel Export with pandas
**What:** Generate Excel file from database query with proper column mapping
**When to use:** Export/download functionality
**Example:**
```python
# Source: pandas documentation
from fastapi.responses import StreamingResponse
import io

@router.get("/export")
def export_insurers(db: Session = Depends(get_db)):
    """Export all insurers to Excel matching source format"""
    insurers = db.query(Insurer).all()

    # Convert to DataFrame with column mapping
    df = pd.DataFrame([
        {
            'ANS Code': ins.ans_code,
            'Insurer Name': ins.name,
            'Company Registration Number': ins.cnpj,
            'Product': ins.category,
            'MARKET MASTER': ins.market_master
        }
        for ins in insurers
    ])

    # Write to bytes buffer
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Insurers')
    output.seek(0)

    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=insurers.xlsx'}
    )
```

### Anti-Patterns to Avoid
- **Opening DB connections per request:** Use dependency injection with SessionLocal, not new engine per endpoint
- **Synchronous DB calls in async endpoints:** Either use async SQLAlchemy or sync endpoints with `def` not `async def`
- **Committing in dependencies yield cleanup:** Transaction state cannot change response; commit explicitly in endpoint
- **Ignoring SQLite check_same_thread:** Must set `check_same_thread=False` for FastAPI multi-threaded access
- **Not validating before DB operations:** Pydantic validation should happen before attempting INSERT/UPDATE
- **Hardcoded SQL strings:** Use SQLAlchemy query builder for type safety and SQL injection prevention

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination logic | Manual offset/limit calculation with page numbers | fastapi-pagination library | Handles edge cases, multiple pagination styles, consistent response format |
| Excel file validation | Custom row-by-row parsing loops | pandas + Pydantic schemas | pandas handles missing data, Pydantic validates types and constraints |
| Unique constraint errors | String parsing of error messages | SQLAlchemy IntegrityError with try/except | Database-agnostic, cleaner error handling, explicit rollback |
| Database migrations | Manual CREATE TABLE/ALTER scripts | Alembic migration system | Version control for schema, rollback capability, team collaboration |
| API documentation | Writing OpenAPI spec by hand | FastAPI automatic docs generation | Type hints generate accurate docs, interactive testing UI included |
| Input sanitization | Regex validation and strip/clean functions | Pydantic field validators and str constraints | Comprehensive validation, better error messages, type coercion |

**Key insight:** The Python data ecosystem has mature solutions for these problems. Custom implementations often miss edge cases (timezone handling, encoding issues, NULL vs empty string, transaction rollback cleanup) that these libraries handle robustly.

## Common Pitfalls

### Pitfall 1: SQLite Legacy Transaction Mode
**What goes wrong:** Database changes commit immediately even when you expect them to be rolled back on error. SELECT statements are not repeatable within a transaction.
**Why it happens:** SQLite's default "legacy transaction mode" doesn't follow PEP 249 standards. Python's sqlite3 driver doesn't automatically BEGIN transactions for SELECT or DDL statements.
**How to avoid:** For Python 3.12+, explicitly set `autocommit=False` in engine connection args:
```python
engine = create_engine(
    "sqlite:///./db.sqlite",
    connect_args={"autocommit": False, "check_same_thread": False}
)
```
**Warning signs:** Tests pass but production behavior differs. Concurrent requests see uncommitted data. ROLLBACK doesn't undo changes.

### Pitfall 2: pandas read_excel Missing Data Handling
**What goes wrong:** Excel cells with blank values, "NA", "null", etc. are inconsistently parsed. Some become NaN, others become strings, causing Pydantic validation failures.
**Why it happens:** pandas recognizes some missing value forms by default (blank, 'NA', 'null', 'nan') but not others ('?', 'N/A', 'Nil', empty string).
**How to avoid:** Explicitly define missing value indicators and provide default values:
```python
df = pd.read_excel(
    file,
    engine='openpyxl',
    na_values=['', 'NA', 'N/A', 'null', 'Nil', '?'],  # All forms to treat as missing
    keep_default_na=True  # Also keep pandas' defaults
)
# Fill missing values before validation
df = df.fillna({'cnpj': '', 'market_master': ''})
```
**Warning signs:** Validation errors like "expected str, got float" or "NaN is not a valid string". Inconsistent parsing between Excel files.

### Pitfall 3: Unique Constraint Violations Without Proper Error Handling
**What goes wrong:** Duplicate ANS codes cause cryptic IntegrityError exceptions with SQLite-specific error messages. Application crashes instead of showing user-friendly validation errors.
**Why it happens:** SQLAlchemy raises generic IntegrityError; the specific constraint violated is only in the error message string, which varies by database.
**How to avoid:** Catch IntegrityError and parse the error message:
```python
from sqlalchemy.exc import IntegrityError

try:
    db.add(new_insurer)
    db.commit()
except IntegrityError as e:
    db.rollback()
    error_msg = str(e.orig).lower()
    if 'unique' in error_msg and 'ans_code' in error_msg:
        raise HTTPException(
            status_code=400,
            detail=f"ANS Code {new_insurer.ans_code} already exists"
        )
    raise HTTPException(status_code=500, detail="Database constraint violation")
```
**Warning signs:** Generic "500 Internal Server Error" for duplicate entries. Users don't know what went wrong. No rollback, leaving session in inconsistent state.

### Pitfall 4: FastAPI Dependency with yield Cannot Change Response
**What goes wrong:** Attempting to commit/rollback in the dependency's finally block after yield, but exceptions during commit can't change the HTTP response since it's already been determined.
**Why it happens:** FastAPI dependencies with yield run cleanup code after the endpoint returns. By then, the response status and body are already set.
**How to avoid:** Commit explicitly in the endpoint function, not in the dependency:
```python
# WRONG - commit in dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Too late to handle errors!
    except:
        db.rollback()
    finally:
        db.close()

# RIGHT - commit in endpoint
@router.post("/insurers")
def create_insurer(data: InsurerCreate, db: Session = Depends(get_db)):
    try:
        insurer = Insurer(**data.model_dump())
        db.add(insurer)
        db.commit()
        db.refresh(insurer)
        return insurer
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate ANS code")
```
**Warning signs:** Successful responses (200 OK) even though database changes failed. Inconsistent state between database and API responses.

### Pitfall 5: Pydantic v2 Migration - Using Config Instead of model_config
**What goes wrong:** Defining validation configuration with `class Config` (Pydantic v1 syntax) in Pydantic v2 models causes warnings or failures.
**Why it happens:** Pydantic v2 changed configuration from nested `Config` class to `model_config` dictionary attribute.
**How to avoid:** Use Pydantic v2 syntax:
```python
# WRONG - Pydantic v1 style
class InsurerBase(BaseModel):
    class Config:
        orm_mode = True

# RIGHT - Pydantic v2 style
from pydantic import ConfigDict

class InsurerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```
**Warning signs:** Deprecation warnings about `orm_mode`. Configuration not being applied. Pydantic version mismatches.

### Pitfall 6: Excel Column Name Variations
**What goes wrong:** Excel parsing fails because column names have extra spaces, different capitalization, or the user modified the template.
**Why it happens:** pandas column matching is case-sensitive and whitespace-sensitive. Users often edit Excel headers.
**How to avoid:** Normalize column names and use flexible mapping:
```python
df = pd.read_excel(file, engine='openpyxl')
# Normalize: strip whitespace, lowercase, remove special chars
df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

# Flexible column mapping
COLUMN_MAP = {
    'ans_code': ['ans_code', 'anscode', 'ans', 'code'],
    'name': ['insurer_name', 'name', 'company_name'],
    'category': ['product', 'category', 'type']
}

for standard_name, variants in COLUMN_MAP.items():
    for variant in variants:
        if variant in df.columns:
            df.rename(columns={variant: standard_name}, inplace=True)
            break
```
**Warning signs:** KeyError for column names that "obviously" exist in the Excel file. Works with your test file but fails with user uploads.

## Code Examples

Verified patterns from official sources:

### SQLAlchemy Model Definition
```python
# Source: https://docs.sqlalchemy.org/en/21/dialects/sqlite.html
from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint
from .database import Base

class Insurer(Base):
    __tablename__ = "insurers"

    id = Column(Integer, primary_key=True, index=True)
    ans_code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    cnpj = Column(String(18), nullable=True)
    category = Column(String(50), nullable=False)  # Health, Dental, Group Life
    market_master = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint('ans_code', name='uix_ans_code'),
    )
```

### Pydantic Schema Hierarchy
```python
# Source: https://docs.pydantic.dev/latest/concepts/models/
from pydantic import BaseModel, ConfigDict, Field

class InsurerBase(BaseModel):
    """Shared fields for all schemas"""
    ans_code: str = Field(..., min_length=6, max_length=6, pattern=r'^\d{6}$')
    name: str = Field(..., min_length=1, max_length=255)
    cnpj: str | None = Field(None, max_length=18)
    category: str = Field(..., pattern=r'^(Health|Dental|Group Life)$')
    market_master: str | None = None
    status: str | None = None

class InsurerCreate(InsurerBase):
    """Schema for creating new insurer"""
    enabled: bool = True

class InsurerUpdate(BaseModel):
    """Schema for partial updates"""
    name: str | None = None
    enabled: bool | None = None

class InsurerResponse(InsurerBase):
    """Schema for API responses"""
    id: int
    enabled: bool

    model_config = ConfigDict(from_attributes=True)
```

### Router Organization with Prefix and Tags
```python
# Source: https://fastapi.tiangolo.com/tutorial/bigger-applications/
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List
from ..dependencies import get_db
from ..schemas.insurer import InsurerCreate, InsurerResponse
from ..models.insurer import Insurer

router = APIRouter(
    prefix="/api/insurers",
    tags=["insurers"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[InsurerResponse])
def list_insurers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    insurers = db.query(Insurer).offset(skip).limit(limit).all()
    return insurers

@router.get("/{ans_code}", response_model=InsurerResponse)
def get_insurer(ans_code: str, db: Session = Depends(get_db)):
    insurer = db.query(Insurer).filter(Insurer.ans_code == ans_code).first()
    if not insurer:
        raise HTTPException(status_code=404, detail="Insurer not found")
    return insurer
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `class Config` | Pydantic v2 `model_config = ConfigDict()` | Pydantic 2.0 (2023) | Breaking change; must update all models |
| SQLAlchemy 1.4 `declarative_base()` | SQLAlchemy 2.0 `DeclarativeBase` class | SQLAlchemy 2.0 (2023) | Preferred pattern; old still works |
| pandas `xlrd` engine | pandas `openpyxl` engine | xlrd 2.0 (2020) | xlrd dropped .xlsx support; openpyxl is now default |
| Manual pagination | `fastapi-pagination` library | Library matured 2024-2025 | Standardized pagination patterns |
| FastAPI `orm_mode=True` | FastAPI `from_attributes=True` | Pydantic 2.0 (2023) | Renamed for clarity; same functionality |

**Deprecated/outdated:**
- **xlrd for .xlsx files**: xlrd 2.0+ only supports .xls (legacy Excel format); use openpyxl for modern .xlsx files
- **SQLAlchemy 1.x query API**: Still works but `session.execute(select(...))` is preferred in 2.x
- **Pydantic v1 validators**: `@validator` decorator replaced by `@field_validator` in v2

## Open Questions

Things that couldn't be fully resolved:

1. **Preview session storage strategy for production**
   - What we know: In-memory dict works for development but won't scale or survive restarts
   - What's unclear: Whether to use Redis, database table, or file system for preview sessions
   - Recommendation: Use Redis with TTL for production (fast, scales, automatic cleanup). For MVP, in-memory dict is acceptable with warning to users about session expiry.

2. **Optimal batch size for bulk imports**
   - What we know: SQLAlchemy `bulk_save_objects()` is faster than individual commits; 897 rows is small
   - What's unclear: Whether to chunk large imports or handle all 897 at once
   - Recommendation: For this dataset size, bulk insert all at once. If dataset grows >10K rows, implement chunking with progress tracking.

3. **Excel template validation strictness**
   - What we know: Column name variations are common; normalization helps but isn't perfect
   - What's unclear: Whether to enforce exact column names or support multiple variants
   - Recommendation: Support common variants via COLUMN_MAP but provide downloadable template with canonical names. Show clear error if required columns not found.

## Sources

### Primary (HIGH confidence)
- [FastAPI Official Docs - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) - Project structure patterns
- [FastAPI Official Docs - SQL Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/) - SQLAlchemy integration
- [SQLAlchemy 2.1 Docs - SQLite](https://docs.sqlalchemy.org/en/21/dialects/sqlite.html) - SQLite-specific configuration
- [Pydantic Docs - Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Pydantic v2 validation patterns
- [Pydantic Docs - Models](https://docs.pydantic.dev/latest/concepts/models/) - Model configuration
- [pandas Docs - read_excel](https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html) - Excel parsing API

### Secondary (MEDIUM confidence)
- [FastAPI Best Practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices) - Community-vetted patterns
- [Medium: FastAPI Project Structure 2026](https://medium.com/@devsumitg/the-perfect-structure-for-a-large-production-ready-fastapi-app-78c55271d15c) - Production structure examples
- [Medium: Pydantic v2 Best Practices](https://medium.com/algomart/working-with-pydantic-v2-the-best-practices-i-wish-i-had-known-earlier-83da3aa4d17a) - Pydantic v2 migration guide
- [Medium: 10 Common FastAPI Mistakes](https://medium.com/@connect.hashblock/10-common-fastapi-mistakes-that-hurt-performance-and-how-to-fix-them-72b8553fe8e7) - Performance pitfalls
- [FastAPI GitHub Discussions #8949](https://github.com/fastapi/fastapi/discussions/8949) - Transaction commit/rollback patterns
- [Medium: Database Session Patterns](https://medium.com/@upesh.jindal/database-session-as-a-dependency-and-commit-rollback-pattern-f5533b2667e0) - Session management

### Tertiary (LOW confidence)
- [fastapi-pagination PyPI](https://pypi.org/project/fastapi-pagination/) - Pagination library (verify version compatibility in implementation)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/) - Excel library details (verify pandas integration patterns)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and PyPI current versions
- Architecture: HIGH - Patterns sourced from FastAPI official documentation and SQLAlchemy docs
- Pitfalls: HIGH - Verified via official docs warnings and recent 2026 community articles

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days for stable technologies)

---

**Notes for planner:**
- SQLite configuration (`autocommit=False`, `check_same_thread=False`) is critical and non-negotiable
- Preview-before-commit pattern requires two endpoints and session storage mechanism
- Pydantic v2 validation should happen before any database operations
- All Excel operations should handle missing data explicitly
- Transaction management: commit in endpoint, not in dependency cleanup
