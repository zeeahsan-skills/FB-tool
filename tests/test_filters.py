"""
Unit tests for Dashboard Filters, Sorting, Pagination, and Group Details (Prompt 5).
Validates filtering logic, database query mocking, empty database handling,
sorting orders, and REST API endpoints.
"""
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.database import (
    reset_supabase_client,
    query_groups_filtered,
    get_group_details,
)


@pytest.fixture(autouse=True)
def clean_client_state():
    reset_supabase_client()
    yield
    reset_supabase_client()


MOCK_GROUPS_DB = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Austin Tech & Startup Founders",
        "url": "https://www.facebook.com/groups/austintech",
        "member_count": 25000,
        "privacy": "Public",
        "niche": "Technology",
        "country": "USA",
        "matched_keywords": ["tech", "startups"],
        "activity_status": "Active",
        "external_link_status": "Allowed",
        "discovered_at": "2026-09-01T10:00:00Z",
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "London Singles Community",
        "url": "https://www.facebook.com/groups/londonsingles",
        "member_count": 8000,
        "privacy": "Private",
        "niche": "Dating",
        "country": "UK",
        "matched_keywords": ["dating", "singles"],
        "activity_status": "Moderate",
        "external_link_status": "Restricted",
        "discovered_at": "2026-09-02T12:00:00Z",
    },
    {
        "id": "33333333-3333-3333-3333-333333333333",
        "name": "Digital Marketing Global Hub",
        "url": "https://www.facebook.com/groups/digitalmarketing",
        "member_count": 150000,
        "privacy": "Public",
        "niche": "Marketing",
        "country": "Global",
        "matched_keywords": ["marketing", "seo"],
        "activity_status": "Active",
        "external_link_status": "Allowed",
        "discovered_at": "2026-09-03T14:00:00Z",
    },
    {
        "id": "44444444-4444-4444-4444-444444444444",
        "name": "Hidden Small Community",
        "url": "https://www.facebook.com/groups/hidden",
        "member_count": 500,
        "privacy": "Private",
        "niche": "General",
        "country": "USA",
        "matched_keywords": ["community"],
        "activity_status": "Inactive",
        "external_link_status": "Prohibited",
        "discovered_at": "2026-09-04T16:00:00Z",
    },
]

MOCK_ANALYSES_DB = [
    {
        "id": "a1111111-1111-1111-1111-111111111111",
        "group_id": "11111111-1111-1111-1111-111111111111",
        "activity_status": "Active",
        "activity_score": 92,
        "external_link_status": "Allowed",
        "summary": "Thriving startup hub with high engagement.",
        "activity_summary": "15+ posts daily with fast response times.",
        "rules_summary": "Allowed links if value-adding.",
        "external_link_evidence": "Found multiple blog and Substack links.",
        "external_urls": ["https://techcrunch.com", "https://substack.com"],
        "recent_post_evidence": ["Post asking for cofounder with link"],
        "raw_evidence": {"sample_posts": 5},
        "created_at": "2026-09-01T11:00:00Z",
    }
]


# ==============================================================================
# Repository Filter & Sort Tests
# ==============================================================================

def test_query_groups_filtered_unconfigured(monkeypatch):
    """When Supabase is unconfigured, return safe empty paginated response."""
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: None)

    res = query_groups_filtered(keyword="tech", page=1, page_size=20)
    assert res["total"] == 0
    assert res["page"] == 1
    assert res["total_pages"] == 1
    assert res["groups"] == []


def test_query_groups_filtered_empty_database(monkeypatch):
    """When database has 0 records, return empty list gracefully."""
    mock_client = MagicMock()
    mock_groups_select = MagicMock()
    mock_groups_select.execute.return_value = MagicMock(data=[])
    mock_client.table.return_value.select.return_value = mock_groups_select

    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    res = query_groups_filtered()
    assert res["total"] == 0
    assert res["groups"] == []


def test_query_groups_filtered_by_niche_and_country(monkeypatch):
    """Filter records by niche and country."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_ANALYSES_DB)
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Filter by niche=Technology
    tech_res = query_groups_filtered(niche="tech")
    assert tech_res["total"] == 1
    assert tech_res["groups"][0]["name"] == "Austin Tech & Startup Founders"

    # Filter by country=UK
    uk_res = query_groups_filtered(country="UK")
    assert uk_res["total"] == 1
    assert uk_res["groups"][0]["name"] == "London Singles Community"


def test_query_groups_filtered_by_member_count_range(monkeypatch):
    """Filter records by min_members and max_members."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Min 10,000 members
    res_min = query_groups_filtered(min_members=10000)
    assert res_min["total"] == 2
    names = [g["name"] for g in res_min["groups"]]
    assert "Austin Tech & Startup Founders" in names
    assert "Digital Marketing Global Hub" in names

    # Max 1,000 members
    res_max = query_groups_filtered(max_members=1000)
    assert res_max["total"] == 1
    assert res_max["groups"][0]["name"] == "Hidden Small Community"


