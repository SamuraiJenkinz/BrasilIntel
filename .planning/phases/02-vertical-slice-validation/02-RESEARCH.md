# Phase 2: Vertical Slice Validation - Research

**Researched:** 2026-02-04
**Domain:** Apify SDK + Azure OpenAI + Microsoft Graph API + Docker + Windows Scheduled Task
**Confidence:** HIGH

## Summary

This research covers implementing an end-to-end vertical slice for BrasilIntel: scraping Google News via Apify, classifying insurer status and summarizing news via Azure OpenAI structured outputs, sending reports via Microsoft Graph API email, and deploying via Docker and Windows Scheduled Task. The standard approach combines Apify's Python client for actor-based scraping, Azure OpenAI's structured outputs with Pydantic models for reliable classification, Microsoft Graph SDK for enterprise email delivery, and FastAPI containerization patterns for cross-platform deployment.

Critical technical considerations include: (1) Apify actors return news metadata but require proper rate limiting for 897+ insurers, (2) Azure OpenAI structured outputs with Pydantic ensure consistent classification responses, (3) Microsoft Graph requires Azure AD app registration with Mail.Send permission for daemon email sending, and (4) Windows Scheduled Task deployment requires batch file wrapper with venv activation.

**Primary recommendation:** Implement a minimal vertical slice with one insurer, one news source (Google News), basic classification (4 status levels), simple HTML report template, and Graph API email delivery. Validate end-to-end before scaling.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| apify-client | 1.8+ | Web scraping orchestration | Official Apify SDK with actor management, async support, and automatic retries |
| openai | 1.42+ | Azure OpenAI integration | Official SDK with AzureOpenAI client and structured output support |
| msgraph-sdk | 1.x | Microsoft Graph API | Official Microsoft SDK for email, calendar, and M365 services |
| azure-identity | 1.x | Azure authentication | Official Azure SDK for DefaultAzureCredential and token providers |
| pydantic | 2.8+ | Structured outputs | Required for Azure OpenAI structured output parsing |
| jinja2 | 3.x | HTML report templates | Standard Python templating for report generation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | 1.x | Environment loading | Load .env file for configuration |
| httpx | 0.27+ | HTTP client | Async HTTP requests if needed beyond SDK |
| uvicorn | 0.30+ | ASGI server | FastAPI production server |
| structlog | 24.x | Structured logging | Production logging with JSON output |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Apify | Direct requests/BeautifulSoup | Apify handles rate limiting, proxies, and retries; direct scraping requires more infrastructure |
| msgraph-sdk | requests + Graph REST API | SDK provides type safety and handles auth; raw REST is more flexible but more error-prone |
| Jinja2 | HTML string formatting | Jinja2 provides inheritance, filters, escaping; string formatting is simpler but harder to maintain |

**Installation:**
```bash
pip install apify-client openai msgraph-sdk azure-identity pydantic python-dotenv jinja2 structlog
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── main.py                    # FastAPI app with lifespan, routers, health check
├── database.py                # SQLite engine, SessionLocal, Base (from Phase 1)
├── dependencies.py            # get_db dependency (from Phase 1)
├── config.py                  # Settings class with env loading
├── models/
│   ├── insurer.py            # Insurer ORM (from Phase 1)
│   ├── news_item.py          # News item ORM model
│   └── run.py                # Run tracking ORM model
├── schemas/
│   ├── insurer.py            # Insurer schemas (from Phase 1)
│   ├── news.py               # News item schemas
│   └── classification.py     # Azure OpenAI response schemas
├── services/
│   ├── scraper.py            # Apify client wrapper
│   ├── classifier.py         # Azure OpenAI classification service
│   ├── reporter.py           # HTML report generator
│   └── emailer.py            # Microsoft Graph email service
├── routers/
│   ├── insurers.py           # Insurer CRUD (from Phase 1)
│   ├── runs.py               # Run management endpoints
│   └── reports.py            # Report generation endpoints
└── templates/
    └── report_basic.html     # Basic HTML report template
```

