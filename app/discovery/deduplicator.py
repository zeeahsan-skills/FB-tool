import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from app.discovery.models import DiscoveredGroup


def normalize_facebook_group_url(url: str) -> Optional[str]:
    """
    Normalizes Facebook group URLs so that identical groups with query parameters,
    trailing slashes, or m.facebook.com prefixes resolve to the same canonical key.

    Examples:
        https://m.facebook.com/groups/12345/?ref=share -> https://www.facebook.com/groups/12345
        https://www.facebook.com/groups/datingusa/about/ -> https://www.facebook.com/groups/datingusa
        https://web.facebook.com/groups/mygroup -> https://www.facebook.com/groups/mygroup
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    if not ("facebook.com" in cleaned or "fb.com" in cleaned):
        # Ignore external links or invalid URLs
        return None

    try:
        parsed = urlparse(cleaned)
        path = parsed.path.rstrip("/")

        # Match /groups/<identifier>
        # Identifier can be numeric ID (123456789) or slug (techcareers)
        match = re.search(r"/(groups)/([a-zA-Z0-9\.\_\-]+)", path)
        if match:
            group_id = match.group(2)
            # Filter out non-group reserved endpoints like 'feed', 'discover', 'joins'
            if group_id.lower() in ("discover", "feed", "joins", "search"):
                return None
            return f"https://www.facebook.com/groups/{group_id}"

        return None
    except Exception:
        return None


class GroupDeduplicator:
    """
    In-memory registry to deduplicate discovered groups by canonical URL
    while accumulating all matched keywords across multiple searches.
    """

    def __init__(self):
        self._groups_by_canonical_url: Dict[str, DiscoveredGroup] = {}

    def add_or_merge(self, group: DiscoveredGroup) -> bool:
        """
        Adds a new group or merges matched keywords if canonical URL already exists.
        Returns True if a new group was added, False if merged with an existing one.
        """
        canonical = normalize_facebook_group_url(group.url)
        if not canonical:
            return False

        # Set the normalized canonical URL on the group model
        group.url = canonical

        if canonical in self._groups_by_canonical_url:
            existing = self._groups_by_canonical_url[canonical]
            for kw in group.matched_keywords:
                if kw not in existing.matched_keywords:
                    existing.matched_keywords.append(kw)
            # Update member count if previously null but now available
            if existing.member_count is None and group.member_count is not None:
                existing.member_count = group.member_count
                existing.member_count_text = group.member_count_text
            # Update privacy if previously unknown but now available
            if (not existing.privacy or existing.privacy.lower() == "unknown") and group.privacy:
                existing.privacy = group.privacy
            return False
        else:
            self._groups_by_canonical_url[canonical] = group
            return True

    def get_all(self) -> List[DiscoveredGroup]:
        """Returns all deduplicated groups as a list."""
        return list(self._groups_by_canonical_url.values())

    def count(self) -> int:
        """Returns the number of unique groups collected."""
        return len(self._groups_by_canonical_url)

    def clear(self) -> None:
        """Resets the deduplication registry."""
        self._groups_by_canonical_url.clear()
