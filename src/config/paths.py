"""Centralized filesystem paths for the project."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODEL_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
METRICS_DIR = REPORTS_DIR / "metrics"
FIGURES_DIR = REPORTS_DIR / "figures"
CONFIG_DIR = PROJECT_ROOT / "configs"

DEFAULT_TRAINING_DATA = PROCESSED_DATA_DIR / "gurgaon_properties_post_feature_selection_v2.csv"
DEFAULT_MODEL_PATH = MODEL_DIR / "price_model.joblib"
DEFAULT_MODEL_METADATA_PATH = MODEL_DIR / "model_metadata.json"
DEFAULT_METRICS_PATH = METRICS_DIR / "model_metrics.json"
DEFAULT_FEATURE_IMPORTANCE_PATH = METRICS_DIR / "feature_importance.csv"
DEFAULT_RECOMMENDER_DATA = RAW_DATA_DIR / "appartments.csv"


def ensure_project_dirs() -> None:
    """Create output directories required by training and reporting jobs."""

    for path in [MODEL_DIR, METRICS_DIR, FIGURES_DIR]:
        path.mkdir(parents=True, exist_ok=True)

