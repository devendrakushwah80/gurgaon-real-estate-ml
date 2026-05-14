"""Training pipeline for real-estate price prediction."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config.paths import (
    DEFAULT_FEATURE_IMPORTANCE_PATH,
    DEFAULT_METRICS_PATH,
    DEFAULT_MODEL_METADATA_PATH,
    DEFAULT_MODEL_PATH,
    DEFAULT_TRAINING_DATA,
    ensure_project_dirs,
)
from src.features.selection import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)
from src.models.evaluate import regression_metrics
from src.utils.logging import get_logger

LOGGER = get_logger(__name__)


def build_preprocessor() -> ColumnTransformer:
    """Build the sklearn preprocessing graph."""

    return ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("numeric", StandardScaler(), NUMERIC_FEATURES),
        ],
        remainder="drop",
    )


def build_model(random_state: int = 42) -> TransformedTargetRegressor:
    """Build the final model pipeline.

    The target is log-transformed during training and inverse-transformed during
    prediction, matching the notebook experimentation pattern.
    """

    estimator = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=500,
                    random_state=random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    return TransformedTargetRegressor(
        regressor=estimator,
        func=np.log1p,
        inverse_func=np.expm1,
    )


def load_training_frame(path: str | Path = DEFAULT_TRAINING_DATA) -> pd.DataFrame:
    """Load and validate the selected modeling dataset."""

    df = pd.read_csv(path)
    required = MODEL_FEATURES + [TARGET_COLUMN]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Training data is missing required columns: {missing}")
    return df[required].dropna(subset=[TARGET_COLUMN])


def _feature_importance(model: TransformedTargetRegressor) -> pd.DataFrame:
    """Extract feature importance from the fitted RandomForest pipeline."""

    pipeline = model.regressor_
    preprocessor = pipeline.named_steps["preprocessor"]
    regressor = pipeline.named_steps["regressor"]
    names = preprocessor.get_feature_names_out()
    importances = getattr(regressor, "feature_importances_", np.zeros(len(names)))
    return (
        pd.DataFrame({"feature": names, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def train(
    data_path: str | Path = DEFAULT_TRAINING_DATA,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    metrics_path: str | Path = DEFAULT_METRICS_PATH,
    metadata_path: str | Path = DEFAULT_MODEL_METADATA_PATH,
    feature_importance_path: str | Path = DEFAULT_FEATURE_IMPORTANCE_PATH,
    test_size: float = 0.2,
    random_state: int = 42,
) -> dict[str, Any]:
    """Train, evaluate, and persist the production price model."""

    ensure_project_dirs()
    df = load_training_frame(data_path)
    X = df[MODEL_FEATURES]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    model = build_model(random_state=random_state)
    LOGGER.info("Training model on %s rows", len(X_train))
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    metrics = regression_metrics(y_test.to_numpy(), predictions)

    model_path = Path(model_path)
    metrics_path = Path(metrics_path)
    metadata_path = Path(metadata_path)
    feature_importance_path = Path(feature_importance_path)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    feature_importance_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    feature_importance = _feature_importance(model)
    feature_importance.to_csv(feature_importance_path, index=False)

    metadata = {
        "model_type": "TransformedTargetRegressor(RandomForestRegressor)",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_data": str(data_path),
        "model_path": str(model_path),
        "features": MODEL_FEATURES,
        "target": TARGET_COLUMN,
        "metrics": metrics,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    LOGGER.info("Saved model to %s", model_path)
    return metadata


def main() -> None:
    """CLI entry point for model training."""

    parser = argparse.ArgumentParser(description="Train the real-estate price model")
    parser.add_argument("--data-path", default=str(DEFAULT_TRAINING_DATA))
    parser.add_argument("--model-path", default=str(DEFAULT_MODEL_PATH))
    args = parser.parse_args()
    metadata = train(data_path=args.data_path, model_path=args.model_path)
    print(json.dumps(metadata["metrics"], indent=2))


if __name__ == "__main__":
    main()

