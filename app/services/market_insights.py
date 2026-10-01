"""City-scoped locality price insights for the web experience."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from typing import Any

from app.services.property_catalog import search_catalog
from src.ingestion.normalizer import normalize_city


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _price_per_sqft(record: dict[str, Any]) -> float | None:
    supplied = _number(record.get("price_per_sqft"))
    if supplied:
        return supplied
    price = _number(record.get("listing_price"))
    area = _number(record.get("area_sqft"))
    if price and area:
        return price * 10_000_000 / area
    return None


def build_market_insights(city: str) -> dict[str, Any]:
    """Aggregate medians by locality without mixing cities or duplicate listings."""

    canonical_city = normalize_city(city)
    groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    seen: set[str] = set()

    for record in search_catalog(city=canonical_city):
        locality = str(record.get("locality") or record.get("sector") or "").strip()
        price_per_sqft = _price_per_sqft(record)
        if not locality or price_per_sqft is None or not 100 <= price_per_sqft <= 500_000:
            continue
        identity = str(
            record.get("source_listing_id") or record.get("source_url") or record.get("id") or ""
        )
        dedupe_key = f"{canonical_city}:{identity}"
        if identity and dedupe_key in seen:
            continue
        if identity:
            seen.add(dedupe_key)
        groups[locality].append(
            {
                "price_per_sqft": price_per_sqft,
                "listing_price": _number(record.get("listing_price")) or 0,
                "area_sqft": _number(record.get("area_sqft")) or 0,
            }
        )

    localities = []
    all_rates: list[float] = []
    for locality, values in groups.items():
        rates = [item["price_per_sqft"] for item in values]
        prices = [item["listing_price"] for item in values if item["listing_price"]]
        areas = [item["area_sqft"] for item in values if item["area_sqft"]]
        all_rates.extend(rates)
        localities.append(
            {
                "locality": locality,
                "median_price_per_sqft": round(median(rates)),
                "median_listing_price": round(median(prices), 2) if prices else None,
                "median_area_sqft": round(median(areas)) if areas else None,
                "listing_count": len(values),
            }
        )

    localities.sort(key=lambda item: (-item["median_price_per_sqft"], item["locality"].lower()))
    highest = localities[0] if localities else None
    lowest = localities[-1] if localities else None
    return {
        "city": canonical_city,
        "summary": {
            "city_median_price_per_sqft": round(median(all_rates)) if all_rates else None,
            "listing_count": sum(item["listing_count"] for item in localities),
            "locality_count": len(localities),
            "highest_locality": highest["locality"] if highest else None,
            "lowest_locality": lowest["locality"] if lowest else None,
        },
        "localities": localities,
    }