def test_query_groups_filtered_by_privacy_and_activity(monkeypatch):
    """Filter records by privacy and activity status."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Privacy = Private
    res_priv = query_groups_filtered(privacy="Private")
    assert res_priv["total"] == 2
    for g in res_priv["groups"]:
        assert g["privacy"] == "Private"

    # Activity = Inactive
    res_act = query_groups_filtered(activity_status="Inactive")
    assert res_act["total"] == 1
    assert res_act["groups"][0]["name"] == "Hidden Small Community"


def test_query_groups_filtered_by_keyword(monkeypatch):
    """Filter records by keyword matching name, url, or matched_keywords."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Match in matched_keywords
    res = query_groups_filtered(keyword="seo")
    assert res["total"] == 1
    assert res["groups"][0]["name"] == "Digital Marketing Global Hub"


def test_query_groups_filtered_is_analyzed(monkeypatch):
    """Filter records by whether an analysis has been performed."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_ANALYSES_DB)
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Analyzed groups only
    analyzed_res = query_groups_filtered(is_analyzed=True)
    assert analyzed_res["total"] == 1
    assert analyzed_res["groups"][0]["id"] == "11111111-1111-1111-1111-111111111111"

    # Not analyzed groups only
    not_analyzed_res = query_groups_filtered(is_analyzed=False)
    assert not_analyzed_res["total"] == 3


def test_query_groups_sorting(monkeypatch):
    """Sort records by member count, name, and discovery date."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # Member count descending
    res_mc_desc = query_groups_filtered(sort_by="member_count", sort_order="desc")
    assert res_mc_desc["groups"][0]["member_count"] == 150000
    assert res_mc_desc["groups"][-1]["member_count"] == 500

    # Member count ascending
    res_mc_asc = query_groups_filtered(sort_by="member_count", sort_order="asc")
    assert res_mc_asc["groups"][0]["member_count"] == 500
    assert res_mc_asc["groups"][-1]["member_count"] == 150000

    # Name ascending
    res_name = query_groups_filtered(sort_by="name", sort_order="asc")
    assert res_name["groups"][0]["name"] == "Austin Tech & Startup Founders"


def test_query_groups_pagination(monkeypatch):
    """Verify pagination slicing and total_pages computation."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            tbl.select.return_value.execute.return_value = MagicMock(data=MOCK_GROUPS_DB)
        elif name == "analyses":
            tbl.select.return_value.execute.return_value = MagicMock(data=[])
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # 4 items total, page_size = 2 -> 2 pages
    p1 = query_groups_filtered(page=1, page_size=2)
    assert p1["page"] == 1
    assert p1["page_size"] == 2
    assert p1["total"] == 4
    assert p1["total_pages"] == 2
    assert len(p1["groups"]) == 2

    p2 = query_groups_filtered(page=2, page_size=2)
    assert p2["page"] == 2
    assert len(p2["groups"]) == 2
    assert p1["groups"][0]["id"] != p2["groups"][0]["id"]


def test_get_group_details(monkeypatch):
    """Retrieve group and attached analysis or return None if non-existent."""
    mock_client = MagicMock()

    def mock_table(name):
        tbl = MagicMock()
        if name == "groups":
            # mock get_group_by_id (select -> eq -> limit -> execute)
            eq_mock = MagicMock()
            eq_mock.limit.return_value.execute.return_value = MagicMock(data=[MOCK_GROUPS_DB[0]])
            eq_mock.execute.return_value = MagicMock(data=[MOCK_GROUPS_DB[0]])
            tbl.select.return_value.eq.return_value = eq_mock
        elif name == "analyses":
            # mock get_analysis_for_group (select -> eq -> limit -> execute)
            eq_mock = MagicMock()
            eq_mock.limit.return_value.execute.return_value = MagicMock(data=[MOCK_ANALYSES_DB[0]])
            eq_mock.execute.return_value = MagicMock(data=[MOCK_ANALYSES_DB[0]])
            tbl.select.return_value.eq.return_value = eq_mock
        return tbl

    mock_client.table.side_effect = mock_table
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    details = get_group_details("11111111-1111-1111-1111-111111111111")
    assert details is not None
    assert details["group"]["name"] == "Austin Tech & Startup Founders"
    assert details["analysis"]["activity_score"] == 92
    assert details["analysis"]["summary"] == "Thriving startup hub with high engagement."


# ==============================================================================
# REST API Endpoint Tests
# ==============================================================================

def test_api_groups_filter_endpoint():
    """GET /api/groups/filter returns paginated filtered response."""
    client = TestClient(app)

    with patch("app.main.query_groups_filtered") as mock_query:
        mock_query.return_value = {
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "groups": [MOCK_GROUPS_DB[0]],
        }

        res = client.get("/api/groups/filter?niche=Tech&min_members=5000")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["groups"][0]["name"] == "Austin Tech & Startup Founders"


def test_api_group_details_endpoint():
    """GET /api/groups/{id}/details returns group and analysis or 404."""
    client = TestClient(app)

    with patch("app.main.get_group_details") as mock_details:
        mock_details.return_value = {
            "group": MOCK_GROUPS_DB[0],
            "analysis": MOCK_ANALYSES_DB[0],
        }

        res = client.get("/api/groups/11111111-1111-1111-1111-111111111111/details")
        assert res.status_code == 200
        data = res.json()
        assert data["group"]["name"] == "Austin Tech & Startup Founders"
        assert data["analysis"]["activity_score"] == 92

        # Test 404 for missing group
        mock_details.return_value = None
        res_404 = client.get("/api/groups/non-existent-id/details")
        assert res_404.status_code == 404