### Pattern 1: Apify Client Wrapper
**What:** Service class wrapping Apify client with async actor execution and result retrieval
**When to use:** All Google News scraping operations
**Example:**
```python
# Source: https://docs.apify.com/api/client/python/docs/examples/passing-input-to-actor
from apify_client import ApifyClient
from typing import List, Dict, Any
import os

class ApifyScraperService:
    def __init__(self):
        self.client = ApifyClient(os.getenv("APIFY_TOKEN"))
        # Google News scraper actor - multiple available on Apify Store
        self.google_news_actor = "lhotanova/google-news-scraper"

    def search_google_news(
        self,
        query: str,
        language: str = "pt",  # Portuguese
        country: str = "BR",   # Brazil
        max_results: int = 10,
        time_filter: str = "7d"  # Last 7 days
    ) -> List[Dict[str, Any]]:
        """Search Google News for a query string."""
        run_input = {
            "queries": query,
            "language": language,
            "country": country,
            "maxItems": max_results,
            "timeRange": time_filter,
        }

        # Run actor and wait for completion
        run = self.client.actor(self.google_news_actor).call(
            run_input=run_input,
            timeout_secs=300  # 5 minute timeout
        )

        # Retrieve results from default dataset
        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())
        return items

    def search_insurer(self, insurer_name: str, ans_code: str) -> List[Dict[str, Any]]:
        """Search for news about a specific insurer using name + ANS code."""
        # Combine name and ANS code for better accuracy
        query = f'"{insurer_name}" OR "ANS {ans_code}"'
        return self.search_google_news(query)
```

### Pattern 2: Azure OpenAI Structured Output Classification
**What:** Classification service using Pydantic models for structured JSON responses
**When to use:** Classifying insurer status and generating news summaries
**Example:**
```python
# Source: https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from typing import List, Literal
from enum import Enum
import os

class InsurerStatus(str, Enum):
    CRITICAL = "Critical"
    WATCH = "Watch"
    MONITOR = "Monitor"
    STABLE = "Stable"

class NewsClassification(BaseModel):
    """Classification result for a news item."""
    status: Literal["Critical", "Watch", "Monitor", "Stable"] = Field(
        description="Insurer status based on news content"
    )
    summary_bullets: List[str] = Field(
        description="3-5 bullet points summarizing the news impact",
        min_length=1,
        max_length=5
    )
    sentiment: Literal["positive", "negative", "neutral"] = Field(
        description="Overall sentiment of the news"
    )
    reasoning: str = Field(
        description="Brief explanation of why this status was assigned"
    )

class ClassificationService:
    def __init__(self):
        # Azure OpenAI v1 API pattern (recommended for 2026+)
        self.client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-05-01-preview"
        )
        self.model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

    def classify_news(self, insurer_name: str, news_items: List[dict]) -> NewsClassification:
        """Classify insurer status based on aggregated news content."""

        # Format news for prompt
        news_text = "\n".join([
            f"- {item.get('title', 'No title')}: {item.get('description', '')}"
            for item in news_items
        ])

        system_prompt = """You are a financial analyst specializing in Brazilian insurance companies.
Analyze news items and classify the insurer's status.

Classification criteria:
- CRITICAL: Financial crisis, ANS intervention, bankruptcy risk, fraud, criminal charges
- WATCH: M&A activity, major leadership changes, regulatory actions, significant losses
- MONITOR: Rate changes, network changes, market expansion, partnership announcements
- STABLE: No significant news or only routine operational updates

Respond in Portuguese for the summary bullets."""

        user_prompt = f"""Analyze these news items about {insurer_name} and provide classification:

{news_text}

Provide your classification with bullet-point summary."""

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format=NewsClassification,
        )

        return completion.choices[0].message.parsed
```

