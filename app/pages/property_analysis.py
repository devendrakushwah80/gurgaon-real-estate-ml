"""Property-level Trust, Investment, and fair-value analysis page."""

from __future__ import annotations

import streamlit as st

from app.components.cards import empty_state
from app.components.navbar import page_header
from app.services.api_client import ApiClientError
from app.services.intelligence_service import discover_properties, get_property


def render() -> None:
    page_header(
        "Property Analysis",
        "Review fair value, listing confidence, and data-based investment signals.",
    )
    try:
        records = discover_properties(top_n=50)
    except ApiClientError as exc:
        st.error(str(exc))
        return
    if not records:
        empty_state(
            "No properties available", "Start the FastAPI backend and check the source exports."
        )
        return
    labels = {f"{item.get('title', 'Property')} · {item.get('id')}": item["id"] for item in records}
    selected = st.selectbox("Choose a property", list(labels))
    try:
        item = get_property(labels[selected])
    except ApiClientError as exc:
        st.error(str(exc))
        return
    valuation = item.get("valuation", {})
    trust = item.get("trust", {})
    investment = item.get("investment", {})
    cols = st.columns(4)
    cols[0].metric("Listing price", f"₹{float(item.get('listing_price') or 0):.2f} Cr")
    cols[1].metric("AI fair value", f"₹{float(valuation.get('fair_value') or 0):.2f} Cr")
    cols[2].metric("Trust Score", f"{trust.get('score', '—')}/100")
    cols[3].metric("Investment Score", f"{investment.get('score', '—')}/100")
    st.caption(
        valuation.get("disclaimer", "AI-generated estimate based on available property data.")
    )
    left, right = st.columns(2)
    with left:
        st.subheader(trust.get("label", "Trust analysis"))
        st.json(trust.get("breakdown", {}))
        for signal in trust.get("positive_signals", []):
            st.success(signal)
        for warning in trust.get("warnings", []):
            st.warning(warning)
    with right:
        st.subheader(investment.get("label", "Investment analysis"))
        st.json(investment.get("breakdown", {}))
        for signal in investment.get("positive_signals", []):
            st.success(signal)
        for warning in investment.get("warnings", []):
            st.warning(warning)
    st.info(
        "EstateIQ provides AI-generated estimates and data-driven indicators. Property authenticity and investment decisions should be independently verified."
    )
