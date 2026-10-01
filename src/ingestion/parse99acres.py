"""Parse marketplace adapter for the documented 99acres API wrapper."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is present in the project environment
    load_dotenv = None

if load_dotenv:
    load_dotenv()

from .base import FetchResult, ImageEvidence, RawListing
from .normalizer import normalize_city

DEFAULT_PARSE_BASE_URL = "https://api.parse.bot/scraper/18b931b9-d4d5-4c8d-a72f-6bcbb55663da"


class Parse99AcresAdapter:
    """Fetch one page of structured listings from Parse's 99acres endpoint."""

    source_name = "99acres"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        search_path: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key or os.getenv("PARSE_99ACRES_API_KEY", "").strip()
        self.base_url = (
            base_url or os.getenv("PARSE_99ACRES_API_BASE_URL", DEFAULT_PARSE_BASE_URL)
        ).rstrip("/")
        self.search_path = (
            search_path or os.getenv("PARSE_99ACRES_SEARCH_PATH", "search_properties")
        ).strip("/")
        self.transaction_type = os.getenv("PARSE_99ACRES_TRANSACTION_TYPE", "buy")
        self.property_type_filter = os.getenv("PARSE_99ACRES_PROPERTY_TYPE", "residential")
        self.timeout_seconds = timeout_seconds
        if not self.api_key:
            raise ValueError("PARSE_99ACRES_API_KEY is required for the Parse provider")

    def fetch_search(self, *, city: str, page: int, url: str | None = None) -> FetchResult:
        canonical = normalize_city(city)
        params = {
            "page": page,
            "location": canonical,
            "property_type": self.property_type_filter,
            "transaction_type": self.transaction_type,
        }
        url = f"{self.base_url}/{self.search_path}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "X-API-Key": self.api_key,
                "Accept": "application/json",
                "User-Agent": "EstateIQ-Parse-client/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body)
                listings, invalid = normalize_response(payload, requested_city=canonical)
                content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
                return FetchResult(
                    requested_url=url,
                    http_status=int(response.status),
                    final_url=response.geturl(),
                    body=body,
                    listings=listings,
                    candidate_count=len(_properties_payload(payload)),
                    valid_listing_count=len(listings),
                    content_hash=content_hash,
                    raw_payload=payload,
                    parser_errors=invalid,
                )
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            message = _api_error_message(body, f"HTTP {error.code}")
            return FetchResult(
                url,
                error.code,
                error.url,
                body=body,
                blocked=error.code in {401, 403, 429},
                reason=message,
                api_error=message,
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            message = str(error)
            return FetchResult(url, None, None, reason=message, api_error=message)

    def fetch_detail(self, url: str, city: str) -> FetchResult:
        """Parse has no documented single-property endpoint for resale listings.

        Search results already include the exact ``details_url``. We therefore
        do not spend an extra API credit on an undocumented detail call.
        """

        return FetchResult(
            url, None, url, reason="Parse search response is the documented property contract"
        )


def normalize_response(payload: Any, *, requested_city: str) -> tuple[list[RawListing], list[str]]:
    """Normalize only the fields documented by Parse's response schema."""

    properties = _properties_payload(payload)
    listings: list[RawListing] = []
    errors: list[str] = []
    for index, item in enumerate(properties):
        if not isinstance(item, dict):
            errors.append(f"record {index}: not an object")
            continue
        listing = normalize_property(item, requested_city=requested_city)
        if listing is None:
            errors.append(f"record {index}: missing valid property_id/details_url or city mismatch")
            continue
        listings.append(listing)
    return listings, errors


def normalize_property(item: dict[str, Any], *, requested_city: str) -> RawListing | None:
    source_id = _text(item.get("property_id"))
    source_url = _exact_source_url(item.get("details_url"))
    city = normalize_city(item.get("city") or requested_city)
    if not source_id and not source_url:
        return None
    if city != normalize_city(requested_city):
        return None
    if not source_url:
        return None
    images = _image_evidence(item.get("images"))
    fields: dict[str, Any] = {
        "project_name": _text(
            item.get("project_name") or item.get("society_name") or item.get("building_name")
        ),
        "locality": _text(item.get("locality")),
        "city": city,
        "bhk": _integer(item.get("bedrooms")),
        "property_type": _text(item.get("property_type")),
        "listing_price": _price_crore(item.get("price")),
        "area_sqft": _area_sqft(item.get("area")),
        "furnishing": _text(item.get("furnishing")),
        "floor": _text(item.get("floor")),
        "total_floors": _integer(item.get("total_floor") or item.get("total_floors")),
        "seller_type": _text(item.get("seller_name")),
        "verified_seller": bool(item.get("is_verified"))
        if item.get("is_verified") is not None
        else None,
        "posted_date": _text(item.get("posted_date")),
        "updated_date": _text(item.get("updated_date")),
        "description": _text(item.get("description")),
        "amenities": _amenities(item.get("amenities")),
        "latitude": _coordinate(item.get("location_coordinates"), "LATITUDE"),
        "longitude": _coordinate(item.get("location_coordinates"), "LONGITUDE"),
        "price_per_sqft": _price_per_sqft(item.get("price"), item.get("area")),
        "listing_status": _status(item.get("status")),
        "status_reason": "Parse response does not document live availability status"
        if not item.get("status")
        else "Status supplied by Parse response",
    }
    fields = {key: value for key, value in fields.items() if value not in (None, "", [])}
    title = (
        _text(item.get("property_name")) or fields.get("project_name") or "99acres property listing"
    )
    raw = {"provider": "parse", "schema_fields": sorted(item.keys()), "source_payload": item}
    return RawListing(
        source="99acres",
        source_url=source_url,
        source_listing_id=source_id,
        city=city,
        title=title,
        fields=fields,
        image=images[0] if images else None,
        images=images,
        raw=raw,
    )


def _properties_payload(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", payload)
    if isinstance(data, dict) and isinstance(data.get("properties"), list):
        return data["properties"]
    if isinstance(payload.get("properties"), list):
        return payload["properties"]
    return []


def _exact_source_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return None
    parsed = urlsplit(value)
    if (
        "99acres.com" not in parsed.netloc.lower()
        or not parsed.path
        or "ffid" in parsed.path.lower()
        or parsed.path.lower().startswith("/search/")
    ):
        return None
    return value.split("#", 1)[0]


def _image_evidence(value: Any) -> list[ImageEvidence]:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = [
            item if isinstance(item, str) else item.get("url")
            for item in value
            if isinstance(item, (str, dict))
        ]
    else:
        values = []
    now = datetime.now(timezone.utc).isoformat()
    output: list[ImageEvidence] = []
    for image_url in values:
        if (
            isinstance(image_url, str)
            and image_url.startswith(("http://", "https://"))
            and image_url not in {item.url for item in output}
        ):
            output.append(
                ImageEvidence(
                    url=image_url,
                    source="parse:listing.images",
                    verified_at=now,
                    match_confidence=1.0,
                )
            )
    return output


def _price_crore(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 10_000_000 if number > 100_000 else number
    text = _text(value)
    if not text:
        return None
    match = re.search(r"([0-9][0-9,.]*)", text, re.I)
    if not match:
        return None
    try:
        number = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    unit_match = re.search(r"\b(Cr|Crore|Lac|Lakh|L)\b", text, re.I)
    unit = (unit_match.group(1) if unit_match else "INR").lower()
    return float(
        number / Decimal("100")
        if unit in {"l", "lac", "lakh"}
        else number
        if unit in {"cr", "crore"}
        else number / Decimal("10000000")
    )


def _area_sqft(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value)
    match = re.search(r"([0-9][0-9,.]*)\s*(sq\.?\s*ft|sqft|square feet)?", text or "", re.I)
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    if match.group(2) and "meter" in match.group(2).lower():
        number *= 10.7639
    return number


def _price_per_sqft(price: Any, area: Any) -> float | None:
    price_crore = _price_crore(price)
    area_sqft = _area_sqft(area)
    return round(price_crore * 10_000_000 / area_sqft, 2) if price_crore and area_sqft else None


def _coordinate(value: Any, key: str) -> float | None:
    if not isinstance(value, dict):
        return None
    try:
        return float(value.get(key) or value.get(key.lower()))
    except (TypeError, ValueError):
        return None


def _amenities(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _integer(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _status(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return (
        normalized
        if normalized in {"ACTIVE", "STALE", "REMOVED", "UNREACHABLE", "UNKNOWN"}
        else "UNKNOWN"
    )


def _api_error_message(body: str, fallback: str) -> str:
    try:
        payload = json.loads(body)
        if isinstance(payload, dict):
            for key in ("error", "message", "detail", "status"):
                if payload.get(key):
                    return f"{fallback}: {payload[key]}"
    except json.JSONDecodeError:
        pass
    return fallback
