"""Table rendering helpers."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def dataframe(df: pd.DataFrame, height: int | None = None) -> None:
    """Render a consistent dataframe."""

    st.dataframe(df, width="stretch", height=height, hide_index=True)


def metric_table(df: pd.DataFrame) -> None:
    """Render compact metric table."""

    st.dataframe(df, width="stretch", hide_index=True)
