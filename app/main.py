import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# On Windows, ProactorEventLoop is required for Playwright asyncio subprocesses
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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


# ==========================================
# Database Persistence, Filters & Export (Prompts 4 & 5)
# ==========================================

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.database import (
    check_supabase_connection,
    list_groups,
    list_analyzed_groups,
    get_group_by_id,
    get_group_details,
    get_analysis_for_group,
    list_analyses,
    upsert_analysis,
    query_groups_filtered,
    DatabaseStatusResponse,
    GroupAnalysis,
)
from app.export import generate_csv, generate_excel


@app.get("/api/database/status", response_model=DatabaseStatusResponse)
async def get_database_status():
    """
    Returns the configuration and connectivity status of Supabase.
    Sensitive credentials and secrets are strictly redacted.
    """
    status = check_supabase_connection()
    return DatabaseStatusResponse(**status)


@app.get("/api/groups")
async def get_persisted_groups(
    niche: Optional[str] = None,
    country: Optional[str] = None,
    privacy: Optional[str] = None,
    activity_status: Optional[str] = None,
    external_link_status: Optional[str] = None,
    min_members: Optional[int] = None,
    max_members: Optional[int] = None,
    keyword: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    sort_by: str = "discovered_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    paginated: bool = False,
):
    """
    Returns persistent groups stored in Supabase.
    Supports filtering, sorting, and pagination.
    Maintains backward compatibility: returns raw list when paginated=False.
    """
    has_filters = any([
        niche, country, privacy, activity_status, external_link_status,
        min_members is not None, max_members is not None, keyword,
        is_analyzed is not None, sort_by != "discovered_at", sort_order != "desc"
    ])

    if not paginated and not has_filters:
        return list_groups(limit=limit or 100, offset=offset or 0)

    result = query_groups_filtered(
        niche=niche,
        country=country,
        privacy=privacy,
        activity_status=activity_status,
        external_link_status=external_link_status,
        min_members=min_members,
        max_members=max_members,
        keyword=keyword,
        is_analyzed=is_analyzed,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
        limit=limit,
    )

    if paginated:
        return result
    return result["groups"]


@app.get("/api/groups/filter")
async def get_filtered_groups(
    niche: Optional[str] = None,
    country: Optional[str] = None,
    privacy: Optional[str] = None,
    activity_status: Optional[str] = None,
    external_link_status: Optional[str] = None,
    min_members: Optional[int] = None,
    max_members: Optional[int] = None,
    keyword: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    sort_by: str = "discovered_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    """Returns paginated, multi-filtered groups with metadata for the dashboard table."""
    return query_groups_filtered(
        niche=niche,
        country=country,
        privacy=privacy,
        activity_status=activity_status,
        external_link_status=external_link_status,
        min_members=min_members,
        max_members=max_members,
        keyword=keyword,
        is_analyzed=is_analyzed,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@app.get("/api/groups/analyzed")
async def get_analyzed_groups(limit: int = 100, offset: int = 0):
    """Returns persistent groups that have completed analysis."""
    return list_analyzed_groups(limit=limit, offset=offset)


@app.get("/api/groups/{group_id}")
async def get_group(group_id: str):
    """Retrieves a single group by its ID."""
    group = get_group_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@app.get("/api/groups/{group_id}/details")
async def get_group_full_details(group_id: str):
    """Retrieves combined group information, analysis, and raw evidence."""
    details = get_group_details(group_id)
    if not details:
        raise HTTPException(status_code=404, detail="Group not found")
    return details


@app.get("/api/groups/{group_id}/analysis")
async def get_group_analysis(group_id: str):
    """Retrieves analysis intelligence for a group."""
    analysis = get_analysis_for_group(group_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found for group")
    return analysis


@app.post("/api/groups/{group_id}/analysis")
async def save_group_analysis(group_id: str, payload: GroupAnalysis):
    """Saves or updates Gemini analysis for a group in Supabase."""
    payload.group_id = group_id
    saved = upsert_analysis(payload)
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to persist analysis to database")
    return saved


@app.get("/api/analyses")
async def get_analyses(limit: int = 100, offset: int = 0):
    """Lists group analyses stored in Supabase."""
    return list_analyses(limit=limit, offset=offset)


# ==========================================
# Export Endpoints (Prompt 5)
# ==========================================

@app.get("/api/export/csv")
async def export_groups_csv(
    niche: Optional[str] = None,
    country: Optional[str] = None,
    privacy: Optional[str] = None,
    activity_status: Optional[str] = None,
    external_link_status: Optional[str] = None,
    min_members: Optional[int] = None,
    max_members: Optional[int] = None,
    keyword: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    sort_by: str = "discovered_at",
    sort_order: str = "desc",
):
    """
    Exports currently filtered Facebook groups as a CSV download.
    Never exposes internal credentials or API keys in the exported data.
    """
    data = query_groups_filtered(
        niche=niche,
        country=country,
        privacy=privacy,
        activity_status=activity_status,
        external_link_status=external_link_status,
        min_members=min_members,
        max_members=max_members,
        keyword=keyword,
        is_analyzed=is_analyzed,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=2000,
    )
    groups = data.get("groups", [])
    csv_content = generate_csv(groups)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"facebook_groups_{timestamp}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
    )


@app.get("/api/export/excel")
async def export_groups_excel(
    niche: Optional[str] = None,
    country: Optional[str] = None,
    privacy: Optional[str] = None,
    activity_status: Optional[str] = None,
    external_link_status: Optional[str] = None,
    min_members: Optional[int] = None,
    max_members: Optional[int] = None,
    keyword: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    sort_by: str = "discovered_at",
    sort_order: str = "desc",
):
    """
    Exports currently filtered Facebook groups as a formatted Excel (.xlsx) workbook.
    Never exposes internal credentials or API keys in the exported data.
    """
    data = query_groups_filtered(
        niche=niche,
        country=country,
        privacy=privacy,
        activity_status=activity_status,
        external_link_status=external_link_status,
        min_members=min_members,
        max_members=max_members,
        keyword=keyword,
        is_analyzed=is_analyzed,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=2000,
    )
    groups = data.get("groups", [])
    excel_bytes = generate_excel(groups)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"facebook_groups_{timestamp}.xlsx"

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache",
        },
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
