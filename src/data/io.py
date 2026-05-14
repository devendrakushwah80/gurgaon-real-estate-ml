"""Data IO helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import pandas as pd


def read_csv(path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Read a CSV file with a helpful error when it is missing."""

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    return pd.read_csv(csv_path, **kwargs)


def write_csv(df: pd.DataFrame, path: str | Path, **kwargs: Any) -> None:
    """Write a DataFrame to CSV, creating parent directories first."""

    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False, **kwargs)


def save_artifact(obj: Any, path: str | Path) -> None:
    """Persist a Python artifact with joblib."""

    artifact_path = Path(path)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, artifact_path)


def load_artifact(path: str | Path) -> Any:
    """Load a Python artifact persisted with joblib."""

    artifact_path = Path(path)
    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")
    return joblib.load(artifact_path)

