"""Discovery package for Facebook group search, parsing, and deduplication."""
from app.discovery.models import (
    DiscoveredGroup,
    DiscoveryStartRequest,
    DiscoveryStatusResponse,
    DiscoveryResultsResponse,
)
from app.discovery.deduplicator import GroupDeduplicator, normalize_facebook_group_url
from app.discovery.group_parser import parse_member_count, parse_privacy_status
from app.discovery.facebook_search import FacebookSearchEngine
from app.discovery.group_discoverer import GroupDiscoveryService, get_discovery_service

__all__ = [
    "DiscoveredGroup",
    "DiscoveryStartRequest",
    "DiscoveryStatusResponse",
    "DiscoveryResultsResponse",
    "GroupDeduplicator",
    "normalize_facebook_group_url",
    "parse_member_count",
    "parse_privacy_status",
    "FacebookSearchEngine",
    "GroupDiscoveryService",
    "get_discovery_service",
]
