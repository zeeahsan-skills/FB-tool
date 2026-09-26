"""
Database repositories for groups and analyses persistence.
Graceful degradation: all operations return None/empty list and log errors if Supabase is unavailable.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

from app.database.supabase_client import get_supabase_client
from app.database.models import GroupAnalysis
from app.discovery.models import DiscoveredGroup
from app.discovery.deduplicator import normalize_facebook_group_url

logger = logging.getLogger("facebook_agent.repositories")


def _to_group_dict(group: Union[DiscoveredGroup, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert DiscoveredGroup or dict into Supabase-compatible payload."""
    if isinstance(group, DiscoveredGroup):
        raw_url = group.url
        canonical_url = normalize_facebook_group_url(raw_url) or raw_url
        kws = list(group.matched_keywords) if group.matched_keywords else ([group.keyword] if group.keyword else [])
        return {
            "facebook_url": canonical_url,
            "name": group.name,
            "description": None,
            "member_count": group.member_count,
            "member_count_text": group.member_count_text,
            "privacy": group.privacy,
            "niche": group.niche,
            "country": group.country,
            "source": group.source or "facebook_search",
            "matched_keywords": kws,
            "discovered_at": group.discovered_at or datetime.now(timezone.utc).isoformat(),
        }
    else:
        raw_url = group.get("facebook_url") or group.get("url", "")
        canonical_url = normalize_facebook_group_url(raw_url) or raw_url
        kws = group.get("matched_keywords") or ([group.get("keyword")] if group.get("keyword") else [])
        return {
            "facebook_url": canonical_url,
            "name": group.get("name", "Unknown Group"),
            "description": group.get("description"),
            "member_count": group.get("member_count"),
            "member_count_text": group.get("member_count_text"),
            "privacy": group.get("privacy"),
            "niche": group.get("niche"),
            "country": group.get("country"),
            "source": group.get("source", "facebook_search"),
            "matched_keywords": kws,
            "discovered_at": group.get("discovered_at") or datetime.now(timezone.utc).isoformat(),
        }


def _to_analysis_dict(analysis: Union[GroupAnalysis, Dict[str, Any]]) -> Dict[str, Any]:
    """Helper to convert GroupAnalysis or dict into Supabase-compatible payload."""
    if isinstance(analysis, GroupAnalysis):
        payload = analysis.model_dump(exclude_none=True)
    else:
        payload = dict(analysis)

    # Ensure analyzed_at is present
    if "analyzed_at" not in payload or not payload["analyzed_at"]:
        payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    return payload


# ------------------------------------------------------------------------------
# Groups Repository
# ------------------------------------------------------------------------------

def get_group_by_url(facebook_url: str) -> Optional[Dict[str, Any]]:
    """Fetches a group record by its normalized Facebook URL."""
    client = get_supabase_client()
    if client is None:
        return None

    canonical = normalize_facebook_group_url(facebook_url) or facebook_url
    try:
        res = client.table("groups").select("*").eq("facebook_url", canonical).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to query group by URL '%s': %s", canonical, e)
        return None


