"""Premium Streamlit frontend for the Gurgaon Real Estate ML platform."""

from __future__ import annotations

from pathlib import Path
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))
import streamlit as st

from app.components.sidebar import render_sidebar
from app.pages import (
    analytics,
    dashboard,
    prediction,
    recommendations,
)

PAGE_RENDERERS = {
    "dashboard": dashboard.render,
    "prediction": prediction.render,
    "recommendations": recommendations.render,
    "analytics": analytics.render,
}


def load_css() -> None:
    """Load the shared CSS stylesheet."""

    css_path = Path("app/assets/styles.css")
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def initialize_session_state() -> None:
    """Initialize frontend runtime state."""

    st.session_state.setdefault("api_base_url", "http://127.0.0.1:8001")
    st.session_state.setdefault("api_timeout", 8.0)
    st.session_state.setdefault("active_page", "dashboard")
    st.session_state.setdefault("recent_predictions", [])


def main() -> None:
    """Run the Streamlit frontend."""

    st.set_page_config(
        page_title="Gurgaon Real Estate ML",
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
