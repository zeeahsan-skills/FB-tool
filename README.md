# Facebook Group Research Agent

A production-ready foundation for automated Facebook group research, keyword intelligence, and community discovery.

> **Note (Prompt 1 of 6):** This is the core architectural foundation: environment configuration, structured logging, persistent Playwright Chromium browser management, FastAPI backend, and dashboard UI. Scraping, Gemini AI analysis, and Supabase persistence will be layered in subsequent phases.

---

## Architecture Overview

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
│   ├── discovery/            # (Phase 2: Group search & filtering)
│   ├── analyzer/             # (Phase 4: Gemini post analysis)
│   ├── database/             # (Phase 5: Supabase persistence)
│   └── export/               # (Phase 6: CSV / JSON reporting)
│
├── frontend/                 # Interactive dashboard UI
│   ├── index.html
│   ├── app.js
│   └── styles.css
│
├── data/                     # Persistent browser profile storage
├── logs/                     # Application logs (app.log)
├── tests/                    # Unit & API test suite
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
└── run.py                    # Server launch script
```

---

## Getting Started (Windows Guide)

### 1. Prerequisites
- Python 3.11+ installed (e.g. via [python.org](https://www.python.org/) or Miniconda).
- PowerShell or Windows Command Prompt.

### 2. Setup Virtual Environment

Open PowerShell in the project directory:

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

> **Note:** If `playwright install` encounters permission restrictions on Windows, run the installer directly via the bundled driver:
> ```powershell
> & ".\.venv\Lib\site-packages\playwright\driver\node.exe" ".\.venv\Lib\site-packages\playwright\driver\package\cli.js" install chromium
> ```

### 4. Configure Environment

Copy the example file to `.env`:

```powershell
Copy-Item .env.example .env
```

Default contents in `.env`:
```ini
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000

BROWSER_HEADLESS=false
BROWSER_USER_DATA_DIR=./data/browser-profile

# Reserved for future phases:
GEMINI_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
```

---

## Running the Application

### 1. Launch the Server

```powershell
.\.venv\Scripts\python.exe run.py
```

The server will start at:
- **Dashboard UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. Manual Login & Session Persistence Workflow

### 3. Facebook Group Discovery (Prompt 2)

1. Launch or keep the browser started. If not yet logged in, complete manual login in the visible Chromium window.
2. In the **Group Discovery Engine** card on the dashboard:
   - Enter your target **Niche** (e.g. `Dating`).
   - Enter your target **Country / Region** (e.g. `USA`).
   - Enter one or more search **Keywords** (e.g. `dating groups`, `singles USA`). Use **+ Add keyword** to add more.
   - Adjust **Max Results Per Keyword** (default 50) and **Scroll Batches** (default 5).
3. Click **Start Discovery**.
4. The agent will search each keyword sequentially in the background, navigate through group search results, and collect publicly visible groups.
5. If the same group appears across multiple keywords, the **GroupDeduplicator** normalizes its canonical URL and merges all matched keywords into a single consolidated record.
6. Real-time progress is displayed in the live progress bar and terminal log stream.
7. Click **Stop** at any time to gracefully halt discovery while keeping already collected groups and keeping your browser session active.
8. Discovered groups appear immediately in the **Discovered Groups** table with direct links to open each group in a new tab.

---

## Deployment Architecture: Local Agent vs. Vercel

```text
┌────────────────────────────────────────────────────────┐
│                   LOCAL AGENT (Primary)                │
│                                                        │
│  FastAPI (127.0.0.1:8000)                             │
│     ├── Playwright Chromium (Visible Mode)             │
│     ├── Persistent Profile (./data/browser-profile)    │
│     └── Background Group Discovery Engine              │
└──────────────────────────▲─────────────────────────────┘
                           │ Agent API (http://127.0.0.1:8000)
┌──────────────────────────┴─────────────────────────────┐
│                 VERCEL DEPLOYMENT (Static)             │
│                                                        │
│  • Pure static frontend hosting (HTML/CSS/JS)          │
│  • No serverless functions, no crashes                 │
│  • Shows 'Local Agent Offline' if agent is stopped     │
└────────────────────────────────────────────────────────┘
```

### 1. Local Agent (Runs Browser Automation)
The browser automation backend **must run locally on your computer** where persistent cookies, visible browser windows for manual login, and long-running discovery loops are supported.

Start the agent:
```powershell
python run.py
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### 2. Vercel Hosting (Static Dashboard)
The repository is configured via `vercel.json` as a **pure static site** (`outputDirectory: "frontend"`).
- Vercel builds and hosts the dashboard UI statically without invoking any serverless Python functions.
- If you access the dashboard on Vercel while your local agent is stopped, the dashboard displays a clear, informative **"Local Agent Offline"** banner.
- Once you start `python run.py` locally, the Vercel dashboard automatically connects to your local machine (`http://127.0.0.1:8000`) and provides full control over the browser and discovery engine.

---

## Running Tests

Execute the automated test suite with pytest:

```powershell
.\.venv\Scripts\pytest.exe -v
```

---

## Security & Reliability Guidelines

- **No Stored Passwords**: Facebook passwords are never requested, stored, or automated.
- **Access Control & Anti-Bot**: The system does not bypass CAPTCHAs, MFA, rate limits, or private APIs. Users authenticate through standard visible browser sessions.
- **Polite Navigation**: Randomized pacing (`DISCOVERY_DELAY_MIN` to `DISCOVERY_DELAY_MAX`) prevents aggressive request bursts.
- **Git Safety**: Persistent profiles (`data/`), log outputs (`logs/`), and `.env` credentials are excluded by `.gitignore`.
