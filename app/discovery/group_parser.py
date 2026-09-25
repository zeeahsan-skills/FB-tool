import re
import logging
from typing import Optional, Tuple
from bs4 import BeautifulSoup

logger = logging.getLogger("facebook_agent.parser")


def parse_member_count(text: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Extracts visible member count text and converts it to an integer.
    Preserves original text without guessing or hallucinating numbers.

    Examples:
        "125K members" -> (125000, "125K members")
        "1.2M members" -> (1200000, "1.2M members")
        "520 members"  -> (520, "520 members")
        "Active discussion" -> (None, None)
    """
    if not text or not isinstance(text, str):
        return None, None

    # Match patterns like: 125K members, 1.2M members, 450 members, 10,500 members
    # Also handles localized / lowercase variations
    pattern = r"([\d\.,\s]+(?:\s*[KkMmBb])?)\s+(?:members?|people)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None, None

    raw_matched_text = match.group(0).strip()
    raw_num_part = match.group(1).strip().replace(" ", "").replace(",", "")

    try:
        multiplier = 1
        if raw_num_part.lower().endswith("k"):
            multiplier = 1_000
            val_str = raw_num_part[:-1]
        elif raw_num_part.lower().endswith("m"):
            multiplier = 1_000_000
            val_str = raw_num_part[:-1]
        elif raw_num_part.lower().endswith("b"):
            multiplier = 1_000_000_000
            val_str = raw_num_part[:-1]
        else:
            val_str = raw_num_part

        calculated = int(float(val_str) * multiplier)
        return calculated, raw_matched_text
    except Exception as e:
        logger.debug("Failed to calculate integer member count from %s: %s", raw_num_part, e)
        return None, raw_matched_text


def parse_privacy_status(text: str) -> Optional[str]:
    """
    Identifies Public vs Private group status from card subtitle text.
    Returns 'Public', 'Private', or None if not identified.
    """
    if not text:
        return None

    lower = text.lower()
    if "public" in lower:
        return "Public"
    elif "private" in lower:
        return "Private"
    return None


def extract_group_from_card_html(card_html: str) -> dict:
    """
    Robust fallback parser using BeautifulSoup on an HTML card snippet.
    Used for unit testing fixtures and HTML-based extraction.
    """
    soup = BeautifulSoup(card_html, "html.parser")

    # Find the link pointing to /groups/
    link_tag = soup.find("a", href=re.compile(r"/groups/[a-zA-Z0-9\._\-]+"))
    if not link_tag:
        return {}

    url = link_tag.get("href", "")
    name = link_tag.get_text(strip=True)

    # Search for member count and privacy in text nodes
    all_text = soup.get_text(separator=" ", strip=True)
    member_count, member_count_text = parse_member_count(all_text)
    privacy = parse_privacy_status(all_text)

    return {
        "name": name,
        "url": url,
        "member_count": member_count,
        "member_count_text": member_count_text,
        "privacy": privacy,
    }
