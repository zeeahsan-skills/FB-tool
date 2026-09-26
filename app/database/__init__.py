"""
Database module for Supabase persistence layer.
"""
from app.database.supabase_client import (
    get_supabase_client,
    check_supabase_connection,
    is_supabase_configured,
    reset_supabase_client,
)
from app.database.models import GroupRecord, GroupAnalysis, DatabaseStatusResponse
from app.database.repositories import (
    save_discovered_group,
    upsert_discovered_group,
    get_group_by_url,
    get_group_by_id,
    save_analysis,
    update_analysis,
    upsert_analysis,
    get_analysis_for_group,
    list_groups,
    list_analyzed_groups,
    list_analyses,
    get_group_details,
    query_groups_filtered,
)

__all__ = [
    "get_supabase_client",
    "check_supabase_connection",
    "is_supabase_configured",
    "reset_supabase_client",
    "GroupRecord",
    "GroupAnalysis",
    "DatabaseStatusResponse",
    "save_discovered_group",
    "upsert_discovered_group",
    "get_group_by_url",
    "get_group_by_id",
    "save_analysis",
    "update_analysis",
    "upsert_analysis",
    "get_analysis_for_group",
    "list_groups",
    "list_analyzed_groups",
    "list_analyses",
    "get_group_details",
    "query_groups_filtered",
]