### Pattern 3: Microsoft Graph Email Service
**What:** Service for sending HTML emails with Microsoft Graph API using daemon authentication
**When to use:** Sending daily reports and critical alerts
**Example:**
```python
# Source: https://learn.microsoft.com/en-us/graph/tutorials/python-email
from msgraph import GraphServiceClient
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import SendMailPostRequestBody
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from azure.identity import ClientSecretCredential
import os

class GraphEmailService:
    def __init__(self):
        # Daemon app authentication (no user interaction)
        credential = ClientSecretCredential(
            tenant_id=os.getenv("AZURE_TENANT_ID"),
            client_id=os.getenv("AZURE_CLIENT_ID"),
            client_secret=os.getenv("AZURE_CLIENT_SECRET")
        )
        self.client = GraphServiceClient(credential)
        self.sender_email = os.getenv("SENDER_EMAIL")

    async def send_report_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        cc_addresses: List[str] = None,
        bcc_addresses: List[str] = None
    ):
        """Send HTML email report via Microsoft Graph."""

        message = Message(
            subject=subject,
            body=ItemBody(
                content_type=BodyType.Html,
                content=html_body
            ),
            to_recipients=[
                Recipient(email_address=EmailAddress(address=addr))
                for addr in to_addresses
            ]
        )

        if cc_addresses:
            message.cc_recipients = [
                Recipient(email_address=EmailAddress(address=addr))
                for addr in cc_addresses
            ]

        if bcc_addresses:
            message.bcc_recipients = [
                Recipient(email_address=EmailAddress(address=addr))
                for addr in bcc_addresses
            ]

        request_body = SendMailPostRequestBody(
            message=message,
            save_to_sent_items=True
        )

        # Send from configured sender
        await self.client.users.by_user_id(self.sender_email).send_mail.post(request_body)
```

### Pattern 4: FastAPI Health Check with Dependencies
**What:** Health endpoint that checks database connectivity and external service status
**When to use:** Docker health checks and monitoring
**Example:**
```python
# Source: https://www.index.dev/blog/how-to-implement-health-check-in-python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies import get_db
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["Health"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Health check endpoint for monitoring and load balancer probes.

    Checks:
    - Application is running
    - Database is accessible
    - Essential environment variables are set
    """
    health = {
        "status": "healthy",
        "service": "brasilintel",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check database connectivity
    try:
        db.execute(text("SELECT 1"))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = f"error: {str(e)}"

    # Check required environment variables
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_TENANT_ID",
        "APIFY_TOKEN"
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        health["status"] = "degraded"
        health["checks"]["config"] = f"missing: {', '.join(missing)}"
    else:
        health["checks"]["config"] = "ok"

    return health
```

### Pattern 5: Dockerfile for FastAPI with SQLite
**What:** Multi-stage Dockerfile optimized for FastAPI with SQLite persistence
**When to use:** Docker deployment on Windows 11 and containers
**Example:**
```dockerfile
# Source: https://fastapi.tiangolo.com/deployment/docker/
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite and logs
RUN mkdir -p /app/data/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run with uvicorn in exec form for graceful shutdown
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Pattern 6: Windows Scheduled Task with PowerShell
**What:** PowerShell script for setting up Python application as Windows Scheduled Task
**When to use:** Production deployment on Windows Server
**Example:**
```powershell
# Source: Reference from refchyt/deploy/setup_scheduled_task.ps1
param(
    [string]$AppPath = "C:\BrasilIntel",
    [string]$TaskName = "BrasilIntel",
    [string]$Category = "health",  # health, dental, group_life
    [string]$StartTime = "06:00"
)

# Verify venv exists
if (-not (Test-Path "$AppPath\venv\Scripts\python.exe")) {
    Write-Host "ERROR: Virtual environment not found" -ForegroundColor Red
    exit 1
}

# Create batch script
$batchScript = @"
@echo off
cd /d $AppPath
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set LOGFILE=$AppPath\data\logs\run_%datetime:~0,8%_%datetime:~8,6%.log
call venv\Scripts\activate.bat
python -m app.main run --category $Category >> "%LOGFILE%" 2>&1
"@

$batchPath = "$AppPath\run_$Category.bat"
Set-Content -Path $batchPath -Value $batchScript

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At $StartTime
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "$TaskName-$Category" `
    -Action $action -Trigger $trigger -Principal $principal `
    -Description "BrasilIntel $Category report generation"
