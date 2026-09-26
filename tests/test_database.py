"""
Unit tests for Supabase database persistence layer.
Mocks all external network/Supabase calls so tests run cleanly and offline.
"""
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.config import Settings
from app.discovery.models import DiscoveredGroup
from app.database.models import GroupAnalysis, DatabaseStatusResponse
from app.database import (
    is_supabase_configured,
    get_supabase_client,
    check_supabase_connection,
    reset_supabase_client,
    save_discovered_group,
    upsert_discovered_group,
    get_group_by_url,
    get_group_by_id,
    save_analysis,
    update_analysis,
    upsert_analysis,
    get_analysis_for_group,
    list_groups,
    list_analyses,
)


@pytest.fixture(autouse=True)
def clean_client_state():
    """Resets client singleton state before and after each test."""
    reset_supabase_client()
    yield
    reset_supabase_client()


# ==============================================================================
# Configuration & Connection Status Tests
# ==============================================================================

def test_supabase_unconfigured(monkeypatch):
    """When credentials are blank/missing, client is None and status is unconfigured."""
    dummy_settings = Settings(SUPABASE_URL=None, SUPABASE_KEY=None)
    monkeypatch.setattr("app.database.supabase_client.get_settings", lambda: dummy_settings)
    monkeypatch.setattr("app.config.get_settings", lambda: dummy_settings)

    assert is_supabase_configured() is False
    assert get_supabase_client() is None

    status = check_supabase_connection()
    assert status == {"configured": False, "connected": False}


def test_api_database_status_unconfigured(monkeypatch):
    """API endpoint /api/database/status returns configured: false, connected: false."""
    dummy_settings = Settings(SUPABASE_URL="", SUPABASE_KEY="")
    monkeypatch.setattr("app.database.supabase_client.get_settings", lambda: dummy_settings)
    monkeypatch.setattr("app.config.get_settings", lambda: dummy_settings)

    client = TestClient(app)
    res = client.get("/api/database/status")
    assert res.status_code == 200
    data = res.json()
    assert data["configured"] is False
    assert data["connected"] is False


def test_supabase_configured_connected_mock(monkeypatch):
    """When credentials exist and Supabase probe succeeds, status is connected."""
    dummy_settings = Settings(SUPABASE_URL="https://xyz.supabase.co", SUPABASE_KEY="secret-anon-key")
    monkeypatch.setattr("app.database.supabase_client.get_settings", lambda: dummy_settings)

    mock_client = MagicMock()
    # mock table("groups").select("id").limit(1).execute()
    mock_execute = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_execute

    with patch("app.database.supabase_client.create_client", return_value=mock_client):
        status = check_supabase_connection()
        assert status == {"configured": True, "connected": True}


def test_supabase_configured_unreachable_mock(monkeypatch):
    """When credentials exist but Supabase probe raises network/auth error, connected is false."""
    dummy_settings = Settings(SUPABASE_URL="https://xyz.supabase.co", SUPABASE_KEY="secret-anon-key")
    monkeypatch.setattr("app.database.supabase_client.get_settings", lambda: dummy_settings)

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = ConnectionError("Supabase timeout")

    with patch("app.database.supabase_client.create_client", return_value=mock_client):
        status = check_supabase_connection()
        assert status == {"configured": True, "connected": False}


# ==============================================================================
# Graceful Degradation Tests
# ==============================================================================

def test_graceful_degradation_when_unconfigured(monkeypatch):
    """All repository operations return None or empty list without throwing when unconfigured."""
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: None)
    group = DiscoveredGroup(
        name="Dallas Network",
        url="https://www.facebook.com/groups/dallasnetwork",
        keyword="dallas",
        niche="Local",
        country="USA"
    )

    assert save_discovered_group(group) is None
    assert upsert_discovered_group(group) is None
    assert get_group_by_url(group.url) is None
    assert get_group_by_id("fake-uuid") is None
    assert list_groups() == []
    assert get_analysis_for_group("fake-uuid") is None
    assert save_analysis({"group_id": "fake-uuid"}) is None
    assert upsert_analysis({"group_id": "fake-uuid"}) is None
    assert list_analyses() == []


