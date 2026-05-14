"""Reusable analytics computations for dashboards and reports."""

from __future__ import annotations

import pandas as pd


def locality_price_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Return median price and listing counts by sector."""

    return (
        df.groupby("sector", dropna=False)
        .agg(median_price=("price", "median"), listing_count=("price", "size"))
        .sort_values(["median_price", "listing_count"], ascending=[False, False])
        .reset_index()
    )


def amenity_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize price by engineered amenity/furnishing columns."""

    group_cols = [col for col in ["furnishing_type", "luxury_category"] if col in df.columns]
    if not group_cols:
        return pd.DataFrame()
    return (
        df.groupby(group_cols, dropna=False)
        .agg(median_price=("price", "median"), listing_count=("price", "size"))
        .reset_index()
    )


def property_type_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize inventory and prices by property type."""

    return (
        df.groupby("property_type", dropna=False)
        .agg(
            listing_count=("price", "size"),
            median_price=("price", "median"),
            mean_price=("price", "mean"),
            median_area=("built_up_area", "median"),
        )
        .reset_index()
    )

