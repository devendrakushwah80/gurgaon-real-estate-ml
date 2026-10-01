"""Premium home page for the Gurgaon real-estate intelligence app."""

from __future__ import annotations

import streamlit as st

from app.components.cards import feature_card, intelligence_cards, stat_card
from app.components.charts import locality_activity_map
from app.services.analytics_service import (
    load_geo_market_data,
    load_market_data,
    load_model_metrics,
)
from app.services.api_client import ApiClientError
from app.services.intelligence_service import discover_properties


def render() -> None:
    """Render a calm product home page."""

    df = load_market_data()
    metrics = load_model_metrics()

    st.markdown(
        """
        <section class="home-hero">
            <div class="page-kicker">Premium AI real-estate platform</div>
            <h1>Gurgaon Real Estate Intelligence</h1>
            <p>
                Price prediction, apartment discovery, and locality analytics for a sharper
                view of the Gurgaon property market.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(3, gap="large")
    with cols[0]:
        stat_card("Listings analyzed", f"{len(df):,}", "Processed project and property data")
    with cols[1]:
        stat_card(
            "Median price", f"{df['price'].median():.2f} Cr", "Across the trained market data"
        )
    with cols[2]:
        stat_card("Model R2", f"{metrics.get('r2', 0):.3f}", "Latest saved model metric")

    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

    feature_cols = st.columns(3, gap="large")
    with feature_cols[0]:
        feature_card(
            "Price Predictor",
            "Estimate a property value from locality, area, room mix, furnishing, and floor profile.",
        )
    with feature_cols[1]:
        feature_card(
            "Apartment Recommendations",
            "Find projects by locality intent, radius, amenities, and similarity signals.",
        )
    with feature_cols[2]:
        feature_card(
            "Market Analysis",
            "Explore price-per-sqft maps, locality heatmaps, and real processed data trends.",
        )

    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)
    st.markdown('<div class="results-heading">Recommended For You</div>', unsafe_allow_html=True)
    try:
        recommendations = discover_properties(top_n=6)
        if recommendations:
            intelligence_cards(recommendations)
        else:
            st.info("No source-backed recommendations match the current catalog.")
    except ApiClientError:
        st.info("Start the FastAPI backend to load personalized property intelligence.")

    geo = load_geo_market_data()
    if not geo.empty:
        st.markdown('<div class="chart-stage">', unsafe_allow_html=True)
        st.plotly_chart(locality_activity_map(geo), width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
