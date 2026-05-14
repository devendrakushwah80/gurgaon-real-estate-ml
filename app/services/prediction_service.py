"""Frontend prediction service."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.services.analytics_service import append_recent_prediction
from app.services.api_client import ApiClient, ApiClientError


def get_api_client() -> ApiClient:
    """Return the configured API client."""

    return ApiClient(
        base_url=st.session_state.get("api_base_url", "https://gurgaon-real-estate-ml-production.up.railway.app"),
        timeout=float(st.session_state.get("api_timeout", 8.0)),
    )


def predict(payload: dict[str, Any]) -> float:
    """Predict a single property price through the FastAPI backend."""

    response = get_api_client().post("/predict", payload)
    value = float(response["predicted_price_crore"])
    append_recent_prediction(
        {
            "sector": payload.get("sector"),
            "property_type": payload.get("property_type"),
            "built_up_area": payload.get("built_up_area"),
            "prediction_crore": round(value, 3),
        }
    )
    return value


def batch_predict(records: list[dict[str, Any]]) -> list[float]:
    """Predict a batch of records through the FastAPI backend."""

    if not records:
        raise ApiClientError("Upload contains no records.")
    response = get_api_client().post("/batch_predict", {"records": records})
    return [float(value) for value in response["predicted_price_crore"]]


def prepare_batch_download(uploaded: pd.DataFrame, predictions: list[float]) -> pd.DataFrame:
    """Attach predictions to uploaded input data."""

    output = uploaded.copy()
    output["predicted_price_crore"] = predictions
    return output

