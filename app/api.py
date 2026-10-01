"""FastAPI application exposing prediction and recommendation endpoints."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.prediction.service import batch_predict as run_batch_predict
from app.prediction.service import predict_price
from app.recommender.service import recommend, similar_properties
from app.routers import admin, auth, intelligence, market, properties, recommendations
from src.features.selection import MODEL_FEATURES

api = FastAPI(title="EstateIQ Multi-City Property Intelligence API", version="1.2.0")

api.include_router(auth.router, prefix="/api/auth")
api.include_router(properties.router, prefix="/api/properties")
api.include_router(intelligence.router, prefix="/api/intelligence")
api.include_router(market.router, prefix="/api/market")
api.include_router(recommendations.router, prefix="/api/recommendations")
api.include_router(admin.router, prefix="/api/admin")

api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:8501,http://127.0.0.1:8501",
        ).split(",")
        if origin.strip()
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PropertyFeatures(BaseModel):
    """Request body for one price prediction."""

    model_config = ConfigDict(populate_by_name=True)

    property_type: str
    sector: str
    bedRoom: float = Field(gt=0, le=20)
    bathroom: float = Field(gt=0, le=20)
    balcony: str
    agePossession: str
    built_up_area: float = Field(gt=0, le=1_000_000)
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
    top_n: int = Field(default=5, ge=1, le=50)


class SimilarPropertyRequest(BaseModel):
    """Request body for similar project lookup."""

    property_name: str
    top_n: int = Field(default=5, ge=1, le=50)


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
        raise HTTPException(
            status_code=400, detail="Prediction input could not be processed"
        ) from exc


@api.post("/batch_predict")
def batch_predict(payload: BatchPredictionRequest) -> dict[str, list[float]]:
    """Predict prices for multiple properties."""

    try:
        frame = pd.DataFrame(payload.records)
        predictions = run_batch_predict(frame)
        return {"predicted_price_crore": predictions}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="Batch prediction input could not be processed"
        ) from exc


@api.post("/recommend")
def recommend_endpoint(payload: RecommendationRequest) -> dict[str, list[dict[str, Any]]]:
    """Return property recommendations for a query."""

    try:
        return {"recommendations": recommend(payload.query, payload.top_n)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="Recommendation request could not be processed"
        ) from exc


@api.post("/similar_properties")
def similar_properties_endpoint(payload: SimilarPropertyRequest) -> dict[str, list[dict[str, Any]]]:
    """Return properties similar to a named property."""

    try:
        return {"similar_properties": similar_properties(payload.property_name, payload.top_n)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail="Similar-property request could not be processed"
        ) from exc
