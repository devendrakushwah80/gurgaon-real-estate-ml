"""Dedicated fair-value and score endpoints for API consumers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.intelligence import enrich_property, save_score_snapshot
from app.services.property_catalog import find_property

router = APIRouter(tags=["intelligence"])


@router.get("/{property_id}")
def analysis(property_id: str) -> dict:
    record = find_property(property_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    result = enrich_property(record)
    save_score_snapshot(result)
    return result


@router.get("/trust/{property_id}")
def trust(property_id: str) -> dict:
    return analysis(property_id)["trust"]


@router.get("/investment/{property_id}")
def investment(property_id: str) -> dict:
    return analysis(property_id)["investment"]


@router.get("/predictions/fair-value/{property_id}")
def prediction(property_id: str) -> dict:
    return analysis(property_id)["valuation"]
