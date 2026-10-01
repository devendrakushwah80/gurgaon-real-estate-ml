"""Conservative listing freshness classification."""

from __future__ import annotations

from enum import StrEnum


class ListingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    REMOVED = "REMOVED"
    UNREACHABLE = "UNREACHABLE"
    UNKNOWN = "UNKNOWN"


def classify_fetch(
    *, http_status: int | None, body: str = "", blocked: bool = False
) -> tuple[ListingStatus, str]:
    if blocked:
        return ListingStatus.UNREACHABLE, "Source access was blocked or disallowed"
    if http_status in (404, 410):
        return ListingStatus.REMOVED, f"Source returned HTTP {http_status}"
    if http_status is None or http_status >= 500:
        return ListingStatus.UNREACHABLE, f"Source returned HTTP {http_status or 'no response'}"
    if http_status != 200:
        return ListingStatus.UNKNOWN, f"Source returned HTTP {http_status}"
    lowered = body.lower()
    if any(
        marker in lowered
        for marker in (
            "property is no longer available",
            "listing has been removed",
            "page not found",
        )
    ):
        return (
            ListingStatus.REMOVED,
            "Page content indicates that the listing is no longer available",
        )
    return ListingStatus.ACTIVE, "Listing page responded successfully"