```

### Anti-Patterns to Avoid
- **Hardcoding API keys:** Use environment variables via python-dotenv, never commit secrets
- **Synchronous Apify calls in async endpoints:** Either use async client or run in thread pool
- **Missing error handling for Azure OpenAI:** Structured outputs can still timeout or fail; always wrap in try/except
- **Sending email without retry:** Graph API can have transient failures; implement exponential backoff
- **SQLite in container without volume:** Database will be lost on container restart; mount /app/data as volume
- **Using shell form in Dockerfile CMD:** Use exec form `CMD ["uvicorn", ...]` for proper signal handling

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| News scraping | Custom requests + BeautifulSoup | Apify actors | Rate limiting, proxies, retries, CAPTCHA handling built-in |
| JSON response parsing | String parsing of LLM output | Pydantic structured outputs | Guarantees schema conformance, automatic validation |
| Email sending | SMTP library | Microsoft Graph SDK | OAuth2 auth, enterprise compliance, better deliverability |
| Classification prompts | Ad-hoc string formatting | System/user message pattern | Consistent behavior, easier iteration, better results |
| Health checks | Manual endpoint | fastapi-health library | Standard patterns, dependency injection, extensible checks |
| Token refresh | Manual token management | azure-identity library | Handles token caching, refresh, and rotation automatically |

**Key insight:** This phase integrates multiple external services (Apify, Azure OpenAI, Microsoft Graph). Each has an official Python SDK with built-in error handling, auth management, and retry logic. Custom implementations would need to replicate all these features.

## Common Pitfalls

### Pitfall 1: Apify Rate Limiting and Timeouts
**What goes wrong:** Actor runs timeout or get rate limited when processing many insurers sequentially.
**Why it happens:** Google News actors have implicit rate limits. Processing 897 insurers sequentially overwhelms the actor.
**How to avoid:**
- Process in batches of 30-50 insurers
- Set appropriate `timeout_secs` (300-600 seconds)
- Check actor status before retrieving results
- Implement retry with exponential backoff
```python
# Good pattern: batch processing with progress tracking
for batch in chunked(insurers, batch_size=30):
    for insurer in batch:
        try:
            results = scraper.search_insurer(insurer.name, insurer.ans_code)
        except Exception as e:
            logger.error(f"Failed to scrape {insurer.name}: {e}")
            continue
    time.sleep(5)  # Pause between batches
```
**Warning signs:** Frequent timeouts, empty result sets, "Too many requests" errors.

### Pitfall 2: Azure OpenAI Structured Output Failures
**What goes wrong:** Parsing fails even with Pydantic schema because model doesn't always conform.
**Why it happens:** Edge cases in news content can confuse the model. Very short or missing content produces invalid responses.
**How to avoid:**
- Always wrap in try/except
- Provide fallback classification for failures
- Validate content length before classification
- Use temperature=0 for more deterministic outputs
```python
try:
    result = classifier.classify_news(insurer_name, news_items)
except Exception as e:
    logger.warning(f"Classification failed for {insurer_name}: {e}")
    result = NewsClassification(
        status="Monitor",
        summary_bullets=["Classification unavailable"],
        sentiment="neutral",
        reasoning="Automated classification failed"
    )
```
**Warning signs:** ValidationError exceptions, missing parsed content, inconsistent status assignments.

### Pitfall 3: Microsoft Graph Mail.Send Permission Issues
**What goes wrong:** 403 Forbidden when trying to send email via Graph API.
**Why it happens:** App registration missing Mail.Send application permission, or admin consent not granted.
**How to avoid:**
- Register app in Azure AD with Mail.Send application permission (not delegated)
- Grant admin consent for the permission
- Use ClientSecretCredential for daemon apps (no user interaction)
- Ensure sender email is a valid mailbox the app has permission to send from
```python
# Verify in Azure Portal:
# 1. App Registration -> API Permissions -> Microsoft Graph -> Mail.Send (Application)
# 2. Click "Grant admin consent for [tenant]"
```
**Warning signs:** 403 Forbidden, "Insufficient privileges", "Access denied".

### Pitfall 4: Docker Volume Permissions on Windows
**What goes wrong:** SQLite database writes fail in container on Windows Docker Desktop.
**Why it happens:** Windows and Linux have different permission models. Bind mounts can have permission issues.
**How to avoid:**
- Use named volumes instead of bind mounts for data persistence
- Set proper WORKDIR in Dockerfile
- Ensure data directory exists before write
```yaml
# docker-compose.yml
volumes:
  - brasilintel-data:/app/data  # Named volume, not bind mount

volumes:
  brasilintel-data:
