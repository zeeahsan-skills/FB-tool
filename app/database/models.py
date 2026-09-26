"""
Database models and schemas for Supabase persistence.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GroupRecord(BaseModel):
    """Represents a persisted Facebook group entity."""
    id: Optional[str] = None
    facebook_url: str
    name: str
    description: Optional[str] = None
    member_count: Optional[int] = None
    member_count_text: Optional[str] = None
    privacy: Optional[str] = None
    niche: Optional[str] = None
    country: Optional[str] = None
    source: str = "facebook_search"
    matched_keywords: List[str] = Field(default_factory=list)
    discovered_at: Optional[str] = None
    updated_at: Optional[str] = None


class GroupAnalysis(BaseModel):
    """
    Represents Gemini LLM analysis and audit data for a group.
    Matches Prompt 3 & 4 data architecture.
    """
    id: Optional[str] = None
    group_id: str = Field(..., description="Foreign key reference to groups.id")
    activity_status: Optional[str] = Field(
        None, description="'Active', 'Moderate', 'Inactive', or 'Unknown'"
    )
    activity_score: Optional[float] = Field(
        None, description="Numeric score e.g. 0.0 - 100.0 or 1.0 - 10.0"
    )
    external_link_status: Optional[str] = Field(
        None, description="'Allowed', 'Restricted', 'Prohibited', or 'Unknown'"
    )
    external_link_evidence: Optional[str] = Field(
        None, description="Evidence summary of external link policy/behavior"
    )
    rules_summary: Optional[str] = Field(
        None, description="Summary of parsed group rules"
    )
    activity_summary: Optional[str] = Field(
        None, description="Summary of recent post frequency and member engagement"
    )
    overall_summary: Optional[str] = Field(
        None, description="Holistic Gemini intelligence summary"
    )
    rules_evidence: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Parsed raw rules structure"
    )
    recent_posts_evidence: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Raw posts extracted for evidence"
    )
    external_urls: Optional[List[str]] = Field(
        default_factory=list, description="Detected external links in posts/rules"
    )
    analysis_raw_json: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Raw structured Gemini JSON payload"
    )
    analyzed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of analysis"
    )
    updated_at: Optional[str] = None


class DatabaseStatusResponse(BaseModel):
    """Response model for /api/database/status."""
    configured: bool
    connected: bool
