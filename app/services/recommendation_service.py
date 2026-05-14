"""Frontend recommendation service."""

from __future__ import annotations

from typing import Any

from app.services.prediction_service import get_api_client


def recommend(query: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Fetch recommendations from the FastAPI backend."""

    response = get_api_client().post("/recommend", {"query": query, "top_n": top_n})
    return list(response.get("recommendations", []))


def similar_properties(property_name: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Fetch similar properties from the FastAPI backend."""

    response = get_api_client().post(
        "/similar_properties",
        {"property_name": property_name, "top_n": top_n},
    )
    return list(response.get("similar_properties", []))

