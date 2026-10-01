"""Deterministic duplicate keys, scoped by source and canonical city."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


def canonical_url(value: object) -> str:
    parts = urlsplit(str(value or "").strip().lower())
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", ""))


def duplicate_key(record: dict[str, Any]) -> str:
    strong = record.get("source_listing_id")
    if strong:
        raw = f"{record.get('source')}|{record.get('city')}|id|{strong}"
    elif record.get("source_url"):
        raw = (
            f"{record.get('source')}|{record.get('city')}|url|{canonical_url(record['source_url'])}"
        )
    else:
        values = "|".join(
            re.sub(r"\W+", "", str(record.get(name) or "").lower())
            for name in ("title", "locality", "bhk", "area_sqft", "listing_price")
        )
        raw = f"{record.get('city')}|composite|{values}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def deduplicate(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    unique: list[dict[str, Any]] = []
    for record in records:
        key = duplicate_key(record)
        if key in seen:
            duplicates.append(
                {
                    "duplicate_key": key,
                    "kept_id": seen[key].get("id"),
                    "duplicate_id": record.get("id"),
                }
            )
        else:
            record["duplicate_key"] = key
            seen[key] = record
            unique.append(record)
    return unique, duplicates
