"""
Supabase client initialization and connectivity checking.
Security: Secrets are never exposed to the frontend or API responses.
"""
import logging
from typing import Any, Dict, Optional
from supabase import Client, create_client
from app.config import get_settings

logger = logging.getLogger("facebook_agent.database")

_client_instance: Optional[Client] = None
_client_initialized: bool = False


def is_supabase_configured() -> bool:
    """Checks whether valid Supabase credentials exist in configuration."""
    settings = get_settings()
    url = (settings.SUPABASE_URL or "").strip()
    key = (settings.SUPABASE_KEY or "").strip()
    return bool(url and key)


def get_supabase_client() -> Optional[Client]:
    """
    Returns the singleton Supabase client, or None if credentials are not configured.
    Handles initialization failures gracefully.
    """
    global _client_instance, _client_initialized

    if _client_initialized:
        return _client_instance

    if not is_supabase_configured():
        logger.info("Supabase is not configured (SUPABASE_URL / SUPABASE_KEY missing).")
        _client_instance = None
        _client_initialized = True
        return None

    settings = get_settings()
    url = settings.SUPABASE_URL.strip()
    key = settings.SUPABASE_KEY.strip()

    try:
        logger.info("Initializing Supabase client for URL: %s", url)
        _client_instance = create_client(url, key)
        _client_initialized = True
        return _client_instance
    except Exception as e:
        logger.error("Failed to initialize Supabase client: %s", e, exc_info=True)
        _client_instance = None
        _client_initialized = True
        return None


def reset_supabase_client() -> None:
    """Resets client singleton state (used in testing or when config changes)."""
    global _client_instance, _client_initialized
    _client_instance = None
    _client_initialized = False


def check_supabase_connection() -> Dict[str, bool]:
    """
    Probes Supabase connection health without exposing any credentials.
    Returns:
        {"configured": bool, "connected": bool}
    """
    configured = is_supabase_configured()
    if not configured:
        return {"configured": False, "connected": False}

    client = get_supabase_client()
    if client is None:
        return {"configured": True, "connected": False}

    try:
        # Perform lightweight probe on groups table
        response = client.table("groups").select("id").limit(1).execute()
        # If response received without exception, Supabase is connected
        return {"configured": True, "connected": True}
    except Exception as e:
        logger.warning("Supabase connection check failed: %s", e)
        return {"configured": True, "connected": False}
