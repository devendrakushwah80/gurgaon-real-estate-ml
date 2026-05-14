"""Top-level page header components."""

from __future__ import annotations

import streamlit as st


def page_header(title: str, subtitle: str, kicker: str = "Gurgaon Real Estate Intelligence") -> None:
    """Render a centered premium page header."""

    st.markdown(
        f"""
        <section class="page-hero">
            <div class="page-kicker">{kicker}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