def get_group_by_id(group_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single group by its UUID primary key."""
    client = get_supabase_client()
    if client is None:
        return None

    try:
        res = client.table("groups").select("*").eq("id", group_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to query group by ID '%s': %s", group_id, e)
        return None


def save_discovered_group(group: Union[DiscoveredGroup, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Inserts a new discovered group into the database."""
    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase client not available. Group persistence skipped.")
        return None

    data = _to_group_dict(group)
    try:
        res = client.table("groups").insert(data).execute()
        if res.data and len(res.data) > 0:
            logger.info("Successfully persisted group: %s (%s)", data["name"], data["facebook_url"])
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to save discovered group '%s': %s", data.get("facebook_url"), e)
        return None


def upsert_discovered_group(group: Union[DiscoveredGroup, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Persists a discovered group using deduplication:
    - If URL already exists: merges matched keywords and updates metadata (member count, privacy).
    - If URL does not exist: inserts new group.
    Returns the created/updated group row, or None on failure.
    """
    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase client not available. Skipping database upsert.")
        return None

    new_data = _to_group_dict(group)
    canonical_url = new_data["facebook_url"]

    try:
        # Check if group already exists
        existing = get_group_by_url(canonical_url)

        if existing:
            # Merge matched keywords
            existing_kws = existing.get("matched_keywords") or []
            new_kws = new_data.get("matched_keywords") or []
            merged_kws = list(dict.fromkeys(existing_kws + new_kws))

            update_payload: Dict[str, Any] = {
                "matched_keywords": merged_kws,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Update name if new one is valid
            if new_data.get("name") and new_data["name"] != "Unknown Group":
                update_payload["name"] = new_data["name"]

            # Update member count if new data contains it
            if new_data.get("member_count") is not None:
                update_payload["member_count"] = new_data["member_count"]
                update_payload["member_count_text"] = new_data.get("member_count_text")

            # Update privacy if existing is unknown or missing
            existing_privacy = (existing.get("privacy") or "").lower()
            if (not existing_privacy or existing_privacy == "unknown") and new_data.get("privacy"):
                update_payload["privacy"] = new_data["privacy"]

            # Update niche / country if existing lacks them
            if not existing.get("niche") and new_data.get("niche"):
                update_payload["niche"] = new_data["niche"]
            if not existing.get("country") and new_data.get("country"):
                update_payload["country"] = new_data["country"]

            res = client.table("groups").update(update_payload).eq("id", existing["id"]).execute()
            if res.data and len(res.data) > 0:
                logger.info("Upserted (updated) group in database: %s", canonical_url)
                return res.data[0]
            return existing

        else:
            # Insert fresh group
            res = client.table("groups").insert(new_data).execute()
            if res.data and len(res.data) > 0:
                logger.info("Upserted (inserted) new group in database: %s", canonical_url)
                return res.data[0]
            return None

    except Exception as e:
        logger.error("Error upserting group '%s': %s", canonical_url, e, exc_info=True)
        return None


def list_groups(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists persisted groups ordered by discovered_at descending."""
    client = get_supabase_client()
    if client is None:
        return []

    try:
        res = (
            client.table("groups")
            .select("*")
            .order("discovered_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("Failed to list groups: %s", e)
        return []


def list_analyzed_groups(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists groups that have an associated analysis record."""
    client = get_supabase_client()
    if client is None:
        return []

    try:
        # Join groups with analyses
        res = (
            client.table("groups")
            .select("*, analyses!inner(*)")
            .order("discovered_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("Failed to list analyzed groups with inner join: %s. Falling back to ID list.", e)
        try:
            # Fallback: get group_ids from analyses
            analyses_res = client.table("analyses").select("group_id").limit(limit).execute()
            group_ids = [a["group_id"] for a in analyses_res.data or [] if a.get("group_id")]
            if not group_ids:
                return []
            res = client.table("groups").select("*").in_("id", group_ids).execute()
            return res.data or []
        except Exception as fallback_err:
            logger.error("Fallback list_analyzed_groups failed: %s", fallback_err)
            return []


# ------------------------------------------------------------------------------
# Analyses Repository
# ------------------------------------------------------------------------------

def get_analysis_for_group(group_id: str) -> Optional[Dict[str, Any]]:
    """Fetches the analysis record associated with a group ID."""
    client = get_supabase_client()
    if client is None:
        return None

    try:
        res = client.table("analyses").select("*").eq("group_id", group_id).limit(1).execute()
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to get analysis for group ID '%s': %s", group_id, e)
        return None


def save_analysis(analysis: Union[GroupAnalysis, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Inserts a new analysis record."""
    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase client not available. Analysis persistence skipped.")
        return None

    data = _to_analysis_dict(analysis)
    try:
        res = client.table("analyses").insert(data).execute()
        if res.data and len(res.data) > 0:
            logger.info("Saved analysis for group_id: %s", data.get("group_id"))
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to save analysis for group_id '%s': %s", data.get("group_id"), e)
        return None


def update_analysis(analysis_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates an existing analysis record by its ID."""
    client = get_supabase_client()
    if client is None:
        return None

    update_payload = dict(data)
    update_payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        res = client.table("analyses").update(update_payload).eq("id", analysis_id).execute()
        if res.data and len(res.data) > 0:
            logger.info("Updated analysis record ID: %s", analysis_id)
            return res.data[0]
        return None
    except Exception as e:
        logger.error("Failed to update analysis ID '%s': %s", analysis_id, e)
        return None


def upsert_analysis(analysis: Union[GroupAnalysis, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Upserts an analysis record linked to a group:
    - If an analysis already exists for group_id: updates the existing analysis.
    - If not: inserts a new analysis record.
    Prevents duplicate unlimited analysis rows for the same group.
    """
    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase client not available. Analysis upsert skipped.")
        return None

    data = _to_analysis_dict(analysis)
    group_id = data.get("group_id")
    if not group_id:
        logger.error("Cannot upsert analysis without group_id.")
        return None

    try:
        existing = get_analysis_for_group(group_id)
        if existing:
            # Update existing
            analysis_id = existing["id"]
            # Exclude id and group_id from update payload
            data_to_update = {k: v for k, v in data.items() if k not in ("id", "group_id")}
            return update_analysis(analysis_id, data_to_update)
        else:
            # Insert new
            return save_analysis(data)
    except Exception as e:
        logger.error("Error upserting analysis for group_id '%s': %s", group_id, e, exc_info=True)
        return None


def list_analyses(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists analyses ordered by analyzed_at descending."""
    client = get_supabase_client()
    if client is None:
        return []

    try:
        res = (
            client.table("analyses")
            .select("*")
            .order("analyzed_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error("Failed to list analyses: %s", e)
        return []
