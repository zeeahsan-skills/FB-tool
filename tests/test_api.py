import pytest
from starlette.testclient import TestClient
from app.main import app
from app.browser.browser_manager import BrowserManager

client = TestClient(app)


def test_health_endpoint():
    """Verify the health check endpoint returns 200 OK and expected structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "facebook-group-research-agent"


def test_browser_status_endpoint():
    """Verify the browser status endpoint responds accurately."""
    response = client.get("/api/browser/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "headless" in data
    assert "profile_dir" in data


def test_browser_manager_initialization():
    """Verify BrowserManager initializes with expected defaults."""
    bm = BrowserManager()
    assert bm.is_running is False
    assert bm.profile_dir.exists()
    assert bm.headless is False


def test_discovery_status_endpoint():
    """Verify discovery status returns expected default idle status."""
    response = client.get("/api/discovery/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert data["status"] in ["idle", "stopped", "completed"]
    assert "groups_found" in data


def test_discovery_results_endpoint():
    """Verify discovery results returns list structure."""
    response = client.get("/api/discovery/results")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "groups" in data
    assert isinstance(data["groups"], list)


def test_discovery_start_validation_empty_keywords():
    """Verify empty keywords list is rejected with 422 Unprocessable Entity."""
    response = client.post("/api/discovery/start", json={
        "niche": "Tech",
        "country": "USA",
        "keywords": []
    })
    assert response.status_code == 422


def test_discovery_stop_endpoint():
    """Verify discovery stop endpoint executes safely when idle."""
    response = client.post("/api/discovery/stop")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
