"""Runtime settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Application settings with conservative local defaults."""

    app_name: str = os.getenv("APP_NAME", "Gurgaon Real Estate ML")
    environment: str = os.getenv("ENVIRONMENT", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    model_path: str = os.getenv("MODEL_PATH", "models/price_model.joblib")
    recommender_data_path: str = os.getenv(
        "RECOMMENDER_DATA_PATH", "data/raw/appartments.csv"
    )


settings = Settings()

