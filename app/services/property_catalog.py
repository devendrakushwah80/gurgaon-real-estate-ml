"""Source-backed property catalog and normalization helpers.

The catalog reads the existing raw listing exports. It intentionally exposes
only fields present in those exports and leaves image URLs empty when the
source does not provide them.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.database import DATABASE_PATH, connect, json_loads
from src.config.paths import RAW_DATA_DIR
from src.features.engineering import (
    categorize_age_possession,
    categorize_furnishing,
    convert_to_sqft,
    get_additional_room_flag,
    get_furnishing_count,
    luxury_score,
)
from src.features.selection import categorize_floor, categorize_luxury


def _number(value: object) -> float | None:
    match = re.search(r"[0-9]+(?:\.[0-9]+)?", str(value or "").replace(",", ""))
    return float(match.group(0)) if match else None


def _price(value: object) -> float | None:
    number = _number(value)
    if number is None:
        return None
    text = str(value).lower()
    return number / 100 if "lac" in text or "lakh" in text else number


def _sector(address: object) -> str | None:
    match = re.search(r"sector\s+[0-9]+[a-z]?", str(address or ""), flags=re.IGNORECASE)
    return match.group(0).title() if match else None


def _source(url: object) -> str:
    host = urlparse(str(url or "")).netloc.lower()
    if "99acres" in host:
        return "99acres"
    if "magicbricks" in host:
        return "MagicBricks"
    if "housing" in host:
        return "Housing"
    return host or "Source data"


def _images(row: dict[str, str]) -> list[str]:
    for name in ("image_url", "thumbnail", "images"):
        value = row.get(name, "")
        if value:
            return [part.strip() for part in re.split(r"[,|]", value) if part.strip()]
    return []


def normalize_row(row: dict[str, str], source_file: str, index: int) -> dict[str, Any]:
    source_url = row.get("link") or row.get("source_url") or ""
    address = row.get("address", "")
    price = _price(row.get("price"))
    area = convert_to_sqft(row.get("areaWithType") or row.get("area"))
    area = float(area) if area == area else None
    features = row.get("features", "")
    amenities = [
        part.strip(" []'\"") for part in re.split(r"[,|]", features) if part.strip(" []'\"")
    ]
    raw_type = "house" if source_file == "houses.csv" else "flat"
    source_id = row.get("property_id") or f"{source_file}:{index}"
    property_id = f"source-{source_id}"
    floor = row.get("floorNum") or row.get("noOfFloor") or None
    floor_number = _number(floor)
    return {
        "id": property_id,
        "owner_id": None,
        "source": _source(source_url),
        "source_listing_id": source_id,
        "source_url": source_url or None,
        "title": row.get("property_name")
        or f"{raw_type.title()} in {_sector(address) or 'Gurgaon'}",
        "description": row.get("description") or "",
        "property_type": raw_type,
        "bhk": int(_number(row.get("bedRoom")) or 0) or None,
        "locality": _sector(address) or "Gurgaon",
        "sector": _sector(address),
        "city": "gurgaon",
        "area_sqft": area,
        "listing_price": price,
        "price_per_sqft": _number(row.get("rate")),
        "furnishing": categorize_furnishing(get_furnishing_count(row.get("furnishDetails"))),
        "floor": floor,
        "total_floors": int(floor_number) if source_file == "houses.csv" and floor_number else None,
        "property_age": categorize_age_possession(row.get("agePossession")),
        "amenities": amenities,
        "seller_type": None,
        "rera_id": None,
        "images": _images(row),
        "listing_status": "UNKNOWN",
        "status_reason": "Historical export has not been verified against the live source",
        "last_verified_at": None,
        "image_source": None,
        "image_verified_at": None,
        "image_match_confidence": None,
        "project_name": row.get("society") or None,
        "posted_date": None,
        "updated_date": None,
        "ingested_at": None,
        "raw": row,
        "model_payload": {
            "property_type": raw_type,
            "sector": _sector(address) or "unknown",
            "bedRoom": float(_number(row.get("bedRoom")) or 0),
            "bathroom": float(_number(row.get("bathroom")) or 0),
            "balcony": row.get("balcony") or "0",
            "agePossession": categorize_age_possession(row.get("agePossession")),
            "built_up_area": area or 0,
            "servant room": get_additional_room_flag(row.get("additionalRoom"), "servant room"),
            "store room": get_additional_room_flag(row.get("additionalRoom"), "store room"),
            "furnishing_type": categorize_furnishing(
                get_furnishing_count(row.get("furnishDetails"))
            ),
            "luxury_category": categorize_luxury(luxury_score(features)),
            "floor_category": categorize_floor(floor_number or 0),
        },
    }


def _current_records() -> list[dict[str, Any]]:
    with connect() as db:
        rows = db.execute(
            "SELECT * FROM current_listings WHERE listing_status NOT IN ('REMOVED', 'UNREACHABLE', 'STALE') ORDER BY ingested_at DESC"
        ).fetchall()
    records: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["amenities"] = json_loads(item.pop("amenities_json", "[]"), [])
        item["images"] = json_loads(item.pop("image_urls_json", "[]"), [])
        if not item["images"] and item.get("image_url"):
            item["images"] = [item["image_url"]]
        with connect() as image_db:
            image_rows = image_db.execute(
                "SELECT image_url FROM current_listing_images WHERE listing_id=? ORDER BY rowid",
                (item["id"],),
            ).fetchall()
        item["images"] = list(
            dict.fromkeys(item["images"] + [image["image_url"] for image in image_rows])
        )
        item["model_payload"] = {}
        item["raw"] = json_loads(item.pop("raw_json", "{}"), {})
        records.append(item)
    return records


def _catalog_version() -> tuple[int, ...]:
    """Return source modification stamps so live ingestion invalidates the cache."""

    paths = [DATABASE_PATH, Path(RAW_DATA_DIR) / "flats.csv", Path(RAW_DATA_DIR) / "houses.csv"]
    return tuple(path.stat().st_mtime_ns if path.exists() else 0 for path in paths)


@lru_cache(maxsize=2)
def _load_catalog(_version: tuple[int, ...]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = _current_records()
    for filename in ("flats.csv", "houses.csv"):
        path = Path(RAW_DATA_DIR) / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle)):
                records.append(normalize_row(row, filename, index))
    return tuple(records)


def load_catalog() -> tuple[dict[str, Any], ...]:
    return _load_catalog(_catalog_version())


def refresh_catalog() -> None:
    """Clear the process-local catalog after an ingestion or maintenance run."""

    _load_catalog.cache_clear()


def find_property(property_id: str) -> dict[str, Any] | None:
    return next((item for item in load_catalog() if item["id"] == property_id), None)


def search_catalog(**filters: Any) -> list[dict[str, Any]]:
    records = list(load_catalog())
    for key, value in filters.items():
        if value is None or value == "":
            continue
        if key == "budget_min":
            records = [
                item
                for item in records
                if item.get("listing_price") is not None and item["listing_price"] >= value
            ]
        elif key == "budget_max":
            records = [
                item
                for item in records
                if item.get("listing_price") is not None and item["listing_price"] <= value
            ]
        elif key == "bhk":
            records = [item for item in records if item.get("bhk") == value]
        elif key == "min_area_sqft":
            records = [
                item for item in records if item.get("area_sqft") and item["area_sqft"] >= value
            ]
        elif key == "max_area_sqft":
            records = [
                item for item in records if item.get("area_sqft") and item["area_sqft"] <= value
            ]
        elif key == "locality":
            needle = str(value).strip().lower()
            records = [
                item
                for item in records
                if needle
                in " ".join(
                    str(item.get(field) or "").lower()
                    for field in ("locality", "sector", "project_name", "title")
                )
            ]
        elif key == "property_type":
            requested = str(value).strip().lower()
            aliases = {
                "apartment": ("apartment", "flat"),
                "flat": ("apartment", "flat"),
                "house": ("house", "villa", "bungalow"),
                "plot": ("plot", "land"),
            }
            accepted = aliases.get(requested, (requested,))
            records = [
                item
                for item in records
                if any(term in str(item.get("property_type", "")).lower() for term in accepted)
            ]
        elif key == "city":
            city = str(value).strip().lower().replace("gurugram", "gurgaon")
            records = [item for item in records if str(item.get("city", "")).lower() == city]
        elif key == "listing_status":
            records = [
                item
                for item in records
                if str(item.get("listing_status", "")).upper() == str(value).upper()
            ]
    return records
