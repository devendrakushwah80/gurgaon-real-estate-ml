"""Validation rules that prevent cross-city or unverified-image records."""

from __future__ import annotations

from typing import Any

from .normalizer import normalize_city

SUPPORTED_CITIES = ("gurgaon", "indore")


def validate_listing(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if normalize_city(record.get("city")) not in SUPPORTED_CITIES:
        errors.append("unsupported city")
    if not record.get("source_url"):
        errors.append("missing exact source URL")
    if record.get("image_url") and not record.get("image_verified_at"):
        errors.append("image lacks exact-page verification timestamp")
    if (
        record.get("image_match_confidence") is not None
        and float(record["image_match_confidence"]) < 1.0
    ):
        errors.append("image match confidence is below the required exact-match threshold")
    return errors
