"""CLI for responsible, source-preserving 99acres verification runs.

Examples:
    python -m src.ingestion.run --city gurgaon --pages 2
    python -m src.ingestion.run --city indore --url https://www.99acres.com/...

Search responses that are blocked, disallowed, or unavailable are recorded in
data/ingestion/runs without creating synthetic listings.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.database import connect, json_dumps

from .acres99 import Acres99Adapter
from .apify99acres import Apify99AcresAdapter
from .base import RawListing
from .deduplication import deduplicate
from .freshness import classify_fetch
from .normalizer import normalize_city, normalize_listing
from .parse99acres import Parse99AcresAdapter
from .validators import SUPPORTED_CITIES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = PROJECT_ROOT / "data" / "ingestion" / "runs"


def run(
    city: str,
    *,
    pages: int = 1,
    urls: list[str] | None = None,
    delay: float = 2.0,
    debug: bool = True,
    provider: str = "auto",
) -> dict[str, object]:
    canonical = normalize_city(city)
    if canonical not in SUPPORTED_CITIES:
        raise ValueError(f"Unsupported city: {city}. Choose gurgaon or indore.")
    selected_provider = resolve_provider(provider)
    if selected_provider == "parse":
        return _run_parse(canonical, pages=pages, debug=debug)
    if selected_provider == "apify":
        return _run_apify(canonical, pages=pages, debug=debug)
    adapter = Acres99Adapter(delay_seconds=delay)
    targets = urls or [adapter.search_url(canonical, page) for page in range(1, max(1, pages) + 1)]
    fetched: list[dict] = []
    search_listings: list[dict] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()
    repeated_pages = 0
    no_new_streak = 0
    stop_reason = "requested page limit reached"
    debug_dir = PROJECT_ROOT / "debug" / "99acres"
    for page_number, url in enumerate(targets, start=1):
        result = adapter.fetch_search(city=canonical, page=page_number, url=url)
        status, reason = classify_fetch(
            http_status=result.http_status, body=result.body, blocked=result.blocked
        )
        item = {
            "page": page_number,
            "url": url,
            "http_status": result.http_status,
            "final_url": result.final_url,
            "status": status.value,
            "reason": result.reason or reason,
            "content_hash": result.content_hash,
            "candidate_cards": result.candidate_count,
            "valid_listing_urls": result.valid_listing_count,
            "listing_ids": [
                listing.source_listing_id
                for listing in result.listings
                if listing.source_listing_id
            ],
            "listing_urls": [listing.source_url for listing in result.listings],
        }
        fetched.append(item)
        if debug and page_number == 1 and result.body:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"{canonical}_page_1.html").write_text(result.body, encoding="utf-8")
            (debug_dir / f"{canonical}_page_1.json").write_text(
                json.dumps({"response": item, "parser": "search_parser"}, indent=2),
                encoding="utf-8",
            )
        if result.content_hash and result.content_hash in seen_hashes:
            repeated_pages += 1
            stop_reason = "Repeated source response detected"
            item["repeated_response"] = True
            if page_number > 1:
                print(f"Page {page_number}: repeated source response detected; stopping")
                break
        if result.content_hash:
            seen_hashes.add(result.content_hash)
        page_records = [
            _listing_record(listing, status=status.value, reason=reason, page_url=url)
            for listing in result.listings
        ]
        new_ids = {
            record.get("source_listing_id") or record.get("source_url") for record in page_records
        } - seen_ids
        no_new_streak = no_new_streak + 1 if not new_ids else 0
        seen_ids.update(new_ids)
        search_listings.extend(page_records)
        print(
            f"Page {page_number}: HTTP {result.http_status}; candidate cards: {result.candidate_count}; valid listing URLs: {result.valid_listing_count}; new unique listings: {len(new_ids)}"
        )
        if no_new_streak >= 2:
            stop_reason = "No new source IDs or canonical detail URLs for two consecutive pages"
            break

    search_unique, search_duplicates = deduplicate(search_listings)
    detail_records: list[dict] = []
    detail_failures = 0
    detail_pages_fetched = 0
    images_attached = 0
    for _index, search_record in enumerate(search_unique, start=1):
        detail = adapter.fetch_detail(search_record["source_url"], canonical)
        detail_status, detail_reason = classify_fetch(
            http_status=detail.http_status, body=detail.body, blocked=detail.blocked
        )
        if _is_success_status(detail.http_status):
            detail_pages_fetched += 1
        if detail.listing is None:
            detail_failures += 1
            search_record["listing_status"] = detail_status.value
            search_record["status_reason"] = (
                detail.reason
                or "Detail page could not be parsed; retained exact search-result metadata as fallback"
            )
            detail_records.append(search_record)
            continue
        detail_record = _listing_record(
            detail.listing,
            status=detail_status.value,
            reason="Exact detail page fetched and parsed",
            page_url=search_record.get("search_page_url"),
        )
        merged = {
            **search_record,
            **{
                key: value
                for key, value in detail_record.items()
                if value not in (None, "", [], {})
            },
        }
        merged["source_url"] = search_record["source_url"]
        detail_records.append(merged)
        images_attached += len(merged.get("image_urls") or [])
    final_records, final_duplicates = deduplicate(detail_records)
    stored = _store(final_records)
    pages_fetched = sum(1 for item in fetched if _is_success_status(item["http_status"]))
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "city": canonical,
        "provider": "direct",
        "requested_pages": len(targets),
        "pages_fetched": pages_fetched,
        "listing_candidates": sum(item["candidate_cards"] for item in fetched),
        "valid_listing_urls": sum(item["valid_listing_urls"] for item in fetched),
        "listings_parsed": len(detail_records),
        "unique_listings": len(final_records),
        "duplicate_listings": len(search_duplicates) + len(final_duplicates),
        "detail_pages_fetched": detail_pages_fetched,
        "detail_parser_failures": detail_failures,
        "images_extracted": images_attached,
        "stored_listings": stored,
        "repeated_pages_detected": repeated_pages,
        "stop_reason": stop_reason,
        "responses": fetched,
        "note": "No listing or image is synthesized when the exact public source page cannot be fetched.",
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    output = RUN_DIR / f"{canonical}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def resolve_provider(provider: str) -> str:
    value = provider.strip().lower()
    if value not in {"auto", "parse", "apify", "direct"}:
        raise ValueError("provider must be one of: auto, parse, apify, direct")
    if value == "parse":
        return "parse"
    if value == "apify":
        return "apify"
    if value == "direct":
        return "direct"
    if os.getenv("PARSE_99ACRES_API_KEY", "").strip():
        return "parse"
    return "apify" if os.getenv("APIFY_API_TOKEN", "").strip() else "direct"


def _run_apify(city: str, *, pages: int, debug: bool) -> dict[str, object]:
    adapter = Apify99AcresAdapter()
    search_listings: list[dict] = []
    responses: list[dict] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()
    repeated_pages = 0
    api_errors = 0
    invalid_records = 0
    stop_reason = "requested page limit reached"
    debug_dir = PROJECT_ROOT / "debug" / "99acres"
    for page in range(1, max(1, pages) + 1):
        result = adapter.fetch_search(city=city, page=page)
        invalid_records += len(result.parser_errors)
        if result.api_error:
            api_errors += 1
        response = {
            "page": page,
            "url": result.requested_url,
            "http_status": result.http_status,
            "status": "SUCCESS"
            if _is_success_status(result.http_status) and not result.api_error
            else "ERROR",
            "content_hash": result.content_hash,
            "candidate_listings": result.candidate_count,
            "parsed_listings": result.valid_listing_count,
            "parser_errors": result.parser_errors,
            "listing_ids": [
                item.source_listing_id for item in result.listings if item.source_listing_id
            ],
            "listing_urls": [item.source_url for item in result.listings],
            "api_error": result.api_error,
        }
        responses.append(response)
        if debug and page == 1 and result.body:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"{city}_apify_page_1.json").write_text(
                json.dumps(result.raw_payload, indent=2), encoding="utf-8"
            )
            (debug_dir / f"{city}_apify_page_1_meta.json").write_text(
                json.dumps(response, indent=2), encoding="utf-8"
            )
        if result.api_error:
            stop_reason = "Apify API or actor error"
            print(f"Page {page}: Apify error: {result.api_error}")
            break
        if result.content_hash and result.content_hash in seen_hashes:
            repeated_pages += 1
            stop_reason = "Repeated Apify actor response detected"
            break
        if result.content_hash:
            seen_hashes.add(result.content_hash)
        page_records = [
            _listing_record(
                item,
                status=item.fields.get("listing_status", "UNKNOWN"),
                reason=item.fields.get(
                    "status_reason", "Apify result requires freshness verification"
                ),
                page_url=result.requested_url,
            )
            for item in result.listings
        ]
        new_ids = {
            item.get("source_listing_id") or item.get("source_url") for item in page_records
        } - seen_ids
        seen_ids.update(new_ids)
        search_listings.extend(page_records)
        print(
            f"Page {page}: API requests: 1; candidate listings: {result.candidate_count}; parsed listings: {result.valid_listing_count}; new unique listings: {len(new_ids)}"
        )
        if not result.listings:
            stop_reason = "Apify actor returned no listings"
            break
        if len(new_ids) == 0:
            stop_reason = "No new source IDs or exact URLs"
            break
    unique, duplicates = deduplicate(search_listings)
    stored = _store(unique)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "city": city,
        "provider": "apify",
        "api_requests": len(responses),
        "pages_requested": pages,
        "pages_fetched": sum(_is_success_status(item["http_status"]) for item in responses),
        "listing_candidates": sum(item["candidate_listings"] for item in responses),
        "listings_parsed": len(search_listings),
        "unique_listings": len(unique),
        "stored_listings": stored,
        "listings_with_images": sum(bool(item.get("image_urls")) for item in unique),
        "images_extracted": sum(len(item.get("image_urls") or []) for item in unique),
        "duplicate_listings": len(duplicates),
        "invalid_records": invalid_records,
        "api_errors": api_errors,
        "detail_pages_fetched": 0,
        "repeated_pages_detected": repeated_pages,
        "stop_reason": stop_reason,
        "responses": responses,
        "sample_source_listing_ids": [
            item.get("source_listing_id") for item in unique[:5] if item.get("source_listing_id")
        ],
        "sample_source_urls": [item.get("source_url") for item in unique[:5]],
        "note": "Apify actor dataset output is normalized without assigning generic images or search URLs as properties.",
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / f"{city}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _run_parse(city: str, *, pages: int, debug: bool) -> dict[str, object]:
    adapter = Parse99AcresAdapter()
    search_listings: list[dict] = []
    responses: list[dict] = []
    seen_hashes: set[str] = set()
    seen_ids: set[str] = set()
    repeated_pages = 0
    api_errors = 0
    invalid_records = 0
    stop_reason = "requested page limit reached"
    debug_dir = PROJECT_ROOT / "debug" / "99acres"
    for page in range(1, max(1, pages) + 1):
        result = adapter.fetch_search(city=city, page=page)
        invalid_records += len(result.parser_errors)
        if result.api_error:
            api_errors += 1
        response = {
            "page": page,
            "url": result.requested_url,
            "http_status": result.http_status,
            "status": "SUCCESS"
            if _is_success_status(result.http_status) and not result.api_error
            else "ERROR",
            "content_hash": result.content_hash,
            "candidate_listings": result.candidate_count,
            "parsed_listings": result.valid_listing_count,
            "parser_errors": result.parser_errors,
            "listing_ids": [
                item.source_listing_id for item in result.listings if item.source_listing_id
            ],
            "listing_urls": [item.source_url for item in result.listings],
            "api_error": result.api_error,
        }
        responses.append(response)
        if debug and page == 1 and result.body:
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / f"{city}_parse_page_1.json").write_text(
                json.dumps(result.raw_payload, indent=2), encoding="utf-8"
            )
            (debug_dir / f"{city}_parse_page_1_meta.json").write_text(
                json.dumps(response, indent=2), encoding="utf-8"
            )
        if result.api_error:
            stop_reason = "Parse API error"
            print(f"Page {page}: Parse API error: {result.api_error}")
            break
        if result.content_hash and result.content_hash in seen_hashes:
            repeated_pages += 1
            stop_reason = "Repeated Parse API response detected"
            break
        if result.content_hash:
            seen_hashes.add(result.content_hash)
        page_records = [
            _listing_record(
                item,
                status=item.fields.get("listing_status", "UNKNOWN"),
                reason=item.fields.get(
                    "status_reason", "Parse API result requires freshness verification"
                ),
                page_url=result.requested_url,
            )
            for item in result.listings
        ]
        new_ids = {
            item.get("source_listing_id") or item.get("source_url") for item in page_records
        } - seen_ids
        seen_ids.update(new_ids)
        search_listings.extend(page_records)
        print(
            f"Page {page}: API requests: 1; candidate listings: {result.candidate_count}; parsed listings: {result.valid_listing_count}; new unique listings: {len(new_ids)}"
        )
        if not result.listings:
            stop_reason = "Parse API returned no listings"
            break
        if len(new_ids) == 0:
            stop_reason = "No new source IDs or exact URLs"
            break

    unique, duplicates = deduplicate(search_listings)
    stored = _store(unique)
    images = sum(len(item.get("image_urls") or []) for item in unique)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "city": city,
        "provider": "parse",
        "api_requests": len(responses),
        "pages_requested": pages,
        "pages_fetched": sum(_is_success_status(item["http_status"]) for item in responses),
        "listing_candidates": sum(item["candidate_listings"] for item in responses),
        "listings_parsed": len(search_listings),
        "unique_listings": len(unique),
        "stored_listings": stored,
        "listings_with_images": sum(bool(item.get("image_urls")) for item in unique),
        "images_extracted": images,
        "duplicate_listings": len(duplicates),
        "invalid_records": invalid_records,
        "api_errors": api_errors,
        "detail_pages_fetched": 0,
        "repeated_pages_detected": repeated_pages,
        "stop_reason": stop_reason,
        "responses": responses,
        "sample_source_listing_ids": [
            item.get("source_listing_id") for item in unique[:5] if item.get("source_listing_id")
        ],
        "sample_source_urls": [item.get("source_url") for item in unique[:5]],
        "note": "Parse search_properties provides the documented property payload and exact details_url; no undocumented detail endpoint is called.",
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / f"{city}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _listing_record(listing: RawListing, *, status: str, reason: str, page_url: str | None) -> dict:
    fields = normalize_listing(
        listing.fields, source=listing.source, source_url=listing.source_url, city=listing.city
    )
    fields.update(
        {
            "source_listing_id": listing.source_listing_id,
            "title": listing.title,
            "listing_status": status,
            "status_reason": reason,
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
            "search_page_url": page_url,
            "raw_source_json": listing.raw,
        }
    )
    images = listing.images or ([listing.image] if listing.image else [])
    fields["image_urls"] = [image.url for image in images]
    if images:
        fields.update(
            {
                "image_url": images[0].url,
                "image_source": images[0].source,
                "image_verified_at": images[0].verified_at,
                "image_match_confidence": images[0].match_confidence,
            }
        )
    return fields


def _is_success_status(status: int | None) -> bool:
    return status is not None and 200 <= status < 300


def _store(records: list[dict]) -> int:
    stored = 0
    with connect() as db:
        for item in records:
            listing_id = f"current-{item.get('source')}-{item.get('source_listing_id') or item.get('source_url')}"
            db.execute(
                """INSERT OR REPLACE INTO current_listings
                (id, source, source_listing_id, source_url, title, description, property_type, bhk, locality, sector, city,
                 area_sqft, listing_price, price_per_sqft, listing_status, status_reason, last_verified_at, image_url,
                 image_source, image_verified_at, image_match_confidence, image_urls_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    listing_id,
                    item.get("source"),
                    item.get("source_listing_id"),
                    item.get("source_url"),
                    item.get("title", "Property listing"),
                    item.get("description"),
                    item.get("property_type"),
                    item.get("bhk"),
                    item.get("locality"),
                    item.get("sector"),
                    item.get("city"),
                    item.get("area_sqft"),
                    item.get("listing_price"),
                    item.get("price_per_sqft"),
                    item.get("listing_status", "UNKNOWN"),
                    item.get("status_reason"),
                    item.get("last_verified_at"),
                    item.get("image_url"),
                    item.get("image_source"),
                    item.get("image_verified_at"),
                    item.get("image_match_confidence"),
                    json_dumps(item.get("image_urls", [])),
                    json_dumps(item),
                ),
            )
            for image_url in item.get("image_urls", []):
                db.execute(
                    "INSERT OR REPLACE INTO current_listing_images(listing_id, image_url, image_source, image_verified_at, image_match_confidence) VALUES (?, ?, ?, ?, ?)",
                    (
                        listing_id,
                        image_url,
                        item.get("image_source"),
                        item.get("image_verified_at"),
                        item.get("image_match_confidence"),
                    ),
                )
            db.execute(
                """UPDATE current_listings SET project_name=?, latitude=?, longitude=?, furnishing=?, floor=?, total_floors=?, amenities_json=?, seller_type=?, verified_seller=?, posted_date=?, updated_date=? WHERE id=?""",
                (
                    item.get("project_name"),
                    item.get("latitude"),
                    item.get("longitude"),
                    item.get("furnishing"),
                    item.get("floor"),
                    item.get("total_floors"),
                    json_dumps(item.get("amenities", [])),
                    item.get("seller_type"),
                    item.get("verified_seller"),
                    item.get("posted_date"),
                    item.get("updated_date"),
                    listing_id,
                ),
            )
            stored += 1
    return stored


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a responsible 99acres verification pass")
    parser.add_argument("--city", choices=SUPPORTED_CITIES)
    parser.add_argument("--all", action="store_true", dest="all_cities")
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--url", action="append", dest="urls")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument(
        "--provider",
        choices=("auto", "parse", "apify", "direct"),
        default=os.getenv("INGESTION_PROVIDER", "auto"),
    )
    args = parser.parse_args()
    cities = list(SUPPORTED_CITIES) if args.all_cities else [args.city or "gurgaon"]
    try:
        reports = [
            run(
                city,
                pages=args.pages,
                urls=args.urls if len(cities) == 1 else None,
                delay=args.delay,
                provider=args.provider,
            )
            for city in cities
        ]
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
