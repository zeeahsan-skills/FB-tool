import os
import asyncio
import logging
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
except ImportError:
    async_playwright = None
    BrowserContext = None
    Page = None
    Playwright = None

from app.config import Settings, get_settings
from app.browser.session_manager import SessionManager

logger = logging.getLogger("facebook_agent.browser")


class BrowserManager:
    """
    Manages Playwright browser lifecycle with persistent context.
    Ensures sessions, cookies, and manual logins are preserved.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.profile_dir: Path = self.settings.resolved_browser_profile_dir
        self.session_manager = SessionManager(self.profile_dir)
        self.headless: bool = self.settings.BROWSER_HEADLESS

        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        """Returns True if the browser context is active and not closed."""
        return self._context is not None and len(self._context.pages) > 0

    async def start(self) -> Page:
        """
        Launches or retrieves the persistent Playwright Chromium browser.
        Returns the primary active Page.
        """
        # Guard against running persistent Chromium in serverless cloud environments (e.g. Vercel)
        if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            raise RuntimeError(
                "Browser automation must run in the local agent environment (Python on Windows/macOS/Linux) "
                "to maintain persistent browser profiles, visible manual login, and long-running discovery. "
                "Serverless functions do not support long-running persistent browser processes."
            )

        if async_playwright is None:
            raise RuntimeError(
                "Playwright is not installed. Please run: pip install -r requirements.txt && playwright install chromium"
            )

        async with self._lock:
            if self._context is not None:
                logger.info("Browser already running. Reusing existing context.")
                return await self.get_page()

            logger.info("Browser starting...")
            logger.info("Using profile directory: %s", self.profile_dir)
            logger.info("Headless mode: %s", self.headless)

            self.session_manager.ensure_profile_dir()

            try:
                self._playwright = await async_playwright().start()

                # Launch persistent context with Chromium
                self._context = await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=self.headless,
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                    ],
                )

                # Attach on close listener
                self._context.on("close", self._on_context_closed)

                pages = self._context.pages
                if pages:
                    self._page = pages[0]
                else:
                    self._page = await self._context.new_page()

                logger.info("Browser started successfully.")
                return self._page

            except Exception as e:
                logger.error("Failed to start browser: %s", str(e), exc_info=True)
                await self._cleanup()
                raise RuntimeError(f"Browser startup failure: {e}") from e

    def _on_context_closed(self, _context: BrowserContext):
        """Handler for when user manually closes the browser window."""
        logger.info("Browser window was closed by user or system.")
        self._context = None
        self._page = None

    async def get_context(self) -> BrowserContext:
        """Returns the active BrowserContext, starting it if not already running."""
        if self._context is None:
            await self.start()
        return self._context

    async def get_page(self) -> Page:
        """Returns the primary Page, creating or starting one if needed."""
        if self._context is None:
            return await self.start()

        if self._page is None or self._page.is_closed():
            pages = [p for p in self._context.pages if not p.is_closed()]
            if pages:
                self._page = pages[0]
            else:
                self._page = await self._context.new_page()

        return self._page

    async def open_facebook(self) -> dict:
        """
        Opens Facebook homepage in the persistent browser.
        Leaves the browser visible for manual login if needed.
        """
        page = await self.get_page()
        logger.info("Navigating to https://www.facebook.com ...")
        try:
            # wait_until domcontentloaded to handle heavy JS gracefully without blocking
            await page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=45000)
            logger.info("Facebook opened. Current URL: %s | Title: %s", page.url, await page.title())
            return {
                "url": page.url,
                "title": await page.title(),
                "status": "opened"
            }
        except Exception as e:
            logger.error("Facebook page loading failure: %s", str(e))
            raise RuntimeError(f"Facebook page loading failure: {e}") from e

    async def close(self) -> None:
        """Closes the browser cleanly and frees resources."""
        async with self._lock:
            await self._cleanup()
            logger.info("Browser stopped.")

    async def _cleanup(self) -> None:
        """Internal cleanup helper."""
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as e:
                logger.warning("Error closing context: %s", e)
            finally:
                self._context = None
                self._page = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning("Error stopping playwright: %s", e)
            finally:
                self._playwright = None


# Global singleton instance
_browser_manager_instance: Optional[BrowserManager] = None


def get_browser_manager() -> BrowserManager:
    """Returns the singleton BrowserManager instance."""
    global _browser_manager_instance
    if _browser_manager_instance is None:
        _browser_manager_instance = BrowserManager()
    return _browser_manager_instance
