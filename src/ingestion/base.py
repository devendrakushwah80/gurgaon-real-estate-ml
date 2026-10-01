"""Contracts shared by public property-source adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ImageEvidence:
    url: str
    source: str
    verified_at: str
    match_confidence: float


@dataclass
class RawListing:
    source: str
    source_url: str
    source_listing_id: str | None
    city: str
    title: str
    fields: dict[str, Any] = field(default_factory=dict)
    image: ImageEvidence | None = None
    images: list[ImageEvidence] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResult:
    requested_url: str
    http_status: int | None
    final_url: str | None
    body: str = ""
    blocked: bool = False
    reason: str | None = None
    listing: RawListing | None = None
    listings: list[RawListing] = field(default_factory=list)
    candidate_count: int = 0
    valid_listing_count: int = 0
    content_hash: str | None = None
    parser_errors: list[str] = field(default_factory=list)
    raw_payload: Any | None = None
    api_error: str | None = None


class SourceAdapter(Protocol):
    source_name: str

    def fetch_search(self, *, city: str, page: int, url: str | None = None) -> FetchResult: ...

    def fetch_detail(self, url: str, city: str) -> FetchResult: ...
