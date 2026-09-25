import pytest
from pydantic import ValidationError
from app.discovery.models import DiscoveredGroup, DiscoveryStartRequest, DiscoveryStatusResponse
from app.discovery.deduplicator import normalize_facebook_group_url, GroupDeduplicator
from app.discovery.group_parser import parse_member_count, parse_privacy_status, extract_group_from_card_html


def test_url_normalization():
    """Verify various Facebook URL formats are normalized to canonical form."""
    assert normalize_facebook_group_url("https://www.facebook.com/groups/datingusa/") == "https://www.facebook.com/groups/datingusa"
    assert normalize_facebook_group_url("https://m.facebook.com/groups/123456789?ref=share") == "https://www.facebook.com/groups/123456789"
    assert normalize_facebook_group_url("https://web.facebook.com/groups/my_group.sub/?id=1") == "https://www.facebook.com/groups/my_group.sub"
    # Reserved endpoints return None
    assert normalize_facebook_group_url("https://www.facebook.com/groups/feed/") is None
    assert normalize_facebook_group_url("https://www.facebook.com/groups/discover") is None
    # External URLs return None
    assert normalize_facebook_group_url("https://google.com/test") is None
    assert normalize_facebook_group_url("") is None


def test_deduplicator_merge_keywords():
    """Verify duplicate groups from multiple keywords merge matched_keywords."""
    dedup = GroupDeduplicator()

    g1 = DiscoveredGroup(
        name="USA Singles",
        url="https://www.facebook.com/groups/usasingles/?ref=search",
        member_count=85000,
        member_count_text="85K members",
        privacy="Public",
        keyword="dating groups",
        niche="Dating",
        country="USA"
    )
    g2 = DiscoveredGroup(
        name="USA Singles",
        url="https://m.facebook.com/groups/usasingles",
        member_count=85000,
        member_count_text="85K members",
        privacy="Public",
        keyword="singles USA",
        niche="Dating",
        country="USA"
    )

    added1 = dedup.add_or_merge(g1)
    added2 = dedup.add_or_merge(g2)

    assert added1 is True
    assert added2 is False
    assert dedup.count() == 1

    all_groups = dedup.get_all()
    assert len(all_groups) == 1
    assert "dating groups" in all_groups[0].matched_keywords
    assert "singles USA" in all_groups[0].matched_keywords
    assert all_groups[0].url == "https://www.facebook.com/groups/usasingles"


def test_parse_member_count():
    """Verify member count text parsing into integer counts."""
    c, t = parse_member_count("Public group · 125K members · 10 posts a day")
    assert c == 125000
    assert "125K members" in t

    c2, t2 = parse_member_count("Private group · 1.2M members")
    assert c2 == 1200000
    assert "1.2M members" in t2

    c3, t3 = parse_member_count("450 members")
    assert c3 == 450
    assert "450 members" in t3

    c4, t4 = parse_member_count("No count here")
    assert c4 is None
    assert t4 is None


def test_parse_privacy_status():
    """Verify privacy status extraction."""
    assert parse_privacy_status("Public group · 50K members") == "Public"
    assert parse_privacy_status("Private group · 10 members") == "Private"
    assert parse_privacy_status("Just some random text") is None


def test_html_card_extraction_fixture():
    """Verify card HTML extraction using static fixture."""
    fixture_html = """
    <div class="search-result-card">
        <a href="https://www.facebook.com/groups/austinsingles/">
            <h3>Austin Singles & Dating Network</h3>
        </a>
        <div>
            <span>Public group · 24K members · 5 posts a day</span>
        </div>
    </div>
    """
    parsed = extract_group_from_card_html(fixture_html)
    assert parsed["name"] == "Austin Singles & Dating Network"
    assert parsed["url"] == "https://www.facebook.com/groups/austinsingles/"
    assert parsed["member_count"] == 24000
    assert parsed["privacy"] == "Public"


def test_discovery_request_validation():
    """Verify DiscoveryStartRequest validates keywords and bounds."""
    # Valid
    req = DiscoveryStartRequest(
        niche="Fitness",
        country="UK",
        keywords=["london fitness", "uk runners"]
    )
    assert len(req.keywords) == 2

    # Empty keywords list
    with pytest.raises(ValidationError):
        DiscoveryStartRequest(
            niche="Fitness",
            country="UK",
            keywords=[]
        )

    # All whitespace keywords
    with pytest.raises(ValidationError):
        DiscoveryStartRequest(
            niche="Fitness",
            country="UK",
            keywords=["   ", ""]
        )

    # Exceeding bounds
    with pytest.raises(ValidationError):
        DiscoveryStartRequest(
            niche="Fitness",
            country="UK",
            keywords=["fitness"],
            max_results_per_keyword=500  # max 200
        )
