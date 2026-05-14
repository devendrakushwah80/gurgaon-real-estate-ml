"""Reusable Plotly chart factories."""

from __future__ import annotations

import pandas as pd
import plotly.express as px


def price_distribution(df: pd.DataFrame):
    """Create a price distribution histogram."""

    return px.histogram(df, x="price", nbins=50, title="Price Distribution")


def price_by_sector(df: pd.DataFrame):
    """Create a sector-wise price boxplot."""

    return px.box(df, x="sector", y="price", title="Price by Sector")


def area_price_scatter(df: pd.DataFrame):
    """Create an area-vs-price scatter plot."""

    return px.scatter(
        df,
        x="built_up_area",
        y="price",
        color="property_type",
        title="Area vs Price",
    )

