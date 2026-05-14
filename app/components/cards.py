"""Card-style Streamlit components."""

from __future__ import annotations

from collections.abc import Iterable
from html import escape
from typing import Any

import streamlit as st


def kpi_card(label: str, value: str, help_text: str | None = None) -> None:
    """Render a small KPI card."""

    help_html = f'<div class="kpi-help">{escape(help_text)}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{escape(label)}</div>
            <div class="kpi-value">{escape(value)}</div>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def info_panel(title: str, body: str) -> None:
    """Render a compact information panel."""

    st.markdown(
        f"""
        <div class="panel">
            <h3>{escape(title)}</h3>
            <p class="page-subtitle">{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(title: str, body: str) -> None:
    """Render a quiet product feature card."""

    st.markdown(
        f"""
        <div class="feature-card">
            <div class="feature-title">{escape(title)}</div>
            <div class="feature-body">{escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label: str, value: str, help_text: str | None = None) -> None:
    """Render a compact centered statistic."""

    help_html = f'<div class="stat-help">{escape(help_text)}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="stat-card">
            <div class="stat-label">{escape(label)}</div>
            <div class="stat-value">{escape(value)}</div>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def prediction_result(
    value: float,
    lower: float,
    upper: float,
    nearby_price: float | None = None,
    price_per_sqft: float | None = None,
) -> None:
    """Render a prediction result card."""

    nearby = f"{nearby_price:.2f} Cr" if nearby_price is not None else "Not enough local data"
    sqft = f"Rs {price_per_sqft:,.0f}" if price_per_sqft is not None else "Unavailable"
    st.markdown(
        f"""
        <div class="result-card primary-result">
            <div class="result-label">Predicted Price</div>
            <div class="prediction-value">{value:.2f} Cr</div>
            <div class="result-help">Confidence range: {lower:.2f} Cr - {upper:.2f} Cr</div>
        </div>
        <div class="result-grid">
            <div class="result-card">
                <div class="result-label">Nearby Comparison</div>
                <div class="result-value">{nearby}</div>
                <div class="result-help">Median price for matching locality</div>
            </div>
            <div class="result-card">
                <div class="result-label">Price Per Sqft</div>
                <div class="result-value">{sqft}</div>
                <div class="result-help">Derived from the model estimate</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def recommendation_cards(records: Iterable[dict[str, Any]]) -> None:
    """Render recommendation results as understated cards."""

    for item in records:
        title = escape(str(item.get("property_name") or "Unnamed property"))
        subtitle = escape(str(item.get("property_sub_name") or "Project metadata"))
        locality = escape(str(item.get("locality") or "Gurgaon"))
        price = escape(str(item.get("estimated_price") or "Price on request"))
        amenities = [escape(str(value)) for value in item.get("amenities", [])[:4]]
        score = item.get("score")
        score_text = f"{float(score) * 100:.1f}%" if isinstance(score, int | float) else "N/A"
        link = item.get("link")
        link_html = f'<a class="muted-link" href="{escape(str(link))}" target="_blank">View source</a>' if link else ""
        amenity_html = "".join(f'<span class="tag">{amenity}</span>' for amenity in amenities)
        st.markdown(
            f"""
            <div class="recommendation-card">
                <div>
                    <div class="recommendation-title">{title}</div>
                    <div class="recommendation-meta">{subtitle}</div>
                    <div class="tag-row"><span class="tag locality-tag">{locality}</span>{amenity_html}</div>
                    {link_html}
                </div>
                <div class="recommendation-side">
                    <div class="card-price">{price}</div>
                    <span class="score-pill">Similarity {score_text}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def empty_state(title: str, body: str) -> None:
    """Render a professional empty state."""

    st.markdown(
        f"""
        <div class="state-box">
            <strong>{escape(title)}</strong><br />
            {escape(body)}
        </div>
        """,
        unsafe_allow_html=True,
    )
