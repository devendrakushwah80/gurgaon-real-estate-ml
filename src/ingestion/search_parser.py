"""Structure-first parser for 99acres search responses.

It never turns the search page itself into a property. A candidate must have
an exact detail URL, preferably with the stable ``spid`` identifier used by
99acres. The parser deliberately uses generic URL and JSON signals instead of
generated CSS class names.
"""

from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

from .base import ImageEvidence, RawListing
from .normalizer import normalize_city


@dataclass
class SearchParseResult:
    listings: list[RawListing] = field(default_factory=list)
    candidate_cards: int = 0
    invalid_urls: int = 0
    content_hash: str = ""
    page_metadata: dict[str, Any] = field(default_factory=dict)
    parser_errors: list[str] = field(default_factory=list)


def parse_search_page(body: str, *, page_url: str, city: str) -> SearchParseResult:
    result = SearchParseResult(
        content_hash=hashlib.sha256(body.encode("utf-8", errors="replace")).hexdigest()
    )
    canonical_city = normalize_city(city)
    candidates: dict[str, RawListing] = {}
    result.page_metadata = {
        "title": _meta_value(body, "og:title") or _title(body),
        "canonical": _canonical(body),
    }

    for payload in _script_payloads(body):
        for item in _candidate_dicts(payload, page_url):
            url = _detail_url(
                item.get("url") or item.get("urlAbsolute") or item.get("link"), page_url
            )
            if not url:
                continue
            result.candidate_cards += 1
            listing = _listing_from_dict(item, url=url, city=canonical_city)
            candidates.setdefault(url, listing)

    anchors = _AnchorParser()
    anchors.feed(body)
    result.candidate_cards += sum(1 for href, _ in anchors.hrefs if _detail_url(href, page_url))
    for href, text in anchors.hrefs:
        url = _detail_url(href, page_url)
        if not url:
            if _looks_like_listing_href(href):
                result.invalid_urls += 1
            continue
        context = _context_for_href(body, href)
        fields = _quick_fields(context + " " + text)
        listing = RawListing(
            source="99acres",
            source_url=url,
            source_listing_id=source_id_from_url(url),
            city=canonical_city,
            title=text.strip() or fields.get("title") or "99acres listing",
            fields=fields,
            raw={"search_page_url": page_url, "extraction": "href"},
        )
        if url in candidates:
            candidates[url].fields = {**listing.fields, **candidates[url].fields}
            if candidates[url].title == "99acres listing":
                candidates[url].title = listing.title
        else:
            candidates[url] = listing

    result.listings = list(candidates.values())
    return result


def parse_detail_page(body: str, *, detail_url: str, city: str) -> RawListing | None:
    canonical_city = normalize_city(city)
    payloads = list(_script_payloads(body))
    best: dict[str, Any] = {}
    for payload in payloads:
        for item in _candidate_dicts(payload, detail_url):
            best = {**best, **item}
            if item.get("name") or item.get("title") or item.get("propertyName"):
                break
    fields = _quick_fields(body)
    fields.update(_map_fields(best))
    title = str(
        best.get("name")
        or best.get("title")
        or fields.get("title")
        or _meta_value(body, "og:title")
        or _title(body)
        or "99acres listing"
    ).strip()
    images = _image_urls_from_payloads(payloads)
    if not images:
        images = _meta_images(body)
    source_id = (
        source_id_from_url(detail_url)
        or str(best.get("propertyId") or best.get("id") or "")
        or None
    )
    if not source_id and not _detail_url(detail_url, detail_url):
        return None
    now = datetime.now(timezone.utc).isoformat()
    image_evidence = [
        ImageEvidence(url=url, source="detail:embedded", verified_at=now, match_confidence=1.0)
        for url in images
    ]
    return RawListing(
        source="99acres",
        source_url=detail_url,
        source_listing_id=source_id,
        city=canonical_city,
        title=title,
        fields=fields,
        image=image_evidence[0] if image_evidence else None,
        images=image_evidence,
        raw={
            "detail_url": detail_url,
            "extraction": "detail_structured_data",
            "image_count": len(images),
        },
    )


def source_id_from_url(url: str) -> str | None:
    match = re.search(r"(?:spid[-_/]|property[-_]?id[=/])([A-Za-z0-9]+)", url, re.I)
    return match.group(1) if match else None


def _detail_url(value: object, page_url: str) -> str | None:
    if not value or not isinstance(value, str):
        return None
    value = html_lib.unescape(value).replace("\\/", "/").strip()
    absolute = urljoin(page_url, value)
    parts = urlsplit(absolute)
    if parts.scheme not in {"http", "https"} or "99acres.com" not in parts.netloc.lower():
        return None
    path = parts.path.lower()
    if "-ffid" in path or path.startswith("/search/") or path in {"", "/"}:
        return None
    if not ("spid-" in path or "property-detail" in path or "/property/" in path):
        return None
    return absolute.split("#", 1)[0]


def _looks_like_listing_href(href: str) -> bool:
    return "99acres" in href.lower() and ("spid" in href.lower() or "property" in href.lower())


def _script_payloads(body: str):
    pattern = r"<script(?:[^>]*?)>(.*?)</script>"
    for block in re.findall(pattern, body, re.I | re.S):
        text = html_lib.unescape(block).strip()
        if not text or not (text.startswith("{") or text.startswith("[")):
            continue
        try:
            yield json.loads(text)
        except json.JSONDecodeError:
            # Some state blobs are JavaScript assignments; isolate the first
            # balanced JSON object without executing page JavaScript.
            start = min(
                [index for index in (text.find("{"), text.find("[")) if index >= 0], default=-1
            )
            if start >= 0:
                try:
                    yield json.JSONDecoder().raw_decode(text[start:])[0]
                except json.JSONDecodeError:
                    continue