```
**Warning signs:** "Permission denied" on database writes, "sqlite3.OperationalError: unable to open database file".

### Pitfall 5: Portuguese Content in Prompts
**What goes wrong:** Classification results are inconsistent or in wrong language for Portuguese news.
**Why it happens:** Model defaults to English output even with Portuguese input. Instructions unclear about language.
**How to avoid:**
- Explicitly request Portuguese output in system prompt
- Use Portuguese examples in few-shot prompts
- Validate that bullet points are in Portuguese
- Consider bilingual fallback for edge cases
```python
system_prompt = """Você é um analista financeiro especializado em seguradoras brasileiras.
Analise as notícias e classifique o status da seguradora.
Responda em português brasileiro."""
```
**Warning signs:** Mixed language outputs, English summaries for Portuguese news, inconsistent terminology.

### Pitfall 6: Windows Scheduled Task Environment Variables
**What goes wrong:** Scheduled task fails because environment variables aren't loaded.
**Why it happens:** Scheduled tasks run in SYSTEM context which doesn't have user environment variables.
**How to avoid:**
- Load .env file at application startup with python-dotenv
- Or set environment variables in the batch script
- Or store config in a config file alongside application
```batch
@echo off
cd /d C:\BrasilIntel
set AZURE_OPENAI_ENDPOINT=https://...
call venv\Scripts\activate.bat
python -m app.main
```
**Warning signs:** "Environment variable not found", empty configuration values, authentication failures in scheduled runs.

## Code Examples

Verified patterns from official sources:

### News Item Model
```python
# Source: SQLAlchemy 2.x documentation patterns
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class NewsItem(Base):
    """News item found during a scraping run."""
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    insurer_id = Column(Integer, ForeignKey("insurers.id"), nullable=False)

    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_name = Column(String(255), nullable=True)
    published_at = Column(DateTime, nullable=True)

    # Classification results
    status = Column(String(50), nullable=True)  # Critical, Watch, Monitor, Stable
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    summary = Column(Text, nullable=True)  # Bullet-point summary

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    insurer = relationship("Insurer", back_populates="news_items")
    run = relationship("Run", back_populates="news_items")
```

### Run Tracking Model
```python
# Source: Project requirements for run history tracking
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Run(Base):
    """Tracks individual scraping/classification runs."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)  # Health, Dental, Group Life
    trigger_type = Column(String(20), nullable=False)  # scheduled, manual
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    insurers_processed = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    news_items = relationship("NewsItem", back_populates="run")
```

### Basic HTML Report Template
```html
<!-- Source: Jinja2 patterns for email-compatible HTML -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .header { background: #003366; color: white; padding: 20px; }
        .status-critical { color: #dc3545; font-weight: bold; }
        .status-watch { color: #fd7e14; font-weight: bold; }
        .status-monitor { color: #ffc107; }
        .status-stable { color: #28a745; }
        .insurer-card { border: 1px solid #ddd; margin: 15px 0; padding: 15px; }
        .news-item { padding: 10px; border-left: 3px solid #ccc; margin: 10px 0; }
        ul { padding-left: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ company_name }} - {{ category }} Intelligence Report</h1>
        <p>{{ report_date }}</p>
        <p style="font-size: 12px;">CONFIDENTIAL</p>
    </div>

    <h2>Executive Summary</h2>
    <p>This report covers {{ insurers|length }} insurers in the {{ category }} category.</p>
    <ul>
        <li>Critical: {{ critical_count }}</li>
        <li>Watch: {{ watch_count }}</li>
        <li>Monitor: {{ monitor_count }}</li>
        <li>Stable: {{ stable_count }}</li>
    </ul>

    {% for insurer in insurers %}
    <div class="insurer-card">
        <h3>
            <span class="status-{{ insurer.status|lower }}">{{ insurer.status }}</span>
            {{ insurer.name }} (ANS: {{ insurer.ans_code }})
        </h3>

        {% for item in insurer.news_items %}
        <div class="news-item">
            <strong>{{ item.title }}</strong>
            <ul>
            {% for bullet in item.summary_bullets %}
                <li>{{ bullet }}</li>
            {% endfor %}
            </ul>
            <small>Source: {{ item.source_name }} | {{ item.published_at }}</small>
        </div>
        {% endfor %}
    </div>
    {% endfor %}

    <footer style="margin-top: 30px; font-size: 12px; color: #666;">
        Generated: {{ generated_at }} | BrasilIntel v0.1.0
    </footer>
</body>
</html>
```

### Configuration with Pydantic Settings
```python
# Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application configuration loaded from environment."""

    # Database
    database_url: str = "sqlite:///./data/brasilintel.db"

    # Azure OpenAI
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-05-01-preview"
    use_llm_summary: bool = True

    # Microsoft Graph
    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str
    sender_email: str

    # Apify
    apify_token: str

    # Application
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = "./data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `AzureOpenAI()` client | `OpenAI()` with base_url for v1 API | August 2025 | No more api-version parameter needed |
| JSON parsing of LLM output | Pydantic structured outputs | OpenAI 1.42.0 | Guaranteed schema conformance |
| SMTP for M365 email | Microsoft Graph SDK | Ongoing | Better auth, compliance, tracking |
| Requests for scraping | Apify SDK actors | Ongoing | Infrastructure managed, better reliability |
| Manual token refresh | azure-identity library | 2024+ | Automatic token lifecycle management |