def test_graceful_degradation_on_supabase_exception(monkeypatch):
    """Database exceptions during upsert are caught and logged, not raised."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.side_effect = RuntimeError("Supabase cluster unreachable")
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    group = DiscoveredGroup(
        name="Austin Tech",
        url="https://www.facebook.com/groups/austintech",
        keyword="austin tech",
        niche="Tech",
        country="USA"
    )

    # Must return None rather than raising an unhandled exception
    res = upsert_discovered_group(group)
    assert res is None


# ==============================================================================
# Group Upsert & Matched Keyword Merging Tests
# ==============================================================================

def test_upsert_discovered_group_insert_new(monkeypatch):
    """When a group is new, upsert inserts a new row with normalized canonical URL."""
    mock_client = MagicMock()

    # Query for existing returns empty
    select_exec = MagicMock(data=[])
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = select_exec

    # Insert returns created row
    inserted_row = {
        "id": "11111111-2222-3333-4444-555555555555",
        "facebook_url": "https://www.facebook.com/groups/techconnect",
        "name": "Tech Connect USA",
        "member_count": 50000,
        "member_count_text": "50K members",
        "privacy": "Public",
        "niche": "Technology",
        "country": "USA",
        "source": "facebook_search",
        "matched_keywords": ["tech jobs"],
    }
    insert_exec = MagicMock(data=[inserted_row])
    mock_client.table.return_value.insert.return_value.execute.return_value = insert_exec

    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    group = DiscoveredGroup(
        name="Tech Connect USA",
        url="https://m.facebook.com/groups/techconnect/?ref=share",
        member_count=50000,
        member_count_text="50K members",
        privacy="Public",
        keyword="tech jobs",
        niche="Technology",
        country="USA",
    )

    result = upsert_discovered_group(group)
    assert result is not None
    assert result["id"] == "11111111-2222-3333-4444-555555555555"
    assert result["facebook_url"] == "https://www.facebook.com/groups/techconnect"
    assert result["matched_keywords"] == ["tech jobs"]


def test_upsert_discovered_group_merge_keywords(monkeypatch):
    """When group already exists, upsert merges matched keywords and updates metadata."""
    mock_client = MagicMock()

    # Existing group in DB
    existing_row = {
        "id": "group-uuid-999",
        "facebook_url": "https://www.facebook.com/groups/singlescafe",
        "name": "Singles Cafe",
        "member_count": None,
        "member_count_text": None,
        "privacy": "Unknown",
        "niche": "Dating",
        "country": "USA",
        "matched_keywords": ["dating meetup"],
    }

    # Query for existing returns existing_row
    select_exec = MagicMock(data=[existing_row])
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = select_exec

    # Update returns updated row with merged keywords and updated member count
    updated_row = dict(existing_row)
    updated_row["matched_keywords"] = ["dating meetup", "speed dating"]
    updated_row["member_count"] = 12000
    updated_row["member_count_text"] = "12K members"
    updated_row["privacy"] = "Public"
    update_exec = MagicMock(data=[updated_row])
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = update_exec

    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    second_group = DiscoveredGroup(
        name="Singles Cafe",
        url="https://www.facebook.com/groups/singlescafe/",
        member_count=12000,
        member_count_text="12K members",
        privacy="Public",
        keyword="speed dating",
        niche="Dating",
        country="USA",
        matched_keywords=["speed dating"]
    )

    result = upsert_discovered_group(second_group)
    assert result is not None
    assert "dating meetup" in result["matched_keywords"]
    assert "speed dating" in result["matched_keywords"]
    assert result["member_count"] == 12000
    assert result["privacy"] == "Public"


# ==============================================================================
# Analysis Model & Persistence Tests
# ==============================================================================

def test_analysis_model_mapping_and_jsonb_preservation():
    """Verify GroupAnalysis Pydantic model serializes structured evidence properly."""
    analysis = GroupAnalysis(
        group_id="group-uuid-123",
        activity_status="Active",
        activity_score=85.5,
        external_link_status="Allowed",
        external_link_evidence="Links to blog and community resources permitted in designated threads.",
        rules_summary="No spam. Keep posts relevant.",
        activity_summary="25 posts per day, high comments.",
        overall_summary="Healthy niche community with organic discussions.",
        rules_evidence={"parsed_rules": ["Be respectful", "No commercial spam"]},
        recent_posts_evidence=[{"text": "Check this guide", "links": ["https://example.com/guide"]}],
        external_urls=["https://example.com/guide"],
        analysis_raw_json={"score": 85.5, "model": "gemini-1.5-flash"},
    )

    dump = analysis.model_dump()
    assert dump["group_id"] == "group-uuid-123"
    assert dump["activity_score"] == 85.5
    assert dump["activity_status"] == "Active"
    assert dump["external_urls"] == ["https://example.com/guide"]
    assert "parsed_rules" in dump["rules_evidence"]
    assert len(dump["recent_posts_evidence"]) == 1


def test_upsert_analysis_new_and_update(monkeypatch):
    """Analysis upsert inserts when new and updates when existing record is present."""
    mock_client = MagicMock()
    monkeypatch.setattr("app.database.repositories.get_supabase_client", lambda: mock_client)

    # 1. New analysis (existing is empty)
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    created_analysis = {
        "id": "analysis-1",
        "group_id": "group-1",
        "activity_status": "Active",
        "activity_score": 90.0,
    }
    mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[created_analysis])

    analysis_new = GroupAnalysis(group_id="group-1", activity_status="Active", activity_score=90.0)
    saved = upsert_analysis(analysis_new)
    assert saved["id"] == "analysis-1"

    # 2. Update analysis (existing found)
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[created_analysis])
    updated_analysis = dict(created_analysis)
    updated_analysis["activity_score"] = 95.0
    mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[updated_analysis])

    analysis_update = GroupAnalysis(group_id="group-1", activity_status="Active", activity_score=95.0)
    res_update = upsert_analysis(analysis_update)
    assert res_update["activity_score"] == 95.0


# ==============================================================================
# API Endpoints Tests
# ==============================================================================

def test_api_get_groups(monkeypatch):
    """GET /api/groups returns persisted groups list."""
    mock_groups = [
        {"id": "g-1", "name": "Group One", "facebook_url": "https://www.facebook.com/groups/1"},
        {"id": "g-2", "name": "Group Two", "facebook_url": "https://www.facebook.com/groups/2"}
    ]
    monkeypatch.setattr("app.main.list_groups", lambda limit, offset: mock_groups)

    client = TestClient(app)
    res = client.get("/api/groups")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["name"] == "Group One"


def test_api_get_group_by_id(monkeypatch):
    """GET /api/groups/{group_id} returns 200 when found and 404 when missing."""
    mock_group = {"id": "g-1", "name": "Group One", "facebook_url": "https://www.facebook.com/groups/1"}
    monkeypatch.setattr("app.main.get_group_by_id", lambda gid: mock_group if gid == "g-1" else None)

    client = TestClient(app)
    res_ok = client.get("/api/groups/g-1")
    assert res_ok.status_code == 200
    assert res_ok.json()["id"] == "g-1"

    res_missing = client.get("/api/groups/unknown-id")
    assert res_missing.status_code == 404


def test_api_get_group_analysis(monkeypatch):
    """GET /api/groups/{group_id}/analysis returns analysis or 404."""
    mock_analysis = {
        "id": "a-1",
        "group_id": "g-1",
        "activity_status": "Active",
        "activity_score": 88.0,
        "rules_summary": "No spam"
    }
    monkeypatch.setattr("app.main.get_analysis_for_group", lambda gid: mock_analysis if gid == "g-1" else None)

    client = TestClient(app)
    res_ok = client.get("/api/groups/g-1/analysis")
    assert res_ok.status_code == 200
    assert res_ok.json()["activity_status"] == "Active"

    res_missing = client.get("/api/groups/no-analysis/analysis")
    assert res_missing.status_code == 404


def test_api_list_analyses(monkeypatch):
    """GET /api/analyses returns analyses list."""
    mock_analyses = [
        {"id": "a-1", "group_id": "g-1", "activity_status": "Active"},
        {"id": "a-2", "group_id": "g-2", "activity_status": "Moderate"}
    ]
    monkeypatch.setattr("app.main.list_analyses", lambda limit, offset: mock_analyses)

    client = TestClient(app)
    res = client.get("/api/analyses")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_api_get_analyzed_groups(monkeypatch):
    """GET /api/groups/analyzed returns list of groups with analysis attached."""
    mock_analyzed = [
        {"id": "g-1", "name": "Group One", "analyses": [{"id": "a-1", "activity_status": "Active"}]}
    ]
    monkeypatch.setattr("app.main.list_analyzed_groups", lambda limit, offset: mock_analyzed)

    client = TestClient(app)
    res = client.get("/api/groups/analyzed")
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_api_save_group_analysis(monkeypatch):
    """POST /api/groups/{group_id}/analysis persists analysis and returns it."""
    mock_saved = {
        "id": "a-new",
        "group_id": "g-1",
        "activity_status": "Active",
        "activity_score": 92.0
    }
    monkeypatch.setattr("app.main.upsert_analysis", lambda payload: mock_saved)

    client = TestClient(app)
    payload = {
        "group_id": "g-1",
        "activity_status": "Active",
        "activity_score": 92.0
    }
    res = client.post("/api/groups/g-1/analysis", json=payload)
    assert res.status_code == 200
    assert res.json()["id"] == "a-new"
