"""Reusable data cleaning routines extracted from notebook workflows."""

from __future__ import annotations

import re
from collections.abc import Iterable

import numpy as np
import pandas as pd

PRICE_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)")


def treat_price(value: object) -> float:
    """Convert 99acres price strings to crore units.

    The original notebooks used separate flat and house implementations. This
    shared version handles common strings such as "1.25 Cr", "85 Lac", and
    missing/price-on-request values.
    """

    if pd.isna(value):
        return np.nan

    text = str(value).lower().replace(",", "").strip()
    if not text or "price on request" in text:
        return np.nan

    match = PRICE_PATTERN.search(text)
    if not match:
        return np.nan

    amount = float(match.group(1))
    if "lac" in text or "lakh" in text:
        return amount / 100
    if "cr" in text or "crore" in text:
        return amount
    return amount


def normalize_sector(value: object) -> str:
    """Normalize sector names into a compact lowercase representation."""

    if pd.isna(value):
        return "unknown"
    text = str(value).lower().strip()
    text = text.replace("gurgaon", "").replace("gurugram", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,-") or "unknown"


def clean_property_frame(df: pd.DataFrame, property_type: str) -> pd.DataFrame:
    """Apply shared raw listing cleanup for flats or houses."""

    cleaned = df.copy()
    cleaned["property_type"] = property_type

    if "price" in cleaned.columns:
        cleaned["price"] = cleaned["price"].apply(treat_price)

    if "rate" in cleaned.columns and "price_per_sqft" not in cleaned.columns:
        cleaned = cleaned.rename(columns={"rate": "price_per_sqft"})

    if "price_per_sqft" not in cleaned.columns and {"price", "area"}.issubset(cleaned.columns):
        area = pd.to_numeric(cleaned["area"], errors="coerce")
        cleaned["price_per_sqft"] = (cleaned["price"] * 10_000_000) / area

    cleaned = cleaned.drop(columns=["link", "property_id"], errors="ignore")
    return cleaned.dropna(subset=["price"], how="any")


def merge_property_frames(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Merge cleaned property DataFrames with aligned columns."""

    return pd.concat(list(frames), ignore_index=True, sort=False).drop_duplicates()


def clean_level_two(df: pd.DataFrame) -> pd.DataFrame:
    """Apply second-stage cleanup used before feature engineering."""

    cleaned = df.copy()
    if "address" in cleaned.columns and "sector" not in cleaned.columns:
        cleaned["sector"] = cleaned["address"].apply(normalize_sector)
    elif "sector" in cleaned.columns:
        cleaned["sector"] = cleaned["sector"].apply(normalize_sector)

    keep_cols = [
        "property_type",
        "society",
        "sector",
        "price",
        "price_per_sqft",
        "area",
        "areaWithType",
        "bedRoom",
        "bathroom",
        "balcony",
        "additionalRoom",
        "floorNum",
        "facing",
        "agePossession",
        "nearbyLocations",
        "furnishDetails",
        "features",
    ]
    existing = [col for col in keep_cols if col in cleaned.columns]
    return cleaned[existing].drop_duplicates()

