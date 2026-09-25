from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class DiscoveredGroup(BaseModel):
    """
    Representation of a Facebook group found during discovery.
    Strictly follows data accuracy rules: missing fields are None or 'unknown', not guessed.
    """
    name: str = Field(..., description="Display name of the group")
    url: str = Field(..., description="Normalized URL pointing to the group")
    member_count: Optional[int] = Field(None, description="Parsed integer member count, or None if unparseable")
    member_count_text: Optional[str] = Field(None, description="Exact visible member count string (e.g. '125K members')")
    privacy: Optional[str] = Field(None, description="'Public', 'Private', or 'Unknown'")
    keyword: str = Field(..., description="Initial search keyword that found this group")
    niche: str = Field(..., description="Research niche")
    country: str = Field(..., description="Target country/region")
    source: str = Field("facebook_search", description="Data origin")
    discovered_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of discovery"
    )
    matched_keywords: List[str] = Field(
        default_factory=list,
        description="All keywords that yielded this group during discovery"
    )

    def model_post_init(self, __context):
        if not self.matched_keywords and self.keyword:
            self.matched_keywords = [self.keyword]


class DiscoveryStartRequest(BaseModel):
    """Payload to start a group discovery job."""
    niche: str = Field(..., min_length=1, max_length=100, description="Target niche (e.g. Dating)")
    country: str = Field(..., min_length=1, max_length=100, description="Target country or region (e.g. USA)")
    keywords: List[str] = Field(..., min_length=1, description="List of search queries")
    max_results_per_keyword: Optional[int] = Field(50, ge=1, le=200, description="Max results per keyword batch")
    scroll_count: Optional[int] = Field(5, ge=1, le=30, description="Number of scroll batches per keyword")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        cleaned = [k.strip() for k in v if k and k.strip()]
        if not cleaned:
            raise ValueError("Keywords list must contain at least one non-empty search term.")
        if len(cleaned) > 50:
            raise ValueError("Maximum 50 keywords allowed per discovery run.")
        return cleaned


class DiscoveryStatusResponse(BaseModel):
    """Current execution status of the background discovery engine."""
    running: bool
    status: str = Field(..., description="'idle', 'searching', 'completed', 'stopped', 'error'")
    current_keyword: Optional[str] = None
    keywords_completed: int = 0
    keywords_total: int = 0
    groups_found: int = 0
    error: Optional[str] = None


class DiscoveryResultsResponse(BaseModel):
    """Full discovery results listing."""
    total: int
    status: str
    groups: List[DiscoveredGroup]
