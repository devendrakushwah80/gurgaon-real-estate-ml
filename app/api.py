"""FastAPI application exposing prediction and recommendation endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.prediction.service import batch_predict as run_batch_predict
from app.prediction.service import predict_price
from app.recommender.service import recommend, similar_properties
from src.features.selection import MODEL_FEATURES

api = FastAPI(title="Gurgaon Real Estate ML API", version="1.0.0")


class PropertyFeatures(BaseModel):
    """Request body for one price prediction."""

    model_config = ConfigDict(populate_by_name=True)

    property_type: str
    sector: str
    bedRoom: float
    bathroom: float
    balcony: str
    agePossession: str
    built_up_area: float
    servant_room: int = Field(alias="servant room")
    store_room: int = Field(alias="store room")
    furnishing_type: str
    luxury_category: str
    floor_category: str

    def to_model_payload(self) -> dict[str, Any]:
        """Return a dict with exact training column names."""

        payload = self.model_dump(by_alias=True)
        return {feature: payload[feature] for feature in MODEL_FEATURES}


class BatchPredictionRequest(BaseModel):
    """Request body for batch prediction."""

    records: list[dict[str, Any]]


class RecommendationRequest(BaseModel):
    """Request body for recommendations."""

    query: str
    top_n: int = 5


class SimilarPropertyRequest(BaseModel):
    """Request body for similar project lookup."""

    property_name: str
    top_n: int = 5


@api.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""

    return {"status": "ok"}


@api.post("/predict")
def predict(payload: PropertyFeatures) -> dict[str, float]:
    """Predict price for a single property."""

    try:
        prediction = predict_price(payload.to_model_payload())
        return {"predicted_price_crore": prediction}
    except Exception as exc:  # noqa: BLE001 - API boundary should return clean errors
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.post("/batch_predict")
def batch_predict(payload: BatchPredictionRequest) -> dict[str, list[float]]:
    """Predict prices for multiple properties."""

    try:
        frame = pd.DataFrame(payload.records)
        predictions = run_batch_predict(frame)
        return {"predicted_price_crore": predictions}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.post("/recommend")
def recommend_endpoint(payload: RecommendationRequest) -> dict[str, list[dict[str, Any]]]:
    """Return property recommendations for a query."""

    try:
        return {"recommendations": recommend(payload.query, payload.top_n)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api.post("/similar_properties")
def similar_properties_endpoint(payload: SimilarPropertyRequest) -> dict[str, list[dict[str, Any]]]:
    """Return properties similar to a named property."""

    try:
        return {"similar_properties": similar_properties(payload.property_name, payload.top_n)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
