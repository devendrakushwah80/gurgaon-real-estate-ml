"""Leakage-safe benchmark for candidate regression models.

All candidates share the exact production preprocessing and one fixed split.
Optional libraries are only used when installed; the existing RandomForest
artifact remains the production model unless a benchmark is reviewed manually.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.config.paths import DEFAULT_TRAINING_DATA, METRICS_DIR
from src.features.selection import MODEL_FEATURES, TARGET_COLUMN
from src.models.evaluate import regression_metrics
from src.models.train import build_preprocessor


def benchmark(
    data_path: str | Path = DEFAULT_TRAINING_DATA, output_path: str | Path | None = None
) -> dict[str, Any]:
    frame = pd.read_csv(data_path)
    required = MODEL_FEATURES + [TARGET_COLUMN]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Benchmark data is missing required columns: {missing}")
    frame = frame[required].dropna(subset=[TARGET_COLUMN])
    x_train, x_test, y_train, y_test = train_test_split(
        frame[MODEL_FEATURES], frame[TARGET_COLUMN], test_size=0.2, random_state=42
    )
    candidates = {
        "random_forest": RandomForestRegressor(n_estimators=500, random_state=42, n_jobs=-1),
        "extra_trees": ExtraTreesRegressor(n_estimators=500, random_state=42, n_jobs=-1),
        "gradient_boosting": GradientBoostingRegressor(random_state=42),
    }
    results: dict[str, Any] = {}
    for name, estimator in candidates.items():
        pipeline = Pipeline([("preprocessor", build_preprocessor()), ("regressor", estimator)])
        model = TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)
        # Keep evaluation on the original target scale, matching production metrics.
        model.fit(x_train, y_train)
        results[name] = regression_metrics(y_test.to_numpy(), model.predict(x_test))
    if output_path is None:
        output_path = Path(METRICS_DIR) / "model_benchmark.json"
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark EstateIQ valuation models")
    parser.add_argument("--data-path", default=str(DEFAULT_TRAINING_DATA))
    parser.add_argument("--output-path", default=str(Path(METRICS_DIR) / "model_benchmark.json"))
    args = parser.parse_args()
    print(json.dumps(benchmark(args.data_path, args.output_path), indent=2))


if __name__ == "__main__":
    main()
