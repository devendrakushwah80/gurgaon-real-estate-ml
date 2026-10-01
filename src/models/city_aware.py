"""City-routed valuation training; never mixes cities silently.

The legacy Gurgaon artifact remains untouched. This command creates a separate
artifact only for cities with enough labelled rows and writes honest skip
reasons for cities that do not yet have training data.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from src.config.paths import DEFAULT_TRAINING_DATA, METRICS_DIR, MODEL_DIR
from src.features.selection import MODEL_FEATURES, TARGET_COLUMN
from src.models.evaluate import regression_metrics
from src.models.train import build_model


def train_city_models(data_path: str | Path, *, min_rows: int = 30) -> dict[str, Any]:
    frame = pd.read_csv(data_path)
    if "city" not in frame.columns:
        return {
            "status": "not_run",
            "reason": "Input data has no city column; no city-aware metrics were fabricated.",
            "cities": {},
        }
    required = MODEL_FEATURES + [TARGET_COLUMN, "city"]
    missing = [name for name in required if name not in frame.columns]
    if missing:
        return {
            "status": "not_run",
            "reason": f"Input data is missing columns: {missing}",
            "cities": {},
        }
    results: dict[str, Any] = {}
    artifact: dict[str, Any] = {}
    for city, group in frame.groupby(frame["city"].astype(str).str.strip().str.lower()):
        group = group.dropna(subset=[TARGET_COLUMN])
        if len(group) < min_rows:
            results[city] = {
                "status": "skipped",
                "rows": len(group),
                "reason": f"Fewer than {min_rows} labelled rows",
            }
            continue
        train, test = train_test_split(group, test_size=0.2, random_state=42)
        model = build_model()
        model.fit(train[MODEL_FEATURES], train[TARGET_COLUMN])
        results[city] = {
            "status": "trained",
            "rows": len(group),
            "metrics": regression_metrics(
                test[TARGET_COLUMN].to_numpy(), model.predict(test[MODEL_FEATURES])
            ),
        }
        artifact[city] = model
    output = Path(MODEL_DIR) / "city_models.joblib"
    output.parent.mkdir(parents=True, exist_ok=True)
    if artifact:
        joblib.dump(artifact, output)
    report = {
        "status": "complete",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_path": str(data_path),
        "artifact": str(output) if artifact else None,
        "cities": results,
    }
    Path(METRICS_DIR).mkdir(parents=True, exist_ok=True)
    Path(METRICS_DIR, "city_model_benchmark.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train separately routed city valuation models")
    parser.add_argument("--data-path", default=str(DEFAULT_TRAINING_DATA))
    args = parser.parse_args()
    print(json.dumps(train_city_models(args.data_path), indent=2))


if __name__ == "__main__":
    main()
