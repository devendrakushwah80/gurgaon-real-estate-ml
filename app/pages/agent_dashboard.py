"""Protected agent listing workflow."""

from __future__ import annotations

import streamlit as st

from app.components.cards import empty_state, intelligence_cards
from app.components.navbar import page_header
from app.services.api_client import ApiClientError
from app.services.prediction_service import get_api_client


def render() -> None:
    page_header(
        "Agent Dashboard",
        "Create and monitor listings you own; server-side permissions protect every write.",
    )
    if not st.session_state.get("access_token"):
        empty_state(
            "Sign in as an agent", "Use an account granted the AGENT role by an administrator."
        )
        return
    client = get_api_client()
    try:
        mine = client.get("/api/properties/mine").get("properties", [])
    except ApiClientError as exc:
        st.error(str(exc))
        return
    with st.expander("Add listing", expanded=not mine):
        with st.form("agent_listing_form"):
            title = st.text_input("Title")
            locality = st.text_input("Locality", value="Gurgaon")
            property_type = st.selectbox("Property type", ["flat", "house"])
            bhk = st.number_input("BHK", min_value=1, max_value=20, value=3)
            area = st.number_input("Area (sqft)", min_value=100.0, value=1500.0)
            price = st.number_input("Price (Cr)", min_value=0.01, value=1.5)
            source_url = st.text_input("Original listing URL (optional)")
            submitted = st.form_submit_button("Submit listing", type="primary")
        if submitted:
            try:
                client.post(
                    "/api/properties",
                    {
                        "title": title,
                        "description": "",
                        "property_type": property_type,
                        "bhk": int(bhk),
                        "locality": locality,
                        "city": "Gurgaon",
                        "area_sqft": area,
                        "listing_price": price,
                        "amenities": [],
                        "image_urls": [],
                        "source_url": source_url or None,
                    },
                )
                st.success("Listing submitted.")
                st.rerun()
            except ApiClientError as exc:
                st.error(str(exc))
    if mine:
        intelligence_cards(mine)
    else:
        empty_state("No active listings", "Use the form above to submit your first listing.")
