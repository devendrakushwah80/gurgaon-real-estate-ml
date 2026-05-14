"""Market analytics page."""

from __future__ import annotations

import streamlit as st

from app.components.charts import (
    area_price_scatter,
    locality_heatmap,
    locality_trends,
    price_distribution,
    price_per_sqft_map,
)
from app.components.navbar import page_header
from app.services.analytics_service import (
    load_geo_market_data,
    load_locality_trends,
    load_market_data,
)


def render() -> None:
    """Render cinematic market analytics."""

    page_header(
        "Analysis App",
        "Dark, centered market views powered by the processed Gurgaon property dataset.",
    )
    df = load_market_data()
    geo = load_geo_market_data()

    _, control_col, _ = st.columns([1.0, 2.0, 1.0])
    with control_col:
        with st.expander("Market filters", expanded=False):
            property_types = sorted(df["property_type"].dropna().unique().tolist())
            selected_types = st.multiselect("Property type", property_types, default=property_types)
            price_range = st.slider(
                "Price range (Cr)",
                min_value=float(df["price"].min()),
                max_value=float(df["price"].max()),
                value=(float(df["price"].quantile(0.02)), float(df["price"].quantile(0.98))),
            )

    filtered = df[
        df["property_type"].isin(selected_types)
        & df["price"].between(price_range[0], price_range[1])
    ]

    st.markdown('<div class="chart-stage">', unsafe_allow_html=True)
    if not geo.empty:
        st.plotly_chart(price_per_sqft_map(geo), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="spacer-xl"></div>', unsafe_allow_html=True)

    _, chart_col, _ = st.columns([0.45, 3.1, 0.45])
    with chart_col:
        st.plotly_chart(locality_heatmap(filtered), width="stretch")

        cols = st.columns(2, gap="large")
        with cols[0]:
            st.plotly_chart(price_distribution(filtered), width="stretch")
        with cols[1]:
            st.plotly_chart(area_price_scatter(filtered), width="stretch")

        st.plotly_chart(locality_trends(load_locality_trends()), width="stretch")
