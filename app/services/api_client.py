"""HTTP client for the FastAPI backend."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT_SECONDS = 8.0


class ApiClientError(RuntimeError):
    """Raised when the API client cannot complete a request."""


@dataclass(frozen=True)
class ApiHealth:
    """API health response plus measured latency."""

    ok: bool
    status: str
    response_time_ms: float
    detail: str | None = None


class ApiClient:
    """Small typed wrapper around backend HTTP endpoints."""

    def __init__(self, base_url: str = DEFAULT_API_BASE_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> ApiHealth:
        """Check API health and measure response time."""

        start = time.perf_counter()
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            elapsed = (time.perf_counter() - start) * 1000
            response.raise_for_status()
            body = response.json()
            return ApiHealth(
                ok=body.get("status") == "ok",
                status=str(body.get("status", "unknown")),
                response_time_ms=elapsed,
            )
        except requests.RequestException as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ApiHealth(False, "unavailable", elapsed, str(exc))

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON POST request and return the decoded response."""

        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            detail = _extract_error(response)
            raise ApiClientError(detail) from exc
        except requests.RequestException as exc:
            raise ApiClientError(f"Backend request failed: {exc}") from exc


def _extract_error(response: requests.Response) -> str:
    try:
        body = response.json()
        return str(body.get("detail") or body)
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

