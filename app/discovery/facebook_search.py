import asyncio
import logging
import random
import urllib.parse
from typing import AsyncGenerator, Callable, Dict, List, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from app.discovery.group_parser import parse_member_count, parse_privacy_status
from app.discovery.deduplicator import normalize_facebook_group_url

logger = logging.getLogger("facebook_agent.search")


class FacebookSearchEngine:
    """
    Drives Playwright page interactions to search Facebook for groups.
    Uses resilient semantic selectors, role-based inspection, and progressive scrolling.
    Does not use private APIs or attempt to bypass security checks.
    """

    def __init__(
        self,
        page: Page,
        delay_min: float = 1.5,
        delay_max: float = 3.5,
        should_stop_callback: Optional[Callable[[], bool]] = None
    ):
        self.page = page
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.should_stop_callback = should_stop_callback or (lambda: False)

    async def _safe_delay(self, multiplier: float = 1.0) -> None:
        """Sleeps for a randomized human-like delay to ensure polite navigation."""
        base = random.uniform(self.delay_min, self.delay_max) * multiplier
        await asyncio.sleep(base)

    async def search_keyword(
        self,
        keyword: str,
        niche: str,
        country: str,
        max_results: int = 50,
        scroll_count: int = 5
    ) -> List[dict]:
        """
        Executes a Facebook search for a specific keyword in the Groups category.
        Returns a list of raw group dictionaries.
        """
        if self.should_stop_callback():
            logger.info("Search cancellation requested before starting keyword: %s", keyword)
            return []

        logger.info("Navigating to Facebook search for keyword: '%s' (Niche: %s, Country: %s)", keyword, niche, country)

        # Clean keyword search URL
        encoded_query = urllib.parse.quote(keyword)
        search_url = f"https://www.facebook.com/search/groups/?q={encoded_query}"

        try:
            # Navigate to group search page
            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            await self._safe_delay(1.5)
        except Exception:
            # Fallback if networkidle times out due to persistent websockets
            try:
                if not self.page.url.startswith("https://www.facebook.com/search/"):
                    await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await self._safe_delay(2.0)
            except Exception as e:
                logger.warning("Error navigating to %s: %s", search_url, e)

        current_url = self.page.url
        logger.info("Search page loaded. Current URL: %s", current_url)

        # Check for login challenge or checkpoint
        if "checkpoint" in current_url or "login" in current_url:
            logger.warning("Facebook redirected to login/checkpoint: %s. Action required by user in browser.", current_url)
            raise RuntimeError("Facebook session requires login or security verification in visible browser.")

        collected_raw_groups: List[dict] = []
        seen_urls = set()

        for scroll_idx in range(scroll_count):
            if self.should_stop_callback():
                logger.info("Stop requested during scroll batch %d of %d", scroll_idx + 1, scroll_count)
                break

            # Extract groups currently visible in DOM
            batch = await self._extract_visible_group_cards()
            for item in batch:
                norm = normalize_facebook_group_url(item.get("url", ""))
                if norm and norm not in seen_urls:
                    seen_urls.add(norm)
                    item["url"] = norm
                    item["keyword"] = keyword
                    item["niche"] = niche
                    item["country"] = country
                    collected_raw_groups.append(item)
                    if len(collected_raw_groups) >= max_results:
                        break

            if len(collected_raw_groups) >= max_results:
                logger.info("Reached maximum result target (%d) for keyword '%s'", max_results, keyword)
                break

            # Scroll down smoothly to load next batch
            logger.debug("Scrolling search page (batch %d/%d)...", scroll_idx + 1, scroll_count)
            await self.page.evaluate("window.scrollBy({top: window.innerHeight * 1.5, behavior: 'smooth'});")
            await self._safe_delay(1.0)

        logger.info("Collected %d groups for keyword '%s'", len(collected_raw_groups), keyword)
        return collected_raw_groups

    async def _click_groups_filter_tab(self) -> None:
        """Attempts to click the 'Groups' filter tab on Facebook search results if redirected to 'All'."""
        try:
            # Look for semantic navigation tab or link labeled 'Groups'
            filter_selectors = [
                "a[role='tab']:has-text('Groups')",
                "div[role='tab']:has-text('Groups')",
                "a:has-text('Groups')[href*='/search/groups/']",
                "span:has-text('Groups')",
            ]
            for sel in filter_selectors:
                el = self.page.locator(sel).first
                if await el.is_visible():
                    logger.info("Found 'Groups' filter tab with selector: %s. Clicking...", sel)
                    await el.click()
                    await self._safe_delay(1.5)
                    return
        except Exception as e:
            logger.debug("Could not click 'Groups' filter tab: %s", e)

    async def _extract_visible_group_cards(self) -> List[dict]:
        """
        Executes client-side DOM traversal to extract Facebook group cards.
        Uses semantic anchors pointing to /groups/ and extracts nearby headings & subtitle text.
        Avoids fragile hashed class names.
        """
        script = """
        () => {
            const results = [];
            // Find all anchor links that point to /groups/
            const links = Array.from(document.querySelectorAll('a[href*="/groups/"]'));
            
            for (const link of links) {
                const href = link.href || link.getAttribute('href') || '';
                // Filter out non-group navigation links
                if (!href || href.includes('/groups/feed') || href.includes('/groups/discover') || href.includes('/groups/search') || href.includes('/groups/joins')) {
                    continue;
                }
                
                // Get name from anchor text, aria-label, or inner heading/span
                let name = (link.innerText || '').trim();
                if (!name && link.getAttribute('aria-label')) {
                    name = link.getAttribute('aria-label').trim();
                }
                const heading = link.querySelector('h2, h3, span[dir="auto"], strong');
                if (heading && heading.innerText.trim()) {
                    name = heading.innerText.trim();
                }
                
                // If link text is too short or generic, skip
                if (!name || name.length < 2 || name.toLowerCase() === 'groups' || name.toLowerCase() === 'view group') {
                    continue;
                }

                // Traverse up to find the enclosing card container to get member count / privacy
                let container = link;
                let cardText = '';
                for (let i = 0; i < 6; i++) {
                    if (container.parentElement) {
                        container = container.parentElement;
                        const txt = container.innerText || '';
                        if (txt.toLowerCase().includes('member') || txt.toLowerCase().includes('public') || txt.toLowerCase().includes('private')) {
                            cardText = txt;
                            break;
                        }
                    }
                }

                results.push({
                    name: name,
                    url: href,
                    card_text: cardText
                });
            }
            return results;
        }
        """
        try:
            raw_cards = await self.page.evaluate(script)
        except Exception as e:
            logger.error("Error evaluating DOM group cards: %s", e)
            return []

        processed = []
        for c in raw_cards:
            name = c.get("name", "").strip()
            url = c.get("url", "").strip()
            card_text = c.get("card_text", "")

            # Parse members and privacy
            member_count, member_count_text = parse_member_count(card_text)
            privacy = parse_privacy_status(card_text)

            processed.append({
                "name": name,
                "url": url,
                "member_count": member_count,
                "member_count_text": member_count_text,
                "privacy": privacy,
            })

        return processed
