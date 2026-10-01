"""Canonical city and listing normalization; aliases never cross city boundaries."""

from __future__ import annotations

import re
from typing import Any

CITY_ALIASES = {
    "gurgaon": "gurgaon",
    "gurugram": "gurgaon",
    "gurugram, haryana": "gurgaon",
    "indore": "indore",
    "indore, madhya pradesh": "indore",
}


def normalize_city(value: object) -> str:
    key = re.sub(r"\s+", " ", str(value or "").strip().lower())
    return CITY_ALIASES.get(key, key)


def normalize_listing(
    raw: dict[str, Any], *, source: str, source_url: str, city: str
) -> dict[str, Any]:
    city_name = normalize_city(city)
    fields = dict(raw)
    fields.update({"source": source, "source_url": source_url, "city": city_name})
    fields["title"] = str(
        fields.get("title") or fields.get("property_name") or "Property listing"
    ).strip()
    fields["source_listing_id"] = fields.get("source_listing_id") or fields.get("property_id")
    fields["listing_status"] = str(fields.get("listing_status") or "UNKNOWN").upper()
    return fields
