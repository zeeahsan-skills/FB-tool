import pytest
from pathlib import Path
from app.config import Settings, get_settings


def test_settings_load_defaults():
    """Verify default configurations load accurately."""
    settings = Settings()
    assert settings.APP_ENV in ["development", "production", "test"]
    assert settings.APP_HOST == "127.0.0.1"
    assert settings.APP_PORT == 8000
    assert settings.BROWSER_HEADLESS is False
    assert "browser-profile" in settings.BROWSER_USER_DATA_DIR


def test_settings_browser_dir_resolution():
    """Verify browser profile directory resolves to an absolute path."""
    settings = Settings(BROWSER_USER_DATA_DIR="./data/test-browser-profile")
    resolved = settings.resolved_browser_profile_dir
    assert resolved.is_absolute()
    assert resolved.exists()
    # Cleanup test directory
    try:
        resolved.rmdir()
    except Exception:
        pass


def test_get_settings_singleton():
    """Verify get_settings returns consistent cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
