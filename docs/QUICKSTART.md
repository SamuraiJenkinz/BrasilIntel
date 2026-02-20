# BrasilIntel Quickstart Guide

Get up and running in 5 minutes.

---

## 1. Prerequisites

- Python 3.11+
- Azure OpenAI API access
- Microsoft 365 (for email delivery)
- MMC Core API credentials (optional - for Factiva news and equity prices)

---

## 2. Install

```powershell
# Clone and setup
git clone https://github.com/SamuraiJenkinz/BrasilIntel.git
cd BrasilIntel

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Configure

```powershell
copy .env.example .env
notepad .env
```

**Required settings:**

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Email (Microsoft Graph)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=brasilintel@yourcompany.com

# Admin Login
ADMIN_PASSWORD=your-secure-password

# Report Recipients
REPORT_RECIPIENTS_HEALTH=user1@company.com,user2@company.com
REPORT_RECIPIENTS_DENTAL=dental-team@company.com
REPORT_RECIPIENTS_GROUP_LIFE=life-team@company.com
```

**Enterprise API (optional - for Factiva and equity prices):**

```env
# MMC Core API
MMC_API_BASE_URL=https://mmc-dallas-int-non-prod-ingress.mgti.mmc.com
MMC_API_CLIENT_ID=your-client-id
MMC_API_CLIENT_SECRET=your-client-secret
MMC_API_KEY=your-api-key
```

> Without MMC credentials, the app runs normally but enterprise features (Factiva collection, equity enrichment) are skipped.

---

## 4. Initialize Database

```powershell
# Start once to create base tables
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Press Ctrl+C after "Application startup complete"

# Run enterprise migrations
python scripts/migrate_007_enterprise_api_tables.py
```

---

## 5. Start

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open: **http://localhost:8000/admin/**

Login with `admin` / your configured password.

---

## 6. Import Insurers

1. Go to **Import** in the admin menu
2. Upload your Excel file with columns:
   - `ANS Code` (required) - Regulatory registration number
   - `Name` (required) - Insurer name
   - `Category` (required) - "Health", "Dental", or "Group Life"
3. Review preview and click **Confirm Import**

---

## 7. Validate Enterprise API (Optional)

If you configured MMC Core API credentials:

```powershell
# Test authentication
python scripts/test_auth.py

# Test Factiva collection
python scripts/test_factiva.py
```

### Configure Equity Tickers

1. Go to **Equity Tickers** in the admin sidebar
2. Add ticker mappings (e.g., SulAmerica -> SULA11, exchange BVMF)
3. Equity chips will appear in reports for mapped insurers

---

## 8. Run Your First Report

**Option A: Admin Dashboard**
1. Go to **Schedules**
2. Click **Run Now** for any category

**Option B: API**
```bash
curl -X POST "http://localhost:8000/api/runs/execute/category" ^
  -H "Content-Type: application/json" ^
  -d "{\"category\": \"Health\", \"send_email\": false}"
```

---

## 9. Schedule Daily Reports

Run PowerShell as Administrator:

```powershell
.\deploy\setup_scheduled_task.ps1
```

This creates scheduled tasks:
| Category | Time (Sao Paulo) |
|----------|------------------|
| Health | 6:00 AM |
| Dental | 7:00 AM |
| Group Life | 8:00 AM |

Check status:
```powershell
.\deploy\manage_service.ps1 -Action status
```

---

## Quick Reference

### Admin Dashboard
- **Dashboard**: http://localhost:8000/admin/
- **Insurers**: View/edit monitored insurers
- **Import**: Upload insurer data
- **Equity Tickers**: Manage insurer-to-ticker mappings (B3/BVMF)
- **Recipients**: View configured email recipients per category
- **Schedules**: Manage automated runs and trigger manual runs
- **Settings**: View system configuration status

### Key Commands
```powershell
# Check scheduled task status
.\deploy\manage_service.ps1 -Action status

# Run category immediately
.\deploy\manage_service.ps1 -Action run-now -Category health

# View logs
.\deploy\manage_service.ps1 -Action logs -Category health

# Validate enterprise auth
python scripts\test_auth.py

# Validate Factiva collection
python scripts\test_factiva.py
```

### API Endpoints
| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | System health check |
| `GET /api/insurers` | List all insurers |
| `GET /api/insurers/search?q=` | Search insurers |
| `POST /api/runs/execute/category` | Run a category |
| `GET /api/runs/latest` | Latest run per category |
| `GET /api/reports/archive` | Browse archived reports |
| `GET /api/schedules` | List all schedules |

---

## Pipeline Flow

Each scheduled run executes this pipeline:

1. **Collect** - Fetch articles from Factiva (Brazilian insurance codes + Portuguese keywords)
2. **Deduplicate** - Remove duplicates by URL, then by semantic similarity
3. **Match** - Assign articles to insurers (deterministic name match, then AI for ambiguous)
4. **Classify** - Azure OpenAI classifies insurer status (Critical/Watch/Monitor/Stable)
5. **Enrich** - Fetch B3 equity prices for configured tickers
6. **Report** - Generate Marsh-branded HTML report with equity chips
7. **Deliver** - Email report with PDF attachment via Microsoft Graph

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Admin password not configured" | Set `ADMIN_PASSWORD` in `.env` |
| "Azure OpenAI not configured" | Set all `AZURE_OPENAI_*` variables |
| Port 8000 in use | Change `PORT` in `.env` or kill existing process |
| Enterprise features skipped | Set `MMC_API_*` variables, run `python scripts/test_auth.py` |
| No equity chips in reports | Add ticker mappings at `/admin/equity` |

---

## Next Steps

- [Full User Guide](USER_GUIDE.md) - Complete feature documentation
- [Deployment Guide](DEPLOYMENT.md) - Production deployment options
- API docs at `/docs` when server is running

---

*BrasilIntel v1.1 -- [SamuraiJenkinz/BrasilIntel](https://github.com/SamuraiJenkinz/BrasilIntel)*
