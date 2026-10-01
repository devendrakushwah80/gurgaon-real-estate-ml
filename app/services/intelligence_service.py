"""Frontend client for EstateIQ property intelligence endpoints."""

from __future__ import annotations

from typing import Any

from app.services.prediction_service import get_api_client


def discover_properties(**filters: Any) -> list[dict[str, Any]]:
    params = {key: value for key, value in filters.items() if value not in (None, "")}
    return list(get_api_client().get("/api/properties", params=params).get("properties", []))


def get_property(property_id: str) -> dict[str, Any]:
    return get_api_client().get(f"/api/properties/{property_id}")