**Deprecated/outdated:**
- **azure-openai package**: Use official `openai` package with AzureOpenAI client
- **EWS (Exchange Web Services)**: Deprecated in favor of Microsoft Graph API
- **Basic SMTP auth for M365**: Disabled by default; use OAuth2 or Graph API
- **api-version strings**: New v1 API doesn't require versioning

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal Apify actor selection**
   - What we know: Multiple Google News scrapers on Apify Store with different capabilities
   - What's unclear: Which actor best handles Portuguese/Brazilian news with rate limiting
   - Recommendation: Test `lhotanova/google-news-scraper` first; switch if issues arise

2. **Classification prompt tuning for Portuguese**
   - What we know: Azure OpenAI handles Portuguese well; structured outputs work
   - What's unclear: Optimal prompt structure for Brazilian insurance terminology
   - Recommendation: Start with provided prompt, iterate based on classification quality

3. **Graph API quotas for bulk email**
   - What we know: Graph API has rate limits per tenant
   - What's unclear: Exact limits for Mail.Send with HTML attachments
   - Recommendation: Implement exponential backoff; monitor for 429 responses

4. **Windows Server vs Docker deployment preference**
   - What we know: Both work; Docker is more portable, Task Scheduler is simpler
   - What's unclear: Customer IT preference and infrastructure constraints
   - Recommendation: Support both; Docker for dev, Task Scheduler for production

## Sources

### Primary (HIGH confidence)
- [Apify Python Client Documentation](https://docs.apify.com/api/client/python) - Actor execution patterns
- [Azure OpenAI Structured Outputs](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs) - Classification patterns
- [Microsoft Graph Python Email Tutorial](https://learn.microsoft.com/en-us/graph/tutorials/python-email) - Email sending
- [FastAPI Docker Documentation](https://fastapi.tiangolo.com/deployment/docker/) - Container patterns
- [OpenAI Python SDK](https://github.com/openai/openai-python) - AzureOpenAI client

### Secondary (MEDIUM confidence)
- [FastAPI Health Check Patterns](https://www.index.dev/blog/how-to-implement-health-check-in-python) - Health endpoint best practices
- [Apify Google News Scraper](https://apify.com/lhotanova/google-news-scraper) - Actor input schema
- [Azure OpenAI Switching Endpoints](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/switching-endpoints) - v1 API migration

### Tertiary (LOW confidence)
- Project reference files (refchyt/deploy/*.ps1) - Windows deployment patterns
- WebSearch results for Windows Scheduled Task Python patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified via official docs and PyPI
- Architecture: HIGH - Patterns from official documentation
- Pitfalls: MEDIUM - Combination of official docs and community patterns
- Portuguese prompt engineering: MEDIUM - Based on general Azure OpenAI capabilities, needs validation

**Research date:** 2026-02-04
**Valid until:** 2026-03-04 (30 days - APIs are stable but prompt patterns may need iteration)

---

**Notes for planner:**
- Vertical slice should focus on ONE insurer first to validate end-to-end
- Azure AD app registration is a prerequisite with Mail.Send application permission
- Docker deployment needs volume mount for SQLite persistence
- Windows Scheduled Task needs batch file wrapper for venv activation
- Health check endpoint exists from Phase 1 but needs enhancement for dependency checks
- Portuguese prompts should explicitly request Portuguese output
