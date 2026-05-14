import pandas as pd
import pytest

from src.features.selection import MODEL_FEATURES
from src.pipelines.inference import PriceInferencePipeline


def test_inference_validation_requires_all_features():
    with pytest.raises(ValueError):
        PriceInferencePipeline.validate_frame(pd.DataFrame([{"sector": "sector 48"}]))


def test_inference_validation_orders_features():
    row = {
        "property_type": "flat",
        "sector": "sector 48",
        "bedRoom": 3,
        "bathroom": 3,
        "balcony": "2",
        "agePossession": "Relatively New",
        "built_up_area": 1500,
        "servant room": 1,
        "store room": 0,
        "furnishing_type": "semifurnished",
        "luxury_category": "Medium",
        "floor_category": "Mid Floor",
    }
    validated = PriceInferencePipeline.validate_frame(pd.DataFrame([row]))
    assert list(validated.columns) == MODEL_FEATURES

