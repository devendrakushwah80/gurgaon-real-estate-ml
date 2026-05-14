"""Plotly chart helpers for the Streamlit frontend."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PLOTLY_TEMPLATE = "plotly_dark"
NEUTRAL_SEQUENCE = ["#BFC7D5", "#8C95A6", "#626C7C", "#D7DCE5", "#AEB6C4", "#747D8F"]
RED_SCALE = ["#151B24", "#34313A", "#6D3840", "#A23E46", "#D14F58"]


def _layout(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        paper_bgcolor="#0A0F16",
        plot_bgcolor="#0A0F16",
        font={"color": "#EEF2F6", "size": 12},
        margin={"l": 24, "r": 24, "t": 58, "b": 38},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        title={"font": {"size": 18, "color": "#F5F7FA"}, "x": 0.03},
    )
    fig.update_xaxes(gridcolor="#202A36", zerolinecolor="#334155", title_font={"color": "#AAB3C2"})
    fig.update_yaxes(gridcolor="#202A36", zerolinecolor="#334155", title_font={"color": "#AAB3C2"})
    return fig


def price_distribution(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df,
        x="price",
        nbins=48,
        title="Price Distribution",
        color_discrete_sequence=["#D14F58"],
    )
    return _layout(fig)


def area_price_scatter(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df,
        x="built_up_area",
        y="price",
        color="property_type",
        title="Area vs Price",
        color_discrete_sequence=NEUTRAL_SEQUENCE,
        opacity=0.72,
    )
    return _layout(fig)


def property_distribution(df: pd.DataFrame) -> go.Figure:
    counts = df["property_type"].value_counts().reset_index()
    counts.columns = ["property_type", "count"]
    fig = px.bar(
        counts,
        x="property_type",
        y="count",
        title="Property Distribution",
        color="property_type",
        color_discrete_sequence=NEUTRAL_SEQUENCE,
    )
    fig.update_layout(showlegend=False)
    return _layout(fig, height=300)


def locality_trends(trends: pd.DataFrame, top_n: int = 15) -> go.Figure:
    data = trends.head(top_n).sort_values("median_price")
    fig = px.bar(
        data,
        x="median_price",
        y="sector",
        orientation="h",
        title="Top Localities by Median Price",
        color_discrete_sequence=["#D14F58"],
    )
    return _layout(fig, height=430)


def price_growth_proxy(df: pd.DataFrame) -> go.Figure:
    """Plot median price by possession bucket as a market maturity proxy."""

    if "agePossession" not in df.columns:
        return go.Figure()
    order = [
        "Under Construction",
        "New Property",
        "Relatively New",
        "Moderately Old",
        "Old Property",
    ]
    grouped = (
        df.groupby("agePossession", dropna=False)
        .agg(median_price=("price", "median"), listing_count=("price", "size"))
        .reindex(order)
        .dropna()
        .reset_index()
    )
    fig = px.line(
        grouped,
        x="agePossession",
        y="median_price",
        markers=True,
        title="Median Price by Property Maturity",
    )
    fig.update_traces(line={"color": "#CBD5E1", "width": 2}, marker={"size": 7})
    return _layout(fig, height=320)


def locality_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = (
        df.pivot_table(
            index="sector",
            columns="property_type",
            values="price",
            aggfunc="median",
        )
        .sort_index()
        .tail(30)
    )
    fig = px.imshow(
        pivot,
        title="Locality Price Heatmap",
        color_continuous_scale=RED_SCALE,
        aspect="auto",
    )
    return _layout(fig, height=520)


def price_per_sqft_map(df: pd.DataFrame) -> go.Figure:
    """Render a centered locality price-per-sqft map."""

    fig = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        size="listing_count",
        color="price_per_sqft",
        hover_name="sector",
        hover_data={
            "median_price": ":.2f",
            "price_per_sqft": ":,.0f",
            "listing_count": True,
            "lat": False,
            "lon": False,
        },
        color_continuous_scale=RED_SCALE,
        size_max=28,
        zoom=9.8,
        center={"lat": 28.4595, "lon": 77.0266},
        title="Gurgaon Price Per Sqft Map",
    )
    fig.update_layout(mapbox_style="carto-darkmatter")
    return _layout(fig, height=620)


def locality_activity_map(df: pd.DataFrame) -> go.Figure:
    """Render a listing-density map by locality."""

    fig = px.scatter_mapbox(
        df,
        lat="lat",
        lon="lon",
        size="listing_count",
        color="median_price",
        hover_name="sector",
        hover_data={
            "median_price": ":.2f",
            "listing_count": True,
            "price_per_sqft": ":,.0f",
            "lat": False,
            "lon": False,
        },
        color_continuous_scale=RED_SCALE,
        size_max=34,
        zoom=9.8,
        center={"lat": 28.4595, "lon": 77.0266},
        title="Locality Demand And Price Map",
    )
    fig.update_layout(mapbox_style="carto-darkmatter")
    return _layout(fig, height=560)


def feature_importance_chart(df: pd.DataFrame, top_n: int = 18) -> go.Figure:
    data = df.head(top_n).sort_values("importance")
    fig = px.bar(
        data,
        x="importance",
        y="feature",
        orientation="h",
        title="Feature Importance",
        color_discrete_sequence=["#CBD5E1"],
    )
    return _layout(fig, height=500)
