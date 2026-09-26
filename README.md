# Facebook Group Research Agent

A production-ready foundation for automated Facebook group research, keyword intelligence, community discovery, and persistent database storage.

> **Status (Prompt 4 of 6 - Supabase Persistence):** Core architectural foundation, persistent Playwright Chromium browser management, FastAPI backend, background Facebook Group Discovery Engine, and Supabase persistent PostgreSQL storage layer with graceful offline degradation.

---

## Architecture Overview

```text
                VERCEL
          Static Frontend
                 │
                 │ HTTP
                 ▼
         LOCAL FASTAPI
                 │
      ┌──────────┴──────────┐
      ▼                     ▼
 PLAYWRIGHT              GEMINI
      │                     │
      ▼                     │
   FACEBOOK                 │
                            │
             ┌──────────────┘
             ▼
          SUPABASE
```

```text
facebook-group-agent/
│
├── app/
│   ├── main.py               # FastAPI application & REST endpoints
│   ├── config.py             # Pydantic environment configuration
│   ├── logging_config.py     # Structured file & console logging
│   │
│   ├── browser/              # Playwright persistent context & session manager
│   │   ├── browser_manager.py
│   │   └── session_manager.py
│   │
│   ├── discovery/            # Group search, deduplication & keyword tracking
│   │   ├── group_discoverer.py
│   │   ├── facebook_search.py
│   │   ├── deduplicator.py
│   │   ├── group_parser.py
│   │   └── models.py
│   │
│   ├── analyzer/             # Group post intelligence & Gemini analysis models
│   │   └── models.py
│   │
│   ├── database/             # Supabase persistence layer & repositories
│   │   ├── supabase_client.py
│   │   ├── repositories.py
│   │   └── models.py
│   │
│   └── export/               # (Phase 6: CSV / Excel export)
│
├── frontend/                 # Interactive dashboard UI (Static for Vercel)
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── supabase/
│   └── schema.sql            # PostgreSQL schema migration for Supabase
│
├── data/                     # Persistent browser profile storage
├── logs/                     # Application logs (app.log)
├── tests/                    # Comprehensive unit & API test suite
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── run.py                    # Server launch script
```

---

## Supabase Database Setup (Prompt 4)

The application uses Supabase (PostgreSQL) as a persistent database layer for discovered groups and analyses.

### 1. Create Supabase Project
1. Log in to [Supabase](https://supabase.com) and create a new project.
2. Note your **Project URL** and **API Key** in **Project Settings -> API**.

### 2. Run Database Migration
1. In your Supabase project dashboard, open the **SQL Editor** from the left navigation.
2. Open [`supabase/schema.sql`](file:///c:/Users/lenovo/Documents/facebook-group-agent/supabase/schema.sql) in this repository and copy its content.
3. Paste the SQL into the Supabase SQL Editor and click **Run**.
4. This creates:
   - `groups` table: Stores unique Facebook groups, canonical URLs, member counts, privacy, and matched keyword arrays.
   - `analyses` table: Stores activity metrics, external link policies, rules summaries, and raw JSON evidence.
   - Automatic `updated_at` trigger functions and optimized query indexes.

### 3. Configure Credentials in `.env`
Open your local `.env` file (never commit this file) and populate:

```ini
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-backend-api-key
```

### 4. Graceful Degradation
- If Supabase credentials are not configured or the network is unreachable, discovery **will not crash**.
- The agent logs the database error, preserves groups in local memory, and continues discovering other groups.
- The UI header displays a live status indicator showing whether Supabase is **Connected**, **Unreachable**, or **Not Configured**.

---

## Getting Started (Windows Guide)

### 1. Prerequisites
- Python 3.11+ installed.
- PowerShell or Windows Command Prompt.

### 2. Setup Virtual Environment

```powershell
# Navigate into the project folder
cd c:\Users\lenovo\Documents\facebook-group-agent

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies & Playwright Browser

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Set your configuration values inside `.env`.

---

## Running the Application

### 1. Launch the Server

```powershell
.\.venv\Scripts\python.exe run.py
```

The server will start at:
- **Dashboard UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Verify Database Connection
Navigate to [http://127.0.0.1:8000/api/database/status](http://127.0.0.1:8000/api/database/status) or check the **DB Status Badge** in the top navigation bar.

Expected response format:
```json
{
  "configured": true,
  "connected": true
}
```

If credentials are unset:
```json
{
  "configured": false,
  "connected": false
}
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check endpoint |
| `GET` | `/api/browser/status` | Current Playwright browser state |
| `POST` | `/api/browser/start` | Launch persistent Chromium browser |
| `POST` | `/api/browser/stop` | Gracefully close browser and persist session |
| `POST` | `/api/discovery/start` | Launch background group discovery engine |
| `GET` | `/api/discovery/status` | Live discovery progress & keyword tracking |
| `POST` | `/api/discovery/stop` | Gracefully stop ongoing discovery |
| `GET` | `/api/discovery/results` | In-memory deduplicated discovery results |
| `GET` | `/api/database/status` | Supabase configuration and connectivity status |
| `GET` | `/api/groups` | Persistent groups list from Supabase (supports `limit`, `offset`) |
| `GET` | `/api/groups/analyzed` | Persistent groups that have associated analyses |
| `GET` | `/api/groups/{group_id}` | Retrieve single group by UUID |
| `GET` | `/api/groups/{group_id}/analysis` | Retrieve analysis intelligence for group |
| `POST` | `/api/groups/{group_id}/analysis` | Upsert Gemini analysis intelligence for group |
| `GET` | `/api/analyses` | List group analyses stored in Supabase |

---

## Upsert & Deduplication Architecture

1. **Canonical URL Normalization**: Strips tracking queries (`?ref=share`), mobile subdomains (`m.facebook.com`), and trailing slashes to guarantee exact identity across searches.
2. **In-Memory Deduplication**: Maintained via `GroupDeduplicator` during active discovery runs.
3. **Database Upsert**:
   - Unique constraint on `groups.facebook_url`.
   - When a known group is rediscovered: merges new `matched_keywords` with existing keywords, updates `member_count` and `privacy` if improved, and updates `updated_at`.
   - Analysis records use unique constraint on `analyses.group_id` so subsequent analyses update the existing record rather than accumulating duplicates.

---

## Security & Reliability Guidelines

- **Zero Secret Exposure**: Supabase secret keys and database credentials are backend-only. The static frontend and API endpoints never leak credentials.
- **Git Protection**: `.env` is listed in `.gitignore` and must never be committed.
- **Polite Navigation**: Anti-bot delays (`DISCOVERY_DELAY_MIN` to `DISCOVERY_DELAY_MAX`) prevent request bursts.
- **Vercel Pure Static**: Vercel serves only static assets (`HTML/CSS/JS`). All automation, Playwright sessions, and Supabase writes run on the local agent.

---

## Running Automated Tests

Run the full pytest suite:

```powershell
.\.venv\Scripts\pytest.exe -v
```

All 32 unit and API tests execute offline with mock drivers and require no live credentials.
