"""Build and benchmark city-aware models from verified current listings.

This is intentionally separate from the historical Gurgaon production model.
The current-listing target is asking price, so the report labels the result as a
fresh asking-price benchmark and never claims that it improves the historical
baseline.  Price-derived fields such as ``price_per_sqft`` are excluded from
the feature table to avoid target leakage.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from app.database import connect, json_loads
from src.config.paths import METRICS_DIR, MODEL_DIR, PROCESSED_DATA_DIR
from src.features.selection import MODEL_FEATURES, TARGET_COLUMN, categorize_floor
from src.models.evaluate import regression_metrics
from src.models.train import build_model

DEFAULT_DATASET_PATH = PROCESSED_DATA_DIR / "verified_current_city_listings.csv"
DEFAULT_REPORT_PATH = METRICS_DIR / "fresh_city_model_benchmark.json"
DEFAULT_ARTIFACT_PATH = MODEL_DIR / "fresh_city_models.joblib"
BASELINE = {"r2": 0.8211, "mae": 0.5304, "rmse": 1.1727}


def build_dataset(output_path: str | Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    """Export one deduplicated, city-labelled row per live source listing."""

    with connect() as db:
        rows = db.execute(
            """SELECT * FROM current_listings
               WHERE listing_status NOT IN ('REMOVED', 'UNREACHABLE', 'STALE')
                 AND listing_price IS NOT NULL AND listing_price > 0
               ORDER BY CASE WHEN source = '99acres' THEN 0 ELSE 1 END,
                        last_verified_at DESC"""
        ).fetchall()

    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        item = dict(row)
        city = str(item.get("city") or "").strip().lower()
        if city not in {"gurgaon", "indore"}:
            continue
        source_id = str(item.get("source_listing_id") or "").strip()
        source_url = str(item.get("source_url") or "").strip().lower().rstrip("/")
        key = f"{city}|id|{source_id}" if source_id else f"{city}|url|{source_url}"
        if key in seen:
            continue
        seen.add(key)
        raw = json_loads(item.get("raw_json") or "{}", {})
        payload = raw.get("source_payload", {}) if isinstance(raw, dict) else {}
        payload = payload if isinstance(payload, dict) else {}
        area = _number(item.get("area_sqft")) or 0.0
        bhk = _number(item.get("bhk")) or 0.0
        floor_number = _number(item.get("floor")) or 0.0
        records.append(
            {
                "property_type": _property_type(item.get("property_type")),
                "sector": str(item.get("locality") or "unknown").strip() or "unknown",
                TARGET_COLUMN: float(item["listing_price"]),
                "bedRoom": bhk,
                "bathroom": _number(payload.get("bathrooms") or payload.get("bathroom")) or 0.0,
                "balcony": str(payload.get("balconies") or payload.get("balcony") or "0"),
                "agePossession": str(payload.get("possessionStatus") or "Unknown"),
                "built_up_area": area,
                "servant room": 0.0,
                "store room": 0.0,
                "furnishing_type": str(item.get("furnishing") or "Unknown"),
                "luxury_category": "Unknown",
                "floor_category": categorize_floor(floor_number),
                "city": city,
                "source_listing_id": source_id,
                "source_url": item.get("source_url"),
            }
        )

    frame = pd.DataFrame(records)
    if frame.empty:
        raise ValueError("No verified current listings with positive listing prices are available")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


def benchmark(
    data_path: str | Path = DEFAULT_DATASET_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    artifact_path: str | Path = DEFAULT_ARTIFACT_PATH,
    *,
    min_rows: int = 20,
) -> dict[str, Any]:
    """Train separately routed models and report city/overall holdout metrics."""

    frame = pd.read_csv(data_path)
    required = MODEL_FEATURES + [TARGET_COLUMN, "city"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Fresh benchmark data is missing columns: {missing}")

    models: dict[str, Any] = {}
    results: dict[str, Any] = {}
    overall_actual: list[float] = []
    overall_predicted: list[float] = []
    for city, group in frame.groupby(frame["city"].astype(str).str.strip().str.lower()):
        group = group.dropna(subset=[TARGET_COLUMN])
        city_result: dict[str, Any] = {"rows": int(len(group))}
        if len(group) < min_rows:
            city_result.update(
                {"status": "skipped", "reason": f"Fewer than {min_rows} labelled rows"}
            )
            results[city] = city_result
            continue
        train, test = train_test_split(group, test_size=0.2, random_state=42)
        model = build_model(random_state=42)
        model.fit(train[MODEL_FEATURES], train[TARGET_COLUMN])
        predictions = model.predict(test[MODEL_FEATURES])
        metrics = regression_metrics(test[TARGET_COLUMN].to_numpy(), predictions)
        city_result.update({"status": "trained", "test_rows": int(len(test)), "metrics": metrics})
        results[city] = city_result
        models[city] = model
        overall_actual.extend(test[TARGET_COLUMN].astype(float).tolist())
        overall_predicted.extend(float(value) for value in predictions)

    overall = regression_metrics(overall_actual, overall_predicted) if overall_actual else None
    artifact = None
    if models:
        artifact_file = Path(artifact_path)
        artifact_file.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(models, artifact_file)
        artifact = str(artifact_file)

    report = {
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_path": str(data_path),
        "artifact": artifact,
        "cities": results,
        "overall": overall,
        "historical_baseline": BASELINE,
        "comparison": {
            "improvement_claimed": False,
            "reason": "The historical baseline uses an older Gurgaon dataset and fixed split; fresh rows are current asking-price observations with a different population and city coverage.",
        },
        "leakage_controls": {
            "excluded_target_derived_fields": [
                "price_per_sqft",
                "listing_price",
                "raw source price fields",
            ],
            "model_features": MODEL_FEATURES,
            "city_routing": "separate model per canonical city; no city mixing inside city models",
        },
    }
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def _property_type(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    if "land" in text or "plot" in text:
        return "plot"
    if "house" in text or "villa" in text:
        return "house"
    if text in {"unknown", ""}:
        return "unknown"
    return "flat"


def _number(value: Any) -> float | None:
    match = re.search(r"[-+]?[0-9]+(?:\.[0-9]+)?", str(value or "").replace(",", ""))
    return float(match.group(0)) if match else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and benchmark leakage-safe fresh city models"
    )
    parser.add_argument("--data-path", default=str(DEFAULT_DATASET_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--min-rows", type=int, default=20)
    args = parser.parse_args()
    frame = build_dataset(args.data_path)
    report = benchmark(args.data_path, args.report_path, args.artifact_path, min_rows=args.min_rows)
    print(json.dumps({"dataset_rows": len(frame), **report}, indent=2))


if __name__ == "__main__":
    main()
