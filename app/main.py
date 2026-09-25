import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# On Windows, ProactorEventLoop is required for Playwright asyncio subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging
from app.browser.browser_manager import get_browser_manager

# Initialize structured logging
logger = setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application started: Facebook Group Research Agent (Env: %s)", settings.APP_ENV)
    yield
    # Cleanup browser on shutdown
    bm = get_browser_manager()
    if bm.is_running:
        logger.info("Application shutting down: closing active browser...")
        await bm.close()
    logger.info("Application stopped cleanly.")


app = FastAPI(
    title="Facebook Group Research Agent API",
    version="0.1.0",
    description="Production-ready Facebook Group Research Agent foundation",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend directory for static assets
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serves the dashboard frontend index.html."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not found, access API at /docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "facebook-group-research-agent",
        "environment": settings.APP_ENV,
    }


@app.get("/api/browser/status")
async def browser_status():
    """Returns the current status of the Playwright browser."""
    bm = get_browser_manager()
    page_url = None
    page_title = None

    if bm.is_running:
        try:
            page = await bm.get_page()
            page_url = page.url
            page_title = await page.title()
        except Exception:
            pass

    return {
        "running": bm.is_running,
        "headless": bm.headless,
        "profile_dir": str(bm.profile_dir),
        "current_url": page_url,
        "current_title": page_title,
    }


@app.post("/api/browser/start")
async def start_browser(open_fb: bool = True):
    """
    Starts the Playwright Chromium browser with persistent profile.
    Optionally opens Facebook to allow user to complete manual login.
    """
    bm = get_browser_manager()
    try:
        await bm.start()
        fb_info = None
        if open_fb:
            fb_info = await bm.open_facebook()

        return {
            "status": "success",
            "message": "Browser started successfully.",
            "running": True,
            "facebook": fb_info,
        }
    except RuntimeError as e:
        logger.error("Error starting browser via API: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error starting browser: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@app.post("/api/browser/stop")
async def stop_browser():
    """Stops the Playwright browser and frees resources."""
    bm = get_browser_manager()
    try:
        await bm.close()
        return {
            "status": "success",
            "message": "Browser stopped successfully.",
            "running": False,
        }
    except Exception as e:
        logger.error("Error stopping browser via API: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to stop browser: {e}")


# ==========================================
# Group Discovery Endpoints (Prompt 2)
# ==========================================

from app.discovery.models import (
    DiscoveryStartRequest,
    DiscoveryStatusResponse,
    DiscoveryResultsResponse,
)
from app.discovery.group_discoverer import get_discovery_service


@app.post("/api/discovery/start", response_model=DiscoveryStatusResponse)
async def start_discovery(payload: DiscoveryStartRequest):
    """
    Starts background Facebook group discovery for given niche, country, and keywords.
    """
    service = get_discovery_service()
    try:
        status = await service.start(payload)
        return status
    except RuntimeError as e:
        logger.warning("Discovery start rejected: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error starting discovery: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start discovery: {e}")


@app.get("/api/discovery/status", response_model=DiscoveryStatusResponse)
async def get_discovery_status():
    """Returns the current progress and state of the discovery service."""
    service = get_discovery_service()
    return service.get_status()


@app.post("/api/discovery/stop", response_model=DiscoveryStatusResponse)
async def stop_discovery():
    """Gracefully halts ongoing discovery while preserving collected groups and active browser."""
    service = get_discovery_service()
    return await service.stop()


@app.get("/api/discovery/results", response_model=DiscoveryResultsResponse)
async def get_discovery_results():
    """Returns all deduplicated groups discovered so far."""
    service = get_discovery_service()
    groups = service.get_results()
    status_info = service.get_status()
    return DiscoveryResultsResponse(
        total=len(groups),
        status=status_info.status,
        groups=groups
    )


@app.get("/api/browser/debug_dom")
async def debug_dom():
    """Inspects active page DOM structure to analyze rendered Facebook elements."""
    bm = get_browser_manager()
    if not bm.is_running:
        return {"error": "Browser not running"}
    page = await bm.get_page()
    html = await page.content()
    title = await page.title()
    url = page.url

    # Check for group links
    script = """
    () => {
        const anchors = Array.from(document.querySelectorAll('a'));
        return anchors.map(a => ({
            href: a.href,
            text: (a.innerText || '').trim(),
            role: a.getAttribute('role'),
            ariaLabel: a.getAttribute('aria-label')
        })).filter(item => item.href.includes('/groups/'));
    }
    """
    group_anchors = await page.evaluate(script)
    return {
        "url": url,
        "title": title,
        "html_len": len(html),
        "raw_html": html[:500],
        "group_anchors_count": len(group_anchors),
        "group_anchors_sample": group_anchors[:15]
    }
