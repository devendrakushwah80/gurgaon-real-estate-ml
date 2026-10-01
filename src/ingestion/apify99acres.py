"""Apify adapter for the configured 99acres actor.

The actor is called through Apify's synchronous dataset endpoint. The adapter
accepts the actor's current field vocabulary and also preserves the complete
per-listing payload so changes in the actor output can be audited later.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv:
    load_dotenv()

from .base import FetchResult, ImageEvidence, RawListing
from .normalizer import normalize_city

DEFAULT_APIFY_BASE_URL = "https://api.apify.com/v2"
DEFAULT_ACTOR_ID = "rigelbytes~99acres-scraper"


class Apify99AcresAdapter:
    source_name = "99acres"

    def __init__(
        self,
        *,
        api_token: str | None = None,
        actor_id: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_items: int | None = None,
    ):
        self.api_token = api_token or os.getenv("APIFY_API_TOKEN", "").strip()
        self.actor_id = actor_id or os.getenv("APIFY_ACTOR_ID", DEFAULT_ACTOR_ID)
        self.base_url = (
            base_url or os.getenv("APIFY_API_BASE_URL", DEFAULT_APIFY_BASE_URL)
        ).rstrip("/")
        self.timeout_seconds = float(
            timeout_seconds or os.getenv("APIFY_SYNC_TIMEOUT_SECONDS", "300")
        )
        self.max_items = int(max_items or os.getenv("APIFY_MAX_ITEMS", "25"))
        self.property_types = [
            value.strip()
            for value in os.getenv("APIFY_PROPERTY_TYPES", "").split(",")
            if value.strip()
        ]
        self.extract_details = os.getenv("APIFY_EXTRACT_LISTING_DETAILS", "true").lower() in {
            "1",
            "true",
            "yes",
        }
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN is required for the Apify provider")

    def fetch_search(self, *, city: str, page: int, url: str | None = None) -> FetchResult:
        canonical = normalize_city(city)
        page_url = url or self.search_url(canonical, page)
        input_payload = {
            "searchQueries": [canonical.title()],
            "startUrls": [{"url": page_url}],
            "category": "buy",
            "segment": "residential",
            "extractListingDetails": self.extract_details,
            "extractAgentDetails": False,
            "maxConcurrency": 5,
            "maxItems": self.max_items,
            "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
        }
        if self.property_types:
            input_payload["propertyTypes"] = self.property_types
        actor_path = quote(self.actor_id, safe="~")
        endpoint = f"{self.base_url}/acts/{actor_path}/run-sync-get-dataset-items"
        query = urlencode({"timeout": int(self.timeout_seconds)})
        request = Request(
            f"{endpoint}?{query}",
            data=json.dumps(input_payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "EstateIQ-Apify-client/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds + 15) as response:
                body = response.read().decode("utf-8", errors="replace")
                payload = json.loads(body)
                items = _dataset_items(payload)
                listings, errors = normalize_apify_items(items, requested_city=canonical)
                return FetchResult(
                    requested_url=page_url,
                    http_status=int(response.status),
                    final_url=response.geturl(),
                    body=body,
                    listings=listings,
                    candidate_count=len(items),
                    valid_listing_count=len(listings),
                    content_hash=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    raw_payload=payload,
                    parser_errors=errors,
                )
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            message = _error_message(body, f"HTTP {error.code}")
            return FetchResult(
                page_url,
                error.code,
                error.url,
                body=body,
                blocked=error.code in {401, 403, 429},
                reason=message,
                api_error=message,
                raw_payload=_safe_json(body),
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            message = str(error)
            return FetchResult(page_url, None, None, reason=message, api_error=message)

    def fetch_detail(self, url: str, city: str) -> FetchResult:
        return FetchResult(
            url, None, url, reason="Apify dataset already supplies the exact property URL"
        )

    @staticmethod
    def search_url(city: str, page: int) -> str:
        slug = normalize_city(city).replace(" ", "-")
        return (
            f"https://www.99acres.com/search/property/buy/{slug}?preference=S&res_com=R&page={page}"
        )


def normalize_apify_items(
    items: list[Any], *, requested_city: str
) -> tuple[list[RawListing], list[str]]:
    listings: list[RawListing] = []
    errors: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"record {index}: not an object")
            continue
        listing = normalize_apify_item(item, requested_city=requested_city)
        if listing is None:
            errors.append(f"record {index}: missing exact detail URL, stable ID, or matching city")
            continue
        listings.append(listing)
    return listings, errors


def normalize_apify_item(item: dict[str, Any], *, requested_city: str) -> RawListing | None:
    city = normalize_city(
        _first(item, "city_name", "city", "contact_city_name", "location.city_name")
        or requested_city
    )
    if city != normalize_city(requested_city):
        return None
    source_url = _source_url(_first(item, "prop_details_url", "details_url", "property_url", "url"))
    source_id = _first_text(
        item, "spid", "listingId", "property_id", "propertyId", "property_number", "prop_id"
    ) or _id_from_url(source_url)
    if not source_url or not source_id:
        return None
    images = _images(
        _first(
            item,
            "property_images",
            "imageUrls",
            "images",
            "gallery_images",
            "thumbnail_images",
            "imageUrl",
        )
    )
    price = _price_crore(_first(item, "price", "formatted_price"))
    area = _area_sqft(
        _first(
            item,
            "area",
            "areaValue",
            "areaDisplay",
            "super_area",
            "superarea",
            "built_up_area",
            "builtUpArea",
            "carpetArea",
        )
    )
    fields = {
        "project_name": _first_text(
            item, "society_name", "building_name", "project_name", "projectName"
        ),
        "locality": _first_text(
            item, "locality_wo_city", "locality", "locality_name", "localitylabel"
        ),
        "city": city,
        "bhk": _integer(
            _first(item, "bedroom_num", "bedrooms", "bedRoom", "bedroom", "subtitle", "title")
        ),
        "property_type": _first_text(item, "propertyType", "property_type", "property_type_u"),
        "listing_price": price,
        "area_sqft": area,
        "price_per_sqft": _number(_first(item, "pricePerSqft", "price_per_sqft", "rate"))
        or (round(price * 10_000_000 / area, 2) if price and area else None),
        "furnishing": _first_text(item, "furnish", "furnishing", "furnishing_type"),
        "floor": _first_text(item, "floor_num", "floor"),
        "total_floors": _integer(_first(item, "totalFloors", "total_floor", "total_floors")),
        "seller_type": _first_text(
            item, "class_heading", "class_label", "seller_type", "postedBy", "seller.postedBy"
        ),
        "seller_name": _first_text(
            item,
            "contact_name",
            "seller_name",
            "contact_company_name",
            "seller.name",
            "seller.firmName",
        ),
        "verified_seller": _bool_value(
            _first(item, "is_verified", "verified", "isVerified", "seller.reraRegistered")
        ),
        "posted_date": _date_value(
            _first(
                item,
                "posting_date",
                "posting_date__u",
                "posted_date",
                "postedDate",
                "register_date_formatted",
            )
        ),
        "updated_date": _date_value(
            _first(item, "update_date", "update_date__u", "updated_date", "updatedAt")
        ),
        "description": _first_text(item, "description", "prop_description"),
        "amenities": _list_value(_first(item, "amenities", "features")),
        "latitude": _coordinate(item, "latitude", "LATITUDE"),
        "longitude": _coordinate(item, "longitude", "LONGITUDE"),
        "listing_status": _status(_first(item, "status", "availability", "listing_status")),
        "status_reason": "Apify actor does not document live availability unless a status field is returned",
    }
    fields = {key: value for key, value in fields.items() if value not in (None, "", [])}
    title = (
        _first_text(item, "prop_heading", "property_name", "title")
        or fields.get("project_name")
        or "99acres property listing"
    )
    evidence = [
        ImageEvidence(
            url=url,
            source="apify:imageUrls",
            verified_at=datetime.now(timezone.utc).isoformat(),
            match_confidence=1.0,
        )
        for url in images
    ]
    return RawListing(
        source="99acres",
        source_url=source_url,
        source_listing_id=str(source_id),
        city=city,
        title=title,
        fields=fields,
        image=evidence[0] if evidence else None,
        images=evidence,
        raw={"provider": "apify", "source_payload": item},
    )


def _dataset_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("items", "data", "results", "properties"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _dataset_items(value)
                if nested:
                    return nested
    return []


def _source_url(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.startswith("/"):
        value = f"https://www.99acres.com{value}"
    elif not value.startswith(("http://", "https://")):
        value = f"https://www.99acres.com/{value.lstrip('/')}"
    if "99acres.com" not in value.lower() or "/search/" in value.lower() or "ffid" in value.lower():
        return None
    return value.split("#", 1)[0]


def _images(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value]
    output: list[str] = []
    for item in values:
        candidate = (
            item if isinstance(item, str) else item.get("url") if isinstance(item, dict) else None
        )
        if (
            isinstance(candidate, str)
            and candidate.startswith(("http://", "https://"))
            and candidate not in output
        ):
            output.append(candidate)
    return output


def _price_crore(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        number = float(value)
        return number / 10_000_000 if number > 100_000 else number
    text = str(value or "")
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
        number
        if unit in {"cr", "crore"}
        else number / 100
        if unit in {"lac", "lakh"}
        else number / 10_000_000
    )


def _area_sqft(value: Any) -> float | None:
    text = str(value or "")
    match = re.search(
        r"([0-9][0-9,.]*)\s*(sq\.?\s*ft|sqft|sq\.?\s*m|sqm|square meters)?", text, re.I
    )
    if not match:
        return float(value) if isinstance(value, (int, float)) else None
    number = float(match.group(1).replace(",", ""))
    return number * 10.7639 if match.group(2) and "m" in match.group(2).lower() else number


def _coordinate(item: dict[str, Any], direct: str, nested: str) -> float | None:
    value = item.get(direct) or item.get(nested)
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    coords = (
        item.get("location_coordinates")
        if isinstance(item.get("location_coordinates"), dict)
        else {}
    )
    value = (
        value
        or location.get(direct)
        or location.get(nested)
        or coords.get(direct)
        or coords.get(nested)
        or coords.get(direct.lower())
    )
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _first(item: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value: Any = item
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if value not in (None, "", []):
            return value
    return None


def _first_text(item: dict[str, Any], *paths: str) -> str | None:
    value = _first(item, *paths)
    text = str(value).strip() if value is not None else ""
    return text or None


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", "")) if value not in (None, "") else None
    except ValueError:
        return None


def _integer(value: Any) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    return int(match.group(0)) if match else None


def _list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _bool_value(value: Any) -> bool | None:
    if value is None:
        return None
    return str(value).lower() in {"true", "1", "y", "yes"}


def _date_value(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat()
    return str(value).strip() if value not in (None, "") else None


def _status(value: Any) -> str:
    status = str(value or "").strip().upper()
    return (
        status if status in {"ACTIVE", "STALE", "REMOVED", "UNREACHABLE", "UNKNOWN"} else "UNKNOWN"
    )


def _id_from_url(url: str | None) -> str | None:
    match = re.search(
        r"(?:spid[-_/]|npxid[-_/]|npspid[-_/]|property[-_]?id[=/])([A-Za-z0-9]+)", url or "", re.I
    )
    return match.group(1) if match else None


def _safe_json(body: str) -> Any:
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _error_message(body: str, fallback: str) -> str:
    payload = _safe_json(body)
    if isinstance(payload, dict):
        for key in ("error", "message", "detail", "status"):
            if payload.get(key):
                return f"{fallback}: {payload[key]}"
    return fallback
