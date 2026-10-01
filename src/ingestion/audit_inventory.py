"""Audit unique, city-scoped inventory after a live ingestion run."""

from __future__ import annotations

import argparse
from collections import Counter
from typing import Any

from app.database import connect, json_loads
from src.ingestion.normalizer import normalize_city


def property_category(record: dict[str, Any]) -> str:
    evidence = " ".join(
        str(record.get(field) or "").lower() for field in ("property_type", "title", "source_url")
    )
    if any(term in evidence for term in ("apartment", "flat", "penthouse")):
        return "apartments"
    if any(term in evidence for term in ("house", "villa", "bungalow")):
        return "houses_villas"
    if any(term in evidence for term in ("plot", "land")):
        return "plots_land"
    return "unknown"


def audit_inventory(city: str) -> dict[str, Any]:
    canonical = normalize_city(city)
    with connect() as db:
        rows = [
            dict(row)
            for row in db.execute(
                """SELECT * FROM current_listings
                WHERE lower(city) = ?
                  AND listing_status NOT IN ('REMOVED', 'UNREACHABLE', 'STALE')""",
                (canonical,),
            ).fetchall()
        ]

    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if row.get("source_listing_id"):
            identity = ("source_listing_id", str(row["source_listing_id"]))
        else:
            identity = ("source_url", str(row.get("source_url") or row.get("id")))
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(row)

    return {
        "city": canonical,
        "database_rows": len(rows),
        "unique_listings": len(unique),
        "categories": dict(Counter(property_category(row) for row in unique)),
        "with_images": sum(
            bool(json_loads(row.get("image_urls_json") or "[]", [])) for row in unique
        ),
        "with_exact_source_url": sum(
            "99acres.com" in str(row.get("source_url") or "").lower()
            and "/search/" not in str(row.get("source_url") or "").lower()
            for row in unique
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit EstateIQ's city inventory")
    parser.add_argument("--city", required=True)
    arguments = parser.parse_args()
    print(audit_inventory(arguments.city))
