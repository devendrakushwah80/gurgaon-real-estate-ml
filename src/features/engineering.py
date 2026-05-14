"""Feature engineering logic extracted from notebooks."""

from __future__ import annotations

import ast
import re

import numpy as np
import pandas as pd


def categorize_age_possession(value: object) -> str:
    """Map raw possession strings to stable model categories."""

    if pd.isna(value):
        return "Undefined"
    text = str(value)
    if "0 to 1 Year Old" in text or "Within 6 months" in text or "Within 3 months" in text:
        return "New Property"
    if "1 to 5 Year Old" in text:
        return "Relatively New"
    if "5 to 10 Year Old" in text:
        return "Moderately Old"
    if "10+ Year Old" in text:
        return "Old Property"
    if "Under Construction" in text or "By" in text:
        return "Under Construction"
    try:
        int(text.split(" ")[-1])
        return "Under Construction"
    except (ValueError, IndexError):
        return "Undefined"


def convert_to_sqft(value: object) -> float:
    """Convert area strings into square feet where possible."""

    if pd.isna(value):
        return np.nan
    text = str(value).lower().replace(",", "")
    number_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
    if not number_match:
        return np.nan
    number = float(number_match.group(1))
    if "sq. yard" in text or "sq yard" in text or "sqyd" in text:
        return number * 9
    if "sq. meter" in text or "sq meter" in text or "sqm" in text:
        return number * 10.7639
    if "acre" in text:
        return number * 43_560
    return number


def extract_area(area_with_type: object, label: str) -> float:
    """Extract a specific area type from the `areaWithType` free text column."""

    if pd.isna(area_with_type):
        return np.nan
    text = str(area_with_type)
    pattern = rf"{re.escape(label)}[^0-9]*([0-9,.]+)\s*([A-Za-z.\s]*)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return np.nan
    return convert_to_sqft(" ".join(match.groups()))


def get_furnishing_count(value: object) -> int:
    """Count furnishing items from list-like strings."""

    if pd.isna(value):
        return 0
    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, list):
            return len(parsed)
    except (ValueError, SyntaxError):
        pass
    return len([part for part in str(value).split(",") if part.strip()])


def categorize_furnishing(count: int) -> str:
    """Map furnishing item counts to simple categories."""

    if count <= 0:
        return "unfurnished"
    if count <= 3:
        return "semifurnished"
    return "furnished"


def get_additional_room_flag(value: object, room_name: str) -> int:
    """Return 1 when a named additional room appears in the raw text."""

    if pd.isna(value):
        return 0
    return int(room_name.lower() in str(value).lower())


def luxury_score(features: object) -> int:
    """Compute a simple amenities score from feature text/list data."""

    if pd.isna(features):
        return 0
    text = str(features).lower()
    weights = {
        "pool": 30,
        "club": 25,
        "gym": 20,
        "security": 15,
        "park": 10,
        "lift": 10,
        "power": 10,
        "parking": 10,
        "garden": 10,
    }
    return sum(weight for token, weight in weights.items() if token in text)


def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create the engineered table used by downstream cleaning and modeling."""

    engineered = df.copy()
    engineered["agePossession"] = engineered["agePossession"].apply(categorize_age_possession)

    if "areaWithType" in engineered.columns:
        engineered["super_built_up_area"] = engineered["areaWithType"].apply(
            lambda value: extract_area(value, "Super Built up area")
        )
        engineered["built_up_area"] = engineered["areaWithType"].apply(
            lambda value: extract_area(value, "Built Up area")
        )
        engineered["carpet_area"] = engineered["areaWithType"].apply(
            lambda value: extract_area(value, "Carpet area")
        )

    if "additionalRoom" in engineered.columns:
        for room in ["study room", "servant room", "store room", "pooja room", "others"]:
            engineered[room] = engineered["additionalRoom"].apply(
                lambda value, room_name=room: get_additional_room_flag(value, room_name)
            )

    if "furnishDetails" in engineered.columns:
        counts = engineered["furnishDetails"].apply(get_furnishing_count)
        engineered["furnishing_type"] = counts.apply(categorize_furnishing)

    if "features" in engineered.columns:
        engineered["luxury_score"] = engineered["features"].apply(luxury_score)

    drop_cols = ["nearbyLocations", "furnishDetails", "features", "additionalRoom"]
    return engineered.drop(columns=drop_cols, errors="ignore")

