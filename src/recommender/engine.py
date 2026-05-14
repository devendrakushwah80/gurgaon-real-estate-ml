"""Apartment recommendation engine based on project text similarity."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config.paths import DEFAULT_RECOMMENDER_DATA


def extract_list(value: object) -> list[str]:
    """Parse list-like notebook fields into a list of strings."""

    if pd.isna(value):
        return []
    text = str(value)
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        if isinstance(parsed, dict):
            return [str(item) for item in parsed.values()]
    except (ValueError, SyntaxError):
        pass
    return [part.strip() for part in re.split(r"[,|]", text) if part.strip()]


def build_search_text(row: pd.Series) -> str:
    """Build the recommender corpus text for one apartment/project row."""

    parts: list[str] = []
    for column in ["PropertyName", "PropertySubName", "NearbyLocations", "LocationAdvantages", "TopFacilities"]:
        if column in row and pd.notna(row[column]):
            value = row[column]
            if column in {"NearbyLocations", "LocationAdvantages", "TopFacilities"}:
                parts.extend(extract_list(value))
            else:
                parts.append(str(value))
    return " ".join(parts).lower()


class PropertyRecommender:
    """TF-IDF/cosine-similarity recommender for apartment projects."""

    def __init__(self, data_path: str | Path = DEFAULT_RECOMMENDER_DATA) -> None:
        self.data_path = Path(data_path)
        self.data: pd.DataFrame | None = None
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix: Any | None = None

    def fit(self) -> PropertyRecommender:
        """Load data and fit the vectorization matrix."""

        if not self.data_path.exists():
            raise FileNotFoundError(f"Recommender data not found: {self.data_path}")
        data = pd.read_csv(self.data_path).drop_duplicates()
        data["search_text"] = data.apply(build_search_text, axis=1)
        self.matrix = self.vectorizer.fit_transform(data["search_text"])
        self.data = data.reset_index(drop=True)
        return self

    def _ensure_fit(self) -> None:
        if self.data is None or self.matrix is None:
            self.fit()

    def recommend(self, query: str, top_n: int = 5) -> list[dict[str, Any]]:
        """Return top matching properties for a free-text query."""

        self._ensure_fit()
        assert self.data is not None and self.matrix is not None
        query_vector = self.vectorizer.transform([query.lower()])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        top_indices = scores.argsort()[::-1][:top_n]
        return [self._format_result(index, float(scores[index])) for index in top_indices]

    def similar_properties(self, property_name: str, top_n: int = 5) -> list[dict[str, Any]]:
        """Return properties most similar to a named project."""

        self._ensure_fit()
        assert self.data is not None and self.matrix is not None
        matches = self.data[
            self.data["PropertyName"].str.contains(property_name, case=False, na=False)
        ]
        if matches.empty:
            return self.recommend(property_name, top_n=top_n)
        index = int(matches.index[0])
        scores = cosine_similarity(self.matrix[index], self.matrix).ravel()
        top_indices = [idx for idx in scores.argsort()[::-1] if idx != index][:top_n]
        return [self._format_result(idx, float(scores[idx])) for idx in top_indices]

    def _format_result(self, index: int, score: float) -> dict[str, Any]:
        assert self.data is not None
        row = self.data.iloc[index]
        return {
            "property_name": row.get("PropertyName"),
            "property_sub_name": row.get("PropertySubName"),
            "link": row.get("Link"),
            "score": round(score, 4),
        }

