"""Export a sanitized, normalized city catalog for versioned project data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.database import connect
from src.ingestion.normalizer import normalize_city
from src.ingestion.validators import SUPPORTED_CITIES

EXPORT_FIELDS = (
    "source",
    "source_listing_id",
    "source_url",
    "title",
    "property_type",
    "bhk",
    "locality",
    "sector",
    "city",
    "latitude",
    "longitude",
    "area_sqft",
    "listing_price",
    "price_per_sqft",
    "furnishing",
    "floor",
    "total_floors",
    "property_age",
    "project_name",
    "listing_status",
    "posted_date",
    "updated_date",
    "image_url",
)


def export_city(city: str, output: Path) -> int:
    canonical = normalize_city(city)
    if canonical not in SUPPORTED_CITIES:
        raise ValueError(f"Unsupported city: {city}")
    with connect() as db:
        rows = [
            dict(row)
            for row in db.execute(
                """SELECT * FROM current_listings
                WHERE lower(city) = ?
                  AND listing_status NOT IN ('REMOVED', 'UNREACHABLE', 'STALE')
                ORDER BY source_listing_id, source_url""",
                (canonical,),
            ).fetchall()
        ]

    unique: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        identity = (
            ("source_listing_id", str(row["source_listing_id"]))
            if row.get("source_listing_id")
            else ("source_url", str(row.get("source_url") or row.get("id")))
        )
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unique)
    return len(unique)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export a sanitized EstateIQ city catalog")
    parser.add_argument("--city", choices=SUPPORTED_CITIES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    count = export_city(arguments.city, arguments.output)
    print(f"Exported {count} unique {arguments.city} listings to {arguments.output}")
