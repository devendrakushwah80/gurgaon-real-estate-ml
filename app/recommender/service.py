"""Recommendation service wrapper."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.recommender.engine import PropertyRecommender


@lru_cache(maxsize=1)
def get_recommender() -> PropertyRecommender:
    """Return a cached fitted recommender."""

    return PropertyRecommender().fit()


def recommend(query: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Recommend properties for a query."""

    return get_recommender().recommend(query, top_n=top_n)


def similar_properties(property_name: str, top_n: int = 5) -> list[dict[str, Any]]:
    """Find properties similar to a named project."""

    return get_recommender().similar_properties(property_name, top_n=top_n)

