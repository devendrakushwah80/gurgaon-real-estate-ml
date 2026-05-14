"""Sidebar navigation component."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

PAGES = {
    "Home": "dashboard",
    "Price Predictor": "prediction",
    "Analysis App": "analytics",
    "Recommend Apartments": "recommendations",
}


def render_sidebar() -> str:
    """Render sidebar navigation and return the selected page key."""

    logo_path = Path("app/assets/logo.png")
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=42)
    st.sidebar.markdown('<div class="app-title">EstateIQ</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="app-caption">Gurgaon property intelligence</div>',
        unsafe_allow_html=True,
    )

    default_page = st.session_state.get("active_page", "dashboard")
    labels = list(PAGES.keys())
    default_index = list(PAGES.values()).index(default_page) if default_page in PAGES.values() else 0
    selected_label = st.sidebar.radio(
        "Navigation",
        labels,
        index=default_index,
        label_visibility="collapsed",
    )
    selected = PAGES[selected_label]
    st.session_state["active_page"] = selected

    st.sidebar.markdown('<div class="sidebar-status">Backend connected locally</div>', unsafe_allow_html=True)
    return selected
