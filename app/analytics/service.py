"""Analytics service helpers for dashboards."""

from __future__ import annotations

import pandas as pd

from src.analytics.insights import amenity_summary, locality_price_trends, property_type_summary
from src.config.paths import DEFAULT_TRAINING_DATA


def load_dashboard_data() -> pd.DataFrame:
    """Load the processed modeling dataset for analytics views."""

    return pd.read_csv(DEFAULT_TRAINING_DATA)


def dashboard_summaries(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build reusable dashboard summary tables."""

    return {
        "locality_trends": locality_price_trends(df),
        "amenity_summary": amenity_summary(df),
        "property_type_summary": property_type_summary(df),
    }

