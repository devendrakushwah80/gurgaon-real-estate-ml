"""Inference pipeline for single and batch predictions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from src.config.paths import DEFAULT_MODEL_PATH
from src.features.selection import MODEL_FEATURES


class PriceInferencePipeline:
    """Load a trained model and serve validated predictions."""

    def __init__(self, model_path: str | Path = DEFAULT_MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        self.model: Any | None = None

    def load(self) -> None:
        """Load the serialized model from disk."""

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {self.model_path}. Run `python -m src.models.train` first."
            )
        self.model = joblib.load(self.model_path)

    def _ensure_loaded(self) -> Any:
        if self.model is None:
            self.load()
        return self.model

    @staticmethod
    def validate_frame(df: pd.DataFrame) -> pd.DataFrame:
        """Validate and order feature columns."""

        missing = [col for col in MODEL_FEATURES if col not in df.columns]
        if missing:
            raise ValueError(f"Prediction input is missing required columns: {missing}")
        return df[MODEL_FEATURES]

    def predict(self, payload: dict[str, Any]) -> float:
        """Return a single price prediction in crore units."""

        frame = pd.DataFrame([payload])
        return float(self.predict_batch(frame)[0])

    def predict_batch(self, frame: pd.DataFrame) -> list[float]:
        """Return batch predictions in crore units."""

        model = self._ensure_loaded()
        features = self.validate_frame(frame)
        return [float(value) for value in model.predict(features)]

