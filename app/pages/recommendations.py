"""Apartment recommendation page."""

from __future__ import annotations

import ast
import re
from typing import Any

import pandas as pd
import streamlit as st

from app.components.cards import empty_state, recommendation_cards
from app.components.navbar import page_header
from app.services.analytics_service import load_apartment_data
from app.services.api_client import ApiClientError
from app.services.recommendation_service import recommend, similar_properties
from src.recommender.engine import extract_list


def render() -> None:
    """Render the centered apartment recommendation workflow."""

    page_header(
        "Recommend Apartments",
        "Select location intent, distance comfort, and project similarity signals.",
    )
    apartment_df = load_apartment_data()
    localities = _locality_options(apartment_df)
    projects = sorted(apartment_df["PropertyName"].dropna().astype(str).unique().tolist()) if not apartment_df.empty else []

    _, form_col, _ = st.columns([1.25, 1.65, 1.25])
    with form_col:
        st.markdown('<div class="form-title">Select Location and Radius</div>', unsafe_allow_html=True)
        with st.form("recommendation_form", clear_on_submit=False):
            locality = st.selectbox("Location", localities, index=_default_index(localities, "Sector 113"))
            radius = st.number_input("Radius in km", min_value=1, max_value=25, value=5, step=1)
            mode = st.selectbox("Recommendation selector", ["Location and amenities", "Similar apartment"])
            amenities = st.multiselect(
                "Amenities",
                ["Swimming Pool", "Club House", "Gym", "Park", "24x7 Security", "Metro", "School", "Hospital"],
                default=["Swimming Pool", "Club House"],
            )
            project_name = ""
            if mode == "Similar apartment" and projects:
                project_name = st.selectbox("Known apartment", projects)
            top_n = st.slider("Recommendations", min_value=3, max_value=12, value=6)

            st.markdown('<div class="button-space"></div>', unsafe_allow_html=True)
            submitted = st.form_submit_button("Recommend", type="primary", width="stretch")

    _, result_col, _ = st.columns([0.8, 2.25, 0.8])
    with result_col:
        if not submitted:
            empty_state("Recommendations will appear here", "Choose a locality and run the search.")
            return

        try:
            with st.spinner("Finding apartment matches..."):
                if mode == "Similar apartment" and project_name:
                    records = similar_properties(project_name, top_n=top_n)
                else:
                    query = _build_query(locality, radius, amenities)
                    records = recommend(query, top_n=top_n)

            if not records:
                empty_state("No matches returned", "Try a broader locality or fewer amenity filters.")
                return

            st.markdown('<div class="results-heading">Recommended Apartments</div>', unsafe_allow_html=True)
            recommendation_cards(_enrich_records(records, apartment_df))
        except ApiClientError as exc:
            st.error(str(exc))


def _build_query(locality: str, radius: int, amenities: list[str]) -> str:
    return f"{locality} within {radius} km {' '.join(amenities)} premium apartment Gurgaon"


def _locality_options(df: pd.DataFrame) -> list[str]:
    if df.empty or "PropertySubName" not in df.columns:
        return ["Gurgaon"]
    sectors = sorted(
        {
            match.group(0).title()
            for value in df["PropertySubName"].dropna().astype(str)
            for match in re.finditer(r"sector\s+\d+[a-z]?", value, flags=re.IGNORECASE)
        }
    )
    return sectors or ["Gurgaon"]


def _enrich_records(records: list[dict[str, Any]], apartment_df: pd.DataFrame) -> list[dict[str, Any]]:
    if apartment_df.empty:
        return records

    lookup = apartment_df.set_index("PropertyName", drop=False)
    enriched = []
    for record in records:
        item = dict(record)
        name = item.get("property_name")
        if name in lookup.index:
            row = lookup.loc[name]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            item["locality"] = _extract_locality(row.get("PropertySubName"))
            item["amenities"] = extract_list(row.get("TopFacilities"))
            item["estimated_price"] = _extract_price(row.get("PriceDetails"))
        enriched.append(item)
    return enriched


def _extract_locality(value: object) -> str:
    match = re.search(r"sector\s+\d+[a-z]?", str(value), flags=re.IGNORECASE)
    return match.group(0).title() if match else "Gurgaon"


def _extract_price(value: object) -> str:
    try:
        details = ast.literal_eval(str(value))
    except (ValueError, SyntaxError):
        return "Price on request"

    if not isinstance(details, dict):
        return "Price on request"
    ranges = [
        config.get("price-range")
        for config in details.values()
        if isinstance(config, dict) and config.get("price-range")
    ]
    return str(ranges[0]) if ranges else "Price on request"


def _default_index(values: list[str], default: str) -> int:
    return values.index(default) if default in values else 0
