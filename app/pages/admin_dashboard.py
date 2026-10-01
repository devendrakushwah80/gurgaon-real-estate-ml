"""Protected moderation overview."""

from __future__ import annotations

import streamlit as st

from app.components.cards import empty_state
from app.components.navbar import page_header
from app.services.api_client import ApiClientError
from app.services.prediction_service import get_api_client


def render() -> None:
    page_header(
        "Admin Dashboard", "Moderation and platform health overview for authorized administrators."
    )
    if not st.session_state.get("access_token"):
        empty_state(
            "Admin sign-in required",
            "Sign in with an account that has the analytics.view_admin permission.",
        )
        return
    try:
        overview = get_api_client().get("/api/admin/overview")
        pending = get_api_client().get("/api/admin/properties/pending").get("properties", [])
    except ApiClientError as exc:
        st.error(str(exc))
        return
    columns = st.columns(5)
    for column, (label, value) in zip(columns, overview.items(), strict=False):
        column.metric(label.replace("_", " ").title(), value)
    st.info(
        "All moderation and role-management writes are protected by server-side permissions and are available through the /api/admin endpoints."
    )
    if pending:
        st.subheader("Pending verification")
        for item in pending:
            row = st.columns([3, 2, 1, 1])
            row[0].write(item.get("title"))
            row[1].write(f"{item.get('locality')} · {item.get('listing_price')} Cr")
            if row[2].button("Approve", key=f"approve-{item['id']}"):
                get_api_client().post(
                    f"/api/admin/properties/{item['id']}/moderate?action=approve", {}
                )
                st.rerun()
            if row[3].button("Reject", key=f"reject-{item['id']}"):
                get_api_client().post(
                    f"/api/admin/properties/{item['id']}/moderate?action=reject", {}
                )
                st.rerun()
