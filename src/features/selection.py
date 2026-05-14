"""Feature selection and categorical bucketing."""

from __future__ import annotations

import pandas as pd

TARGET_COLUMN = "price"

MODEL_FEATURES = [
    "property_type",
    "sector",
    "bedRoom",
    "bathroom",
    "balcony",
    "agePossession",
    "built_up_area",
    "servant room",
    "store room",
    "furnishing_type",
    "luxury_category",
    "floor_category",
]

CATEGORICAL_FEATURES = [
    "property_type",
    "sector",
    "balcony",
    "agePossession",
    "furnishing_type",
    "luxury_category",
    "floor_category",
]

NUMERIC_FEATURES = [
    "bedRoom",
    "bathroom",
    "built_up_area",
    "servant room",
    "store room",
]


def categorize_luxury(score: object) -> str:
    """Bucket numeric luxury score into notebook-derived categories."""

    value = float(score) if pd.notna(score) else 0.0
    if 0 <= value < 50:
        return "Low"
    if 50 <= value < 150:
        return "Medium"
    return "High"


def categorize_floor(floor: object) -> str:
    """Bucket floor number into low, mid, and high floor categories."""

    value = float(floor) if pd.notna(floor) else 0.0
    if 0 <= value <= 2:
        return "Low Floor"
    if 3 <= value <= 10:
        return "Mid Floor"
    return "High Floor"


def build_modeling_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create the final selected modeling table."""

    modeled = df.copy()
    if "luxury_category" not in modeled.columns and "luxury_score" in modeled.columns:
        modeled["luxury_category"] = modeled["luxury_score"].apply(categorize_luxury)
    if "floor_category" not in modeled.columns and "floorNum" in modeled.columns:
        modeled["floor_category"] = modeled["floorNum"].apply(categorize_floor)

    required = MODEL_FEATURES + [TARGET_COLUMN]
    missing = [col for col in required if col not in modeled.columns]
    if missing:
        raise ValueError(f"Missing required modeling columns: {missing}")
    return modeled[required].dropna(subset=[TARGET_COLUMN])

