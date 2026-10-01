"""Personalized recommendation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.database import connect, json_loads
from app.schemas import RecommendationQuery
from app.security import bearer, get_current_user
from app.services.intelligence import rank_properties, save_score_snapshots
from app.services.property_catalog import search_catalog

router = APIRouter(tags=["recommendations"])


def _optional_user(credentials=Depends(bearer)):
    if credentials is None:
        return None
    return get_current_user(credentials)


@router.post("")
def recommendations(
    payload: RecommendationQuery, user: dict | None = Depends(_optional_user)
) -> dict[str, object]:
    preferences = payload.model_dump(exclude_none=True)
    if user:
        with connect() as db:
            row = db.execute(
                "SELECT * FROM user_preferences WHERE user_id=?", (user["id"],)
            ).fetchone()
        if row:
            stored = dict(row)
            stored["preferred_bhk"] = json_loads(stored.pop("preferred_bhk_json"), [])
            stored["preferred_localities"] = json_loads(stored.pop("preferred_localities_json"), [])
            preferences = {**stored, **preferences}
    records = search_catalog(
        city=preferences.get("city", "gurgaon"),
        budget_min=preferences.get("budget_min"),
        budget_max=preferences.get("budget_max"),
        bhk=preferences.get("bhk"),
        locality=preferences.get("locality"),
        property_type=preferences.get("property_type"),
        min_area_sqft=preferences.get("min_area_sqft"),
    )
    ranked = rank_properties(records, preferences)[: payload.top_n]
    save_score_snapshots(ranked)
    if user:
        with connect() as db:
            for item in ranked:
                db.execute(
                    "INSERT INTO recommendation_events(user_id, property_id, score, reason) VALUES (?, ?, ?, ?)",
                    (
                        user["id"],
                        item["id"],
                        item["recommendation_score"],
                        item["recommendation_reason"],
                    ),
                )
    return {"recommendations": ranked, "count": len(ranked)}
