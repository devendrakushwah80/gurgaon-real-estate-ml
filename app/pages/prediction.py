"""Single property prediction page."""

from __future__ import annotations

import streamlit as st

from app.components.cards import prediction_result
from app.components.navbar import page_header
from app.services.analytics_service import load_market_data
from app.services.api_client import ApiClientError
from app.services.prediction_service import predict


def render() -> None:
    """Render the centered prediction form."""

    page_header(
        "Price Predictor",
        "A focused valuation workflow for Gurgaon apartments and houses.",
    )
    df = load_market_data()
    sectors = sorted(df["sector"].dropna().astype(str).unique().tolist())
    property_types = sorted(df["property_type"].dropna().astype(str).unique().tolist())

    _, form_col, _ = st.columns([1.25, 1.7, 1.25])
    with form_col:
        st.markdown('<div class="form-title">Property Details</div>', unsafe_allow_html=True)
        with st.form("prediction_form", clear_on_submit=False):
            property_type = st.selectbox("Property type", property_types)
            sector = st.selectbox("Sector / locality", sectors, index=_default_index(sectors, "sector 48"))
            built_up_area = st.number_input(
                "Built-up area",
                min_value=100.0,
                max_value=20000.0,
                value=1500.0,
                step=50.0,
            )
            bed_room = st.number_input("Bedrooms", min_value=1, max_value=12, value=3, step=1)
            bathroom = st.number_input("Bathrooms", min_value=1, max_value=12, value=3, step=1)
            balcony = st.selectbox("Balcony", ["0", "1", "2", "3", "3+"])
            age_possession = st.selectbox(
                "Age / possession",
                ["New Property", "Relatively New", "Moderately Old", "Old Property", "Under Construction"],
            )
            furnishing_type = st.selectbox("Furnishing", ["unfurnished", "semifurnished", "furnished"])
            luxury_category = st.selectbox("Luxury category", ["Low", "Medium", "High"])
            floor_category = st.selectbox("Floor category", ["Low Floor", "Mid Floor", "High Floor"])
            servant_room = int(st.checkbox("Servant room"))
            store_room = int(st.checkbox("Store room"))

            st.markdown('<div class="button-space"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Predict Price", type="primary", width="stretch")

    payload = {
        "property_type": property_type,
        "sector": sector,
        "bedRoom": float(bed_room),
        "bathroom": float(bathroom),
        "balcony": balcony,
        "agePossession": age_possession,
        "built_up_area": float(built_up_area),
        "servant room": servant_room,
        "store room": store_room,
        "furnishing_type": furnishing_type,
        "luxury_category": luxury_category,
        "floor_category": floor_category,
    }

    if submitted:
        with st.spinner("Running valuation model..."):
            try:
                value = predict(payload)
                lower, upper = _confidence_range(value)
                nearby = _nearby_median(df, sector, property_type)
                price_per_sqft = (value * 10_000_000) / built_up_area
                _, result_col, _ = st.columns([1.05, 1.9, 1.05])
                with result_col:
                    prediction_result(value, lower, upper, nearby, price_per_sqft)
            except ApiClientError as exc:
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001
                st.error(f"Prediction failed: {exc}")


def _confidence_range(value: float) -> tuple[float, float]:
    """Derive a conservative display range from the point estimate."""

    spread = max(value * 0.12, 0.15)
    return max(value - spread, 0.0), value + spread


def _nearby_median(df, sector: str, property_type: str) -> float | None:
    matched = df[(df["sector"] == sector) & (df["property_type"] == property_type)]
    if matched.empty:
        matched = df[df["sector"] == sector]
    if matched.empty:
        return None
    return float(matched["price"].median())


def _default_index(values: list[str], default: str) -> int:
    return values.index(default) if default in values else 0