def _candidate_dicts(value: Any, page_url: str):
    if isinstance(value, dict):
        if _detail_url(value.get("url") or value.get("urlAbsolute") or value.get("link"), page_url):
            yield value
        for nested in value.values():
            yield from _candidate_dicts(nested, page_url)
    elif isinstance(value, list):
        for nested in value:
            yield from _candidate_dicts(nested, page_url)


def _listing_from_dict(item: dict[str, Any], *, url: str, city: str) -> RawListing:
    fields = _map_fields(item)
    return RawListing(
        source="99acres",
        source_url=url,
        source_listing_id=source_id_from_url(url)
        or str(item.get("propertyId") or item.get("id") or "")
        or None,
        city=city,
        title=str(
            item.get("name") or item.get("title") or fields.get("title") or "99acres listing"
        ),
        fields=fields,
        raw={"extraction": "embedded_structured_json"},
    )


def _map_fields(item: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "title": ("title", "name", "propertyName"),
        "project_name": ("projectName", "project", "society"),
        "locality": ("locality", "localityName", "address"),
        "listing_price": ("price", "amount", "listPrice"),
        "area_sqft": ("area", "builtUpArea", "superBuiltUpArea", "carpetArea"),
        "bhk": ("bhk", "bedrooms", "bedRoom"),
        "property_type": ("propertyType", "type"),
        "description": ("description",),
        "price_per_sqft": ("pricePerSqft", "rate"),
        "furnishing": ("furnishing", "furnishingType"),
        "floor": ("floor", "floorNum"),
        "total_floors": ("totalFloors",),
        "seller_type": ("sellerType", "ownerType"),
        "rera_id": ("reraId", "rera"),
        "latitude": ("latitude", "lat"),
        "longitude": ("longitude", "lng", "lon"),
        "posted_date": ("postedDate", "listingDate"),
        "updated_date": ("updatedDate", "lastUpdated"),
    }
    fields: dict[str, Any] = {}
    for target, names in aliases.items():
        for name in names:
            if item.get(name) not in (None, "", []):
                fields[target] = item[name]
                break
    if "city" in item:
        fields["city"] = item["city"]
    return fields


def _quick_fields(text: str) -> dict[str, Any]:
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_lib.unescape(text))).strip()
    fields: dict[str, Any] = {}
    bhk = re.search(r"\b([1-9][0-9]?)\s*BHK\b", clean, re.I)
    if bhk:
        fields["bhk"] = int(bhk.group(1))
    area = re.search(
        r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:sq\.?\s*ft|sqft|square feet)\b", clean, re.I
    )
    if area:
        fields["area_sqft"] = float(area.group(1).replace(",", ""))
    price = re.search(r"(?:₹|Rs\.?|INR)\s*([0-9][0-9,.]*)\s*(Cr|Crore|Lac|Lakh)?", clean, re.I)
    if price:
        number = float(price.group(1).replace(",", ""))
        fields["listing_price"] = (
            number / 100 if price.group(2) and price.group(2).lower() in {"lac", "lakh"} else number
        )
    sector = re.search(r"\bSector\s*[- ]?\d+[A-Za-z]?\b", clean, re.I)
    if sector:
        fields["sector"] = sector.group(0)
        fields["locality"] = sector.group(0)
    return fields


def _context_for_href(body: str, href: str) -> str:
    index = body.find(href)
    return body[max(0, index - 1200) : index + 1200] if index >= 0 else ""


def _meta_value(body: str, name: str) -> str | None:
    for tag in re.findall(r"<meta\b[^>]*>", body, re.I):
        key = re.search(r"(?:property|name)=[\"']([^\"']+)[\"']", tag, re.I)
        content = re.search(r"content=[\"']([^\"']+)[\"']", tag, re.I)
        if key and content and key.group(1).lower() == name.lower():
            return html_lib.unescape(content.group(1))
    return None


def _meta_images(body: str) -> list[str]:
    return [
        value
        for value in (_meta_value(body, "og:image"), _meta_value(body, "twitter:image"))
        if value
    ]


def _image_urls_from_payloads(payloads: list[Any]) -> list[str]:
    values: list[str] = []

    def walk(value: Any):
        if isinstance(value, dict):
            for key, nested in value.items():
                if key.lower() in {"image", "images", "imageurl", "thumbnailurl"}:
                    if isinstance(nested, str) and nested.startswith(("http://", "https://")):
                        values.append(nested)
                    elif isinstance(nested, list):
                        for item in nested:
                            if isinstance(item, str) and item.startswith(("http://", "https://")):
                                values.append(item)
                            elif isinstance(item, dict) and isinstance(item.get("url"), str):
                                values.append(item["url"])
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    for payload in payloads:
        walk(payload)
    return list(dict.fromkeys(values))


def _canonical(body: str) -> str | None:
    return _meta_value(body, "canonical")


def _title(body: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    return re.sub(r"\s+", " ", html_lib.unescape(match.group(1))).strip() if match else None


class _AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[tuple[str, str]] = []
        self.current: str | None = None
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.current = href
                self.text = []

    def handle_data(self, data: str):
        if self.current is not None:
            self.text.append(data)

    def handle_endtag(self, tag: str):
        if tag.lower() == "a" and self.current is not None:
            self.hrefs.append((self.current, re.sub(r"\s+", " ", " ".join(self.text)).strip()))
            self.current = None
            self.text = []
