# BrasilIntel

Automated competitive intelligence system for monitoring Brazilian insurers.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-proprietary-red.svg)]()

---

## Overview

BrasilIntel monitors **897 Brazilian insurers** across three product categories, automatically collecting news, classifying risk status using AI, and delivering professional daily intelligence reports.

### Categories

| Category | Insurers | Schedule (São Paulo) |
|----------|----------|---------------------|
| Health (Saúde) | 515 | 6:00 AM |
| Dental (Odontológico) | 237 | 7:00 AM |
| Group Life (Vida em Grupo) | 145 | 8:00 AM |

### Features

- **Automated News Collection** - Scrapes 6 sources (Google News, Valor Econômico, InfoMoney, CQCS, ANS, Estadão)
- **AI Classification** - Azure OpenAI classifies insurer status (Critical, Watch, Monitor, Stable)
- **Professional Reports** - Marsh-branded HTML reports with PDF attachments
- **Email Delivery** - Automated daily delivery via Microsoft Graph API
- **Critical Alerts** - Immediate notifications for critical status detection
- **Admin Dashboard** - Web interface for managing insurers, schedules, and reports

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/mmctech/BrasilIntel.git
cd BrasilIntel

# Setup Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt

# Configure
copy .env.example .env
# Edit .env with your API keys

# Run
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/admin/** to access the dashboard.

See [Quickstart Guide](docs/QUICKSTART.md) for detailed setup instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [Quickstart Guide](docs/QUICKSTART.md) | Get running in 5 minutes |
| [User Guide](docs/USER_GUIDE.md) | Complete feature documentation |
| [Deployment Guide](docs/DEPLOYMENT.md) | Production deployment options |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      BrasilIntel                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Scraper   │  │  Classifier │  │   Report    │         │
│  │   Service   │  │   Service   │  │  Generator  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────────────────────────────────────────┐       │
│  │              Orchestration Layer                 │       │
│  │         (APScheduler + FastAPI)                  │       │
│  └─────────────────────────────────────────────────┘       │
│         │                │                │                 │
│         ▼                ▼                ▼                 │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐           │
│  │  SQLite   │    │   Azure   │    │ Microsoft │           │
│  │    DB     │    │  OpenAI   │    │   Graph   │           │
│  └───────────┘    └───────────┘    └───────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Database**: SQLite
- **AI**: Azure OpenAI (GPT-4o)
- **Email**: Microsoft Graph API
- **Scraping**: Apify SDK
- **PDF**: WeasyPrint
- **Scheduler**: APScheduler
- **Frontend**: HTMX, Jinja2 Templates

---

## Configuration

Create a `.env` file with the following required settings:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Microsoft Graph (Email)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=sender@company.com

# Apify (Web Scraping)
APIFY_TOKEN=your-apify-token

# Admin Interface
ADMIN_PASSWORD=your-secure-password

# Report Recipients
REPORT_RECIPIENTS_HEALTH=user1@company.com,user2@company.com
REPORT_RECIPIENTS_DENTAL=dental@company.com
REPORT_RECIPIENTS_GROUP_LIFE=life@company.com
```

See [Deployment Guide](docs/DEPLOYMENT.md) for complete configuration reference.

---

## Deployment Options

### Docker

```bash
docker-compose build
docker-compose up -d
```

### Windows Server (Production)

```powershell
# Setup scheduled tasks
.\deploy\setup_scheduled_task.ps1

# Check status
.\deploy\manage_service.ps1 -Action status
```

See [Deployment Guide](docs/DEPLOYMENT.md) for detailed instructions.

---

## API

Interactive API documentation available at `/docs` when the server is running.

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| GET | `/api/insurers` | List all insurers |
| POST | `/api/runs/execute/category` | Execute category run |
| GET | `/api/reports/archive` | List archived reports |
| GET | `/api/schedules` | List schedules |

---

## Project Structure

```
BrasilIntel/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Business logic
│   │   ├── scraper/      # News collection
│   │   ├── classifier/   # AI classification
│   │   └── report/       # Report generation
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Service layer
│   ├── storage/          # File storage
│   └── templates/        # Jinja2 templates
├── deploy/               # Deployment scripts
├── docs/                 # Documentation
├── data/                 # Database and logs
└── tests/                # Test suite
```

---

## License

Proprietary - Marsh Brasil

---

## Support

For issues and support, contact the development team.

---

*BrasilIntel v1.0*
