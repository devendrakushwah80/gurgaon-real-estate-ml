"""Prediction service wrapper used by FastAPI and Streamlit."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

from src.pipelines.inference import PriceInferencePipeline


@lru_cache(maxsize=1)
def get_prediction_pipeline() -> PriceInferencePipeline:
    """Return a cached model inference pipeline."""

    pipeline = PriceInferencePipeline()
    pipeline.load()
    return pipeline


def predict_price(payload: dict[str, Any]) -> float:
    """Predict one property price."""

    return get_prediction_pipeline().predict(payload)


def batch_predict(frame: pd.DataFrame) -> list[float]:
    """Predict a batch of property prices."""

    return get_prediction_pipeline().predict_batch(frame)

