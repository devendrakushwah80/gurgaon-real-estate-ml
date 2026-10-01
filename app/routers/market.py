"""City-scoped market insight endpoints."""

from fastapi import APIRouter, Query

from app.services.market_insights import build_market_insights

router = APIRouter(tags=["market"])


@router.get("/insights")
def market_insights(city: str = Query(default="gurgaon", max_length=80)) -> dict[str, object]:
    return build_market_insights(city)
