"""Premium Streamlit frontend for the Gurgaon Real Estate ML platform."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
import os

import streamlit as st

from app.components.sidebar import render_sidebar
from app.pages import (
    admin_dashboard,
    agent_dashboard,
    analytics,
    dashboard,
    prediction,
    property_analysis,
    recommendations,
)

PAGE_RENDERERS = {
    "dashboard": dashboard.render,
    "prediction": prediction.render,
    "recommendations": recommendations.render,
    "property_analysis": property_analysis.render,
    "agent_dashboard": agent_dashboard.render,
    "admin_dashboard": admin_dashboard.render,
    "analytics": analytics.render,
}


def load_css() -> None:
    """Load the shared CSS stylesheet."""

    css_path = Path("app/assets/styles.css")
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True
        )


def initialize_session_state() -> None:
    """Initialize frontend runtime state."""

    secrets_url = None
    try:
        if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
            secrets_url = st.secrets["BACKEND_URL"]
    except Exception:  # noqa: BLE001 - Streamlit raises if secrets file missing
        pass

    default_backend_url = os.getenv(
        "BACKEND_URL", os.getenv("API_BASE_URL", secrets_url or "http://127.0.0.1:8000")
    )
    st.session_state.setdefault("api_base_url", default_backend_url)
    st.session_state.setdefault("api_timeout", 8.0)
    st.session_state.setdefault("active_page", "dashboard")
    st.session_state.setdefault("recent_predictions", [])


def main() -> None:
    """Run the Streamlit frontend."""

    st.set_page_config(
        page_title="EstateIQ | Gurgaon Property Intelligence",
        page_icon="app/assets/logo.png",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_session_state()
    load_css()

    selected_page = render_sidebar()
    PAGE_RENDERERS[selected_page]()


if __name__ == "__main__":
    main()
