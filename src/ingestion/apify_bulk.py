"""Long-running, paginated Apify ingestion for large city inventories."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests
from dotenv import load_dotenv

from app.database import connect
from src.ingestion.apify99acres import (
    DEFAULT_ACTOR_ID,
    DEFAULT_APIFY_BASE_URL,
    normalize_apify_items,
)
from src.ingestion.deduplication import deduplicate
from src.ingestion.normalizer import normalize_city
from src.ingestion.run import RUN_DIR, _listing_record, _store
from src.ingestion.validators import SUPPORTED_CITIES

load_dotenv()

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"}


class ApifyBulkError(RuntimeError):
    """Raised when a bulk Actor run cannot produce a complete dataset."""


def _client() -> tuple[requests.Session, str, str]:
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        raise ApifyBulkError("APIFY_API_TOKEN is required")
    base_url = os.getenv("APIFY_API_BASE_URL", DEFAULT_APIFY_BASE_URL).rstrip("/")
    actor_id = os.getenv("APIFY_ACTOR_ID", DEFAULT_ACTOR_ID)
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "EstateIQ-Apify-bulk-client/1.0",
        }
    )
    return session, base_url, actor_id


def _response_data(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as error:
        raise ApifyBulkError(f"Apify returned non-JSON HTTP {response.status_code}") from error
    if not response.ok:
        message = payload.get("error", payload) if isinstance(payload, dict) else payload
        raise ApifyBulkError(f"Apify HTTP {response.status_code}: {message}")
    data = payload.get("data", payload) if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        raise ApifyBulkError("Apify response did not contain a run object")
    return data


def start_run(
    session: requests.Session,
    base_url: str,
    actor_id: str,
    *,
    city: str,
    property_type: str,
    max_items: int,
    search_queries: list[str],
) -> dict[str, Any]:
    payload = {
        "searchQueries": search_queries,
        "category": "buy",
        "segment": "residential",
        "extractListingDetails": False,
        "extractAgentDetails": False,
        "maxConcurrency": 5,
        "maxItems": max_items,
        "proxyConfiguration": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"],
        },
    }
    if property_type != "all":
        payload["propertyTypes"] = [property_type]
    actor_path = quote(actor_id, safe="~")
    response = session.post(
        f"{base_url}/acts/{actor_path}/runs",
        params={"timeout": int(os.getenv("APIFY_BULK_TIMEOUT_SECONDS", "3600"))},
        json=payload,
        timeout=60,
    )
    return _response_data(response)


def locality_queries(city: str, limit: int) -> list[str]:
    """Build actor-supported locality searches from current city inventory."""

    queries = [city.title()]
    if limit <= 0:
        return queries
    with connect() as db:
        rows = db.execute(
            """SELECT locality, COUNT(*) AS listing_count
            FROM current_listings
            WHERE lower(city) = ?
              AND locality IS NOT NULL
              AND trim(locality) != ''
            GROUP BY locality
            ORDER BY listing_count DESC, locality
            LIMIT ?""",
            (city, limit),
        ).fetchall()
    for row in rows:
        locality = str(row["locality"]).strip()
        if not locality or locality.lower() == city:
            continue
        query = locality if city in locality.lower() else f"{locality} {city.title()}"
        if query not in queries:
            queries.append(query)
    return queries


def wait_for_run(
    session: requests.Session,
    base_url: str,
    run: dict[str, Any],
    *,
    poll_seconds: float,
) -> dict[str, Any]:
    run_id = str(run["id"])
    while True:
        response = session.get(f"{base_url}/actor-runs/{run_id}", timeout=60)
        current = _response_data(response)
        status = str(current.get("status") or "UNKNOWN").upper()
        stats = current.get("stats") if isinstance(current.get("stats"), dict) else {}
        print(
            f"Run {run_id}: status={status}; "
            f"requests_finished={stats.get('requestsFinished', 'unknown')}",
            flush=True,
        )
        if status in TERMINAL_STATUSES:
            return current
        time.sleep(poll_seconds)


def fetch_dataset(
    session: requests.Session,
    base_url: str,
    dataset_id: str,
    *,
    page_size: int = 1_000,
) -> list[Any]:
    items: list[Any] = []
    offset = 0
    while True:
        response = session.get(
            f"{base_url}/datasets/{dataset_id}/items",
            params={"clean": "true", "format": "json", "offset": offset, "limit": page_size},
            timeout=120,
        )
        if not response.ok:
            raise ApifyBulkError(f"Dataset HTTP {response.status_code}: {response.text[:300]}")
        batch = response.json()
        if not isinstance(batch, list):
            raise ApifyBulkError("Apify dataset response was not an array")
        items.extend(batch)
        print(f"Dataset {dataset_id}: downloaded {len(items)} records", flush=True)
        if len(batch) < page_size:
            break
        offset += len(batch)
    return items


def ingest_run_result(
    session: requests.Session,
    base_url: str,
    finished: dict[str, Any],
    *,
    city: str,
    property_type: str,
    requested_items: int,
    search_query_count: int,
) -> dict[str, Any]:
    """Normalize and store a completed or intentionally aborted run's dataset."""

    status = str(finished.get("status") or "UNKNOWN").upper()
    if status not in {"SUCCEEDED", "ABORTED"}:
        raise ApifyBulkError(f"Actor run is not importable while status is {status}")
    dataset_id = str(finished.get("defaultDatasetId") or "")
    if not dataset_id:
        raise ApifyBulkError("Actor run did not expose a default dataset")

    raw_items = fetch_dataset(session, base_url, dataset_id)
    listings, errors = normalize_apify_items(raw_items, requested_city=city)
    records = [
        _listing_record(
            listing,
            status=listing.fields.get("listing_status", "UNKNOWN"),
            reason=listing.fields.get(
                "status_reason", "Apify result requires freshness verification"
            ),
            page_url=f"apify://dataset/{dataset_id}",
        )
        for listing in listings
    ]
    unique, duplicates = deduplicate(records)
    stored = _store(unique)
    report = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "city": city,
        "provider": "apify_bulk",
        "property_type_filter": property_type,
        "requested_items": requested_items,
        "search_query_count": search_query_count,
        "run_id": finished.get("id"),
        "dataset_id": dataset_id,
        "actor_status": status,
        "candidate_listings": len(raw_items),
        "listings_parsed": len(records),
        "unique_listings": len(unique),
        "stored_listings": stored,
        "listings_with_images": sum(bool(item.get("image_urls")) for item in unique),
        "images_extracted": sum(len(item.get("image_urls") or []) for item in unique),
        "duplicate_listings": len(duplicates),
        "invalid_records": len(errors),
        "normalization_errors": errors[:100],
        "usage_total_usd": finished.get("usageTotalUsd"),
        "sample_source_listing_ids": [item.get("source_listing_id") for item in unique[:5]],
        "sample_source_urls": [item.get("source_url") for item in unique[:5]],
    }
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    output = RUN_DIR / (
        f"{city}-apify-{property_type}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    return report


def import_run(city: str, *, run_id: str, property_type: str = "all") -> dict[str, Any]:
    """Import a preserved dataset from a succeeded or user-aborted Actor run."""

    canonical = normalize_city(city)
    if canonical not in SUPPORTED_CITIES:
        raise ValueError(f"Unsupported city: {city}")
    session, base_url, _actor_id = _client()
    finished = _response_data(session.get(f"{base_url}/actor-runs/{run_id}", timeout=60))
    return ingest_run_result(
        session,
        base_url,
        finished,
        city=canonical,
        property_type=property_type,
        requested_items=0,
        search_query_count=0,
    )


def run_bulk(
    city: str,
    *,
    property_type: str,
    max_items: int,
    poll_seconds: float = 15,
    seed_localities: int = 0,
) -> dict[str, Any]:
    canonical = normalize_city(city)
    if canonical not in SUPPORTED_CITIES:
        raise ValueError(f"Unsupported city: {city}")
    if property_type not in {"all", "apartment", "house", "villa", "plot"}:
        raise ValueError("property_type must be all, apartment, house, villa, or plot")
    if max_items < 1:
        raise ValueError("max_items must be positive")

    session, base_url, actor_id = _client()
    search_queries = locality_queries(canonical, seed_localities)
    started = start_run(
        session,
        base_url,
        actor_id,
        city=canonical,
        property_type=property_type,
        max_items=max_items,
        search_queries=search_queries,
    )
    print(
        f"Started Apify run {started.get('id')} for {canonical}/{property_type}; "
        f"max_items={max_items}",
        flush=True,
    )
    finished = wait_for_run(
        session,
        base_url,
        started,
        poll_seconds=max(5, poll_seconds),
    )
    status = str(finished.get("status") or "UNKNOWN").upper()
    if status != "SUCCEEDED":
        raise ApifyBulkError(
            f"Actor run {finished.get('id')} ended with {status}: "
            f"{finished.get('statusMessage') or 'no status message'}"
        )
    return ingest_run_result(
        session,
        base_url,
        finished,
        city=canonical,
        property_type=property_type,
        requested_items=max_items,
        search_query_count=len(search_queries),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a long-lived Apify ingestion segment")
    parser.add_argument("--city", choices=SUPPORTED_CITIES, required=True)
    parser.add_argument(
        "--property-type",
        choices=("all", "apartment", "house", "villa", "plot"),
        default="all",
    )
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--poll-seconds", type=float, default=15)
    parser.add_argument("--seed-localities", type=int, default=0)
    parser.add_argument("--import-run")
    arguments = parser.parse_args()
    try:
        if arguments.import_run:
            import_run(
                arguments.city,
                run_id=arguments.import_run,
                property_type=arguments.property_type,
            )
        elif arguments.max_items:
            run_bulk(
                arguments.city,
                property_type=arguments.property_type,
                max_items=arguments.max_items,
                poll_seconds=arguments.poll_seconds,
                seed_localities=arguments.seed_localities,
            )
        else:
            parser.error("--max-items is required unless --import-run is provided")
    except (ApifyBulkError, requests.RequestException, ValueError) as error:
        parser.error(str(error))
