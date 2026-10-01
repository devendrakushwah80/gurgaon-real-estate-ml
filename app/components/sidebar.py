"""Sidebar navigation component."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.services.api_client import ApiClient, ApiClientError

PAGES = {
    "Home": "dashboard",
    "Price Predictor": "prediction",
    "Analysis App": "analytics",
    "Recommend Apartments": "recommendations",
    "Property Analysis": "property_analysis",
    "Agent Dashboard": "agent_dashboard",
    "Admin Dashboard": "admin_dashboard",
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

    if st.session_state.get("user"):
        user = st.session_state["user"]
        st.sidebar.success(f"Signed in as {user.get('full_name') or user.get('email')}")
        if st.sidebar.button("Log out", width="stretch"):
            st.session_state.pop("access_token", None)
            st.session_state.pop("user", None)
            st.rerun()
    else:
        with st.sidebar.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", width="stretch")
        if submitted:
            try:
                base_url = st.session_state.get("api_base_url", "http://127.0.0.1:8000")
                result = ApiClient(base_url=base_url).post(
                    "/api/auth/login", {"email": email, "password": password}
                )
                st.session_state["access_token"] = result["access_token"]
                st.session_state["user"] = result["user"]
                st.rerun()
            except ApiClientError as exc:
                st.sidebar.error(str(exc))

    default_page = st.session_state.get("active_page", "dashboard")
    labels = list(PAGES.keys())
    default_index = (
        list(PAGES.values()).index(default_page) if default_page in PAGES.values() else 0
    )
    selected_label = st.sidebar.radio(
        "Navigation",
        labels,
        index=default_index,
        label_visibility="collapsed",
    )
    selected = PAGES[selected_label]
    st.session_state["active_page"] = selected

    st.sidebar.markdown(
        '<div class="sidebar-status">Backend connected locally</div>', unsafe_allow_html=True
    )
    return selected
