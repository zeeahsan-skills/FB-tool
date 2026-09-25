import asyncio
import logging
from typing import List, Optional
from app.config import get_settings
from app.browser.browser_manager import get_browser_manager
from app.discovery.models import DiscoveredGroup, DiscoveryStartRequest, DiscoveryStatusResponse
from app.discovery.deduplicator import GroupDeduplicator
from app.discovery.facebook_search import FacebookSearchEngine

logger = logging.getLogger("facebook_agent.discoverer")


class GroupDiscoveryService:
    """
    Orchestrates the background Facebook Group Discovery process.
    Tracks live state, handles cancellation, and preserves deduplicated results.
    """

    def __init__(self):
        self.settings = get_settings()
        self.deduplicator = GroupDeduplicator()

        self._running: bool = False
        self._status: str = "idle"  # idle, searching, completed, stopped, error
        self._current_keyword: Optional[str] = None
        self._keywords_completed: int = 0
        self._keywords_total: int = 0
        self._error: Optional[str] = None

        self._stop_requested: bool = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    def get_status(self) -> DiscoveryStatusResponse:
        """Returns the current execution status."""
        return DiscoveryStatusResponse(
            running=self._running,
            status=self._status,
            current_keyword=self._current_keyword,
            keywords_completed=self._keywords_completed,
            keywords_total=self._keywords_total,
            groups_found=self.deduplicator.count(),
            error=self._error,
        )

    def get_results(self) -> List[DiscoveredGroup]:
        """Returns all collected deduplicated groups."""
        return self.deduplicator.get_all()

    async def start(self, req: DiscoveryStartRequest) -> DiscoveryStatusResponse:
        """
        Initiates discovery in a background task.
        Rejects new start if already running.
        """
        async with self._lock:
            if self._running:
                raise RuntimeError("Discovery is already running. Please stop it or wait for completion.")

            self._running = True
            self._status = "searching"
            self._stop_requested = False
            self._error = None
            self._keywords_total = len(req.keywords)
            self._keywords_completed = 0
            self._current_keyword = req.keywords[0] if req.keywords else None
            # Reset deduplicator for fresh run
            self.deduplicator.clear()

            # Launch background execution task
            self._task = asyncio.create_task(self._run_discovery_loop(req))

            logger.info(
                "Discovery started: Niche='%s', Country='%s', Total Keywords=%d",
                req.niche,
                req.country,
                len(req.keywords)
            )
            return self.get_status()

    async def stop(self) -> DiscoveryStatusResponse:
        """Gracefully halts ongoing discovery without closing the user's browser."""
        async with self._lock:
            if not self._running:
                logger.info("Discovery stop requested but service is not currently running.")
                return self.get_status()

            logger.info("Graceful stop requested for group discovery.")
            self._stop_requested = True
            self._status = "stopping"

        # Wait briefly for task to observe flag and exit
        if self._task and not self._task.done():
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        self._running = False
        self._status = "stopped"
        logger.info("Discovery stopped. Preserved %d discovered groups.", self.deduplicator.count())
        return self.get_status()

    async def _run_discovery_loop(self, req: DiscoveryStartRequest) -> None:
        """Worker loop executing search across keywords sequentially."""
        bm = get_browser_manager()

        try:
            # Ensure browser is ready
            if not bm.is_running:
                logger.info("Playwright browser not running. Starting browser for discovery...")
                await bm.start()

            page = await bm.get_page()

            search_engine = FacebookSearchEngine(
                page=page,
                delay_min=self.settings.DISCOVERY_DELAY_MIN,
                delay_max=self.settings.DISCOVERY_DELAY_MAX,
                should_stop_callback=lambda: self._stop_requested
            )

            max_results_per_kw = req.max_results_per_keyword or self.settings.DISCOVERY_MAX_RESULTS_PER_KEYWORD
            scroll_count = req.scroll_count or self.settings.DISCOVERY_SCROLL_COUNT

            for idx, keyword in enumerate(req.keywords):
                if self._stop_requested:
                    logger.info("Halting discovery loop due to stop request.")
                    break

                self._current_keyword = keyword
                logger.info("Discovery progress: Keyword [%d/%d]: '%s'", idx + 1, len(req.keywords), keyword)

                try:
                    raw_items = await search_engine.search_keyword(
                        keyword=keyword,
                        niche=req.niche,
                        country=req.country,
                        max_results=max_results_per_kw,
                        scroll_count=scroll_count
                    )

                    new_added = 0
                    duplicates = 0
                    for raw in raw_items:
                        group = DiscoveredGroup(
                            name=raw["name"],
                            url=raw["url"],
                            member_count=raw.get("member_count"),
                            member_count_text=raw.get("member_count_text"),
                            privacy=raw.get("privacy"),
                            keyword=keyword,
                            niche=req.niche,
                            country=req.country,
                            matched_keywords=[keyword]
                        )
                        added = self.deduplicator.add_or_merge(group)
                        if added:
                            new_added += 1
                        else:
                            duplicates += 1

                    logger.info(
                        "Keyword '%s' complete: Discovered %d groups (%d new, %d duplicate merged). Total collected: %d",
                        keyword,
                        len(raw_items),
                        new_added,
                        duplicates,
                        self.deduplicator.count()
                    )

                except Exception as kw_err:
                    logger.error("Error processing keyword '%s': %s", keyword, kw_err, exc_info=True)
                    # One bad keyword does not crash the entire process
                    continue
                finally:
                    self._keywords_completed += 1

            if self._stop_requested:
                self._status = "stopped"
                logger.info("Discovery job ended in stopped state.")
            else:
                self._status = "completed"
                logger.info("Discovery completed successfully! Total unique groups found: %d", self.deduplicator.count())

        except Exception as e:
            self._error = str(e)
            self._status = "error"
            logger.error("Fatal discovery engine error: %s", e, exc_info=True)
        finally:
            self._running = False
            self._current_keyword = None


# Global singleton instance
_discovery_service: Optional[GroupDiscoveryService] = None


def get_discovery_service() -> GroupDiscoveryService:
    """Returns singleton GroupDiscoveryService instance."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = GroupDiscoveryService()
    return _discovery_service
