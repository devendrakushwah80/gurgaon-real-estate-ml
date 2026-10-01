"""Explainable valuation, trust, investment, and ranking services."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from statistics import median
from typing import Any

from app.services.property_catalog import load_catalog


def fair_value(property_record: dict[str, Any]) -> dict[str, Any]:
    """Return the existing model estimate with a transparent fallback."""

    listing_price = property_record.get("listing_price")
    estimate: float | None = None
    estimate_source = "RandomForest valuation model"
    try:
        payload = property_record.get("model_payload")
        # The legacy model is Gurgaon-only. Indore uses same-city comparables
        # until a separately trained city artifact exists.
        if payload and str(property_record.get("city", "gurgaon")).lower() in {
            "gurgaon",
            "gurugram",
        }:
            estimate = _cached_model_value(
                str(property_record.get("id", "")), json.dumps(payload, sort_keys=True)
            )
    except Exception:  # noqa: BLE001 - an unavailable artifact must not break browsing
        estimate = None
    if estimate is None or not math.isfinite(estimate) or estimate <= 0:
        comparable = comparable_prices(property_record)
        estimate = median(comparable) if comparable else listing_price
        estimate_source = "Comparable source listings"
    if estimate is None:
        estimate = 0.0
    difference = (float(listing_price) - estimate) if listing_price is not None else None
    difference_percent = (
        (difference / estimate * 100) if difference is not None and estimate else None
    )
    if difference_percent is None:
        classification = "Insufficient data"
    elif difference_percent <= -5:
        classification = "Potentially undervalued"
    elif difference_percent >= 5:
        classification = "Potentially overpriced"
    else:
        classification = "Near estimated fair value"
    return {
        "listing_price": listing_price,
        "fair_value": round(estimate, 4),
        "difference_value": round(difference, 4) if difference is not None else None,
        "difference_percent": round(difference_percent, 2)
        if difference_percent is not None
        else None,
        "classification": classification,
        "estimate_source": estimate_source,
        "disclaimer": "AI-generated estimate based on available property data; not a certified valuation.",
    }


@lru_cache(maxsize=1024)
def _cached_model_value(property_id: str, payload_text: str) -> float:
    from app.prediction.service import predict_price

    return float(predict_price(json.loads(payload_text)))


def comparable_prices(property_record: dict[str, Any]) -> list[float]:
    sector = str(property_record.get("sector") or property_record.get("locality") or "").lower()
    property_type = property_record.get("property_type")
    values = [
        float(item["listing_price"])
        for item in load_catalog()
        if item.get("listing_price")
        and item.get("city") == property_record.get("city")
        and str(item.get("sector") or item.get("locality") or "").lower() == sector
        and item.get("property_type") == property_type
    ]
    return values


def trust_score(
    property_record: dict[str, Any], valuation: dict[str, Any] | None = None
) -> dict[str, Any]:
    valuation = valuation or fair_value(property_record)
    listing_price = property_record.get("listing_price")
    fair = valuation.get("fair_value")
    difference = abs((listing_price - fair) / fair) if listing_price and fair else None
    price_points = 10 if difference is None else max(0.0, 20 - min(difference / 0.30, 1.0) * 20)

    fields = [
        "title",
        "property_type",
        "bhk",
        "locality",
        "area_sqft",
        "listing_price",
        "property_age",
        "furnishing",
        "description",
        "amenities",
    ]
    completeness_points = (
        15 * sum(bool(property_record.get(field)) for field in fields) / len(fields)
    )
    image_count = len(property_record.get("images") or [])
    image_points = 3 if image_count == 0 else 9 if image_count == 1 else 15
    source_points = 5 if property_record.get("source_url") else 1
    source_points += 4 if property_record.get("source") not in (None, "Source data") else 0
    source_points += 3 if property_record.get("rera_id") else 0
    source_points += 3 if property_record.get("seller_type") else 0
    location_points = (
        10
        if property_record.get("locality") and property_record.get("city")
        else 6
        if property_record.get("locality")
        else 2
    )
    duplicate_count = _duplicate_count(property_record)
    duplicate_points = 10 if duplicate_count == 0 else max(0, 10 - duplicate_count * 5)
    freshness_points = _freshness_points(property_record)
    metadata_points = 5 if _metadata_consistent(property_record) else 1

    breakdown = {
        "price_consistency": round(price_points, 1),
        "listing_completeness": round(completeness_points, 1),
        "image_confidence": float(image_points),
        "source_confidence": float(min(source_points, 15)),
        "location_consistency": float(location_points),
        "duplicate_check": float(duplicate_points),
        "freshness": float(freshness_points),
        "metadata_consistency": float(metadata_points),
    }
    total = round(sum(breakdown.values()))
    positives: list[str] = []
    warnings: list[str] = []
    if difference is not None and difference <= 0.1:
        positives.append("Listing price is close to the estimated fair value")
    if completeness_points >= 12:
        positives.append("Complete property metadata")
    if image_count >= 2:
        positives.append("Multiple source images are available")
    if location_points >= 8:
        positives.append("Location fields are consistent")
    if image_count == 0:
        warnings.append("No image URL is present in the supplied source data")
    if duplicate_count:
        warnings.append("A similar source listing was found")
    if freshness_points <= 5:
        warnings.append("Listing freshness could not be established from source data")
    return {
        "score": total,
        "label": _trust_label(total),
        "breakdown": breakdown,
        "positive_signals": positives,
        "warnings": warnings,
        "method": "Explainable data-quality and consistency signals; not a guarantee of authenticity.",
    }


def investment_score(
    property_record: dict[str, Any],
    valuation: dict[str, Any] | None = None,
    trust: dict[str, Any] | None = None,
) -> dict[str, Any]:
    valuation = valuation or fair_value(property_record)
    trust = trust or trust_score(property_record, valuation)
    advantage = valuation.get("difference_percent")
    valuation_points = (
        12.5 if advantage is None else max(0.0, min(25.0, 12.5 - float(advantage) / 2))
    )
    comparable = comparable_prices(property_record)
    demand_points = min(15.0, len(comparable) / 10 * 15)
    trend_points = 10.0 if comparable else 5.0
    amenity_count = len(property_record.get("amenities") or [])
    connectivity_points = min(10.0, 4 + amenity_count)
    quality_points = min(
        10.0,
        (2 if property_record.get("furnishing") else 0)
        + (3 if property_record.get("property_age") == "New Property" else 1)
        + min(5, amenity_count / 2),
    )
    rental_points = 0.0
    risk_points = max(0.0, 5 - max(0, 70 - trust["score"]) / 14)
    breakdown = {
        "valuation_advantage": round(valuation_points, 1),
        "locality_price_trend": trend_points,
        "rental_yield": rental_points,
        "demand_liquidity": round(demand_points, 1),
        "connectivity_amenities": round(connectivity_points, 1),
        "property_quality": round(quality_points, 1),
        "risk_penalty": round(risk_points, 1),
    }
    total = round(sum(breakdown.values()))
    positives: list[str] = []
    warnings: list[str] = []
    if advantage is not None and advantage < 0:
        positives.append(f"Listing is {abs(advantage):.1f}% below estimated fair value")
    if len(comparable) >= 3:
        positives.append("Comparable listings provide a demand proxy for this locality")
    if amenity_count >= 3:
        positives.append("Broad amenity profile")
    if rental_points == 0:
        warnings.append("Rental yield information is unavailable in the source data")
    if len(comparable) > 20:
        warnings.append("Many competing source listings may reduce liquidity")
    warnings.append("Investment Score reflects available data, not financial advice")
    return {
        "score": total,
        "label": "Strong data-based investment signals"
        if total >= 70
        else "Moderate investment signals"
        if total >= 45
        else "Requires further due diligence",
        "breakdown": breakdown,
        "positive_signals": positives,
        "warnings": warnings,
    }


def enrich_property(property_record: dict[str, Any]) -> dict[str, Any]:
    valuation = fair_value(property_record)
    trust = trust_score(property_record, valuation)
    investment = investment_score(property_record, valuation, trust)
    result = {
        key: value for key, value in property_record.items() if key not in {"raw", "model_payload"}
    }
    result.update({"valuation": valuation, "trust": trust, "investment": investment})
    return result


def save_score_snapshot(item: dict[str, Any]) -> None:
    """Persist the explainable score and valuation snapshot for auditability."""

    save_score_snapshots([item])


def save_score_snapshots(items: list[dict[str, Any]]) -> None:
    """Persist multiple score snapshots in one transaction."""

    if not items:
        return

    from app.database import connect, json_dumps

    with connect() as db:
        for item in items:
            valuation = item["valuation"]
            trust = item["trust"]
            investment = item["investment"]
            db.execute(
                "INSERT OR REPLACE INTO listing_trust_scores(property_id, total_score, breakdown_json, positive_signals_json, warnings_json, calculated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    item["id"],
                    trust["score"],
                    json_dumps(trust["breakdown"]),
                    json_dumps(trust["positive_signals"]),
                    json_dumps(trust["warnings"]),
                ),
            )
            db.execute(
                "INSERT OR REPLACE INTO investment_scores(property_id, total_score, breakdown_json, positive_signals_json, warnings_json, calculated_at) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    item["id"],
                    investment["score"],
                    json_dumps(investment["breakdown"]),
                    json_dumps(investment["positive_signals"]),
                    json_dumps(investment["warnings"]),
                ),
            )
            db.execute(
                "INSERT OR REPLACE INTO property_predictions(property_id, listing_price, fair_value, difference_value, difference_percent, classification, calculated_at) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (
                    item["id"],
                    valuation.get("listing_price"),
                    valuation.get("fair_value"),
                    valuation.get("difference_value"),
                    valuation.get("difference_percent"),
                    valuation.get("classification"),
                ),
            )


def rank_properties(
    records: list[dict[str, Any]],
    preferences: dict[str, Any] | None = None,
    max_candidates: int = 250,
) -> list[dict[str, Any]]:
    preferences = preferences or {}
    if len(records) > max_candidates:
        stride = max(1, len(records) // max_candidates)
        records = records[::stride][:max_candidates]
    ranked: list[dict[str, Any]] = []
    for record in records:
        item = enrich_property(record)
        score = 0.0
        reasons: list[str] = []
        price = record.get("listing_price")
        if preferences.get("budget_max") and price and price <= preferences["budget_max"]:
            score += 25
            reasons.append("within your budget")
        if preferences.get("budget_min") and price and price >= preferences["budget_min"]:
            score += 5
        if preferences.get("bhk") and record.get("bhk") == preferences["bhk"]:
            score += 20
            reasons.append(f"matches your {preferences['bhk']} BHK preference")
        if preferences.get("preferred_bhk") and record.get("bhk") in preferences["preferred_bhk"]:
            score += 20
            reasons.append("matches your preferred configuration")
        localities = preferences.get("preferred_localities") or []
        if localities and any(
            str(value).lower() in str(record.get("locality", "")).lower() for value in localities
        ):
            score += 20
            reasons.append("matches your preferred locality")
        if (
            record.get("area_sqft")
            and preferences.get("min_area_sqft")
            and record["area_sqft"] >= preferences["min_area_sqft"]
        ):
            score += 8
        score += item["trust"]["score"] * 0.12 + item["investment"]["score"] * 0.15
        if (
            item["valuation"].get("difference_percent") is not None
            and item["valuation"]["difference_percent"] < 0
        ):
            score += min(12, abs(item["valuation"]["difference_percent"]))
            reasons.append("priced below the estimated fair value")
        if not reasons:
            reasons.append("strongest available match across valuation, trust, and market signals")
        item["recommendation_score"] = round(score, 2)
        item["recommendation_reason"] = (
            "Recommended because this property " + ", ".join(reasons) + "."
        )
        ranked.append(item)
    return sorted(ranked, key=lambda value: value["recommendation_score"], reverse=True)


def _trust_label(score: int) -> str:
    if score >= 90:
        return "Very High Listing Confidence"
    if score >= 75:
        return "High Listing Confidence"
    if score >= 60:
        return "Moderate Listing Confidence"
    if score >= 40:
        return "Needs Verification"
    return "High Risk / Insufficient Confidence"


def _duplicate_count(record: dict[str, Any]) -> int:
    key = (
        record.get("bhk"),
        record.get("area_sqft"),
        record.get("listing_price"),
        record.get("locality"),
    )
    return sum(
        1
        for item in load_catalog()
        if item["id"] != record.get("id")
        and (
            item.get("bhk"),
            item.get("area_sqft"),
            item.get("listing_price"),
            item.get("locality"),
        )
        == key
    )


def _freshness_points(record: dict[str, Any]) -> int:
    value = record.get("listing_date") or record.get("created_at")
    if not value:
        return 4
    try:
        days = (
            datetime.now(timezone.utc) - datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        ).days
        return 10 if days <= 30 else 7 if days <= 90 else 4 if days <= 365 else 1
    except ValueError:
        return 4


def _metadata_consistent(record: dict[str, Any]) -> bool:
    return bool(
        record.get("listing_price") and record.get("area_sqft") and record.get("bhk") is not None
    )
