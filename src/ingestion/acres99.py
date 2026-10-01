"""Polite 99acres adapter. It uses public URLs only and does not bypass controls."""

from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base import FetchResult
from .normalizer import normalize_city
from .search_parser import parse_detail_page, parse_search_page


class Acres99Adapter:
    source_name = "99acres"

    def __init__(
        self, *, delay_seconds: float = 2.0, timeout_seconds: float = 15.0, retries: int = 1
    ):
        self.delay_seconds = max(0.0, delay_seconds)
        self.timeout_seconds = timeout_seconds
        self.retries = max(0, retries)

    def fetch(self, url: str, city: str) -> FetchResult:
        """Fetch one public response without interpreting a search page as a listing."""
        return self._request(url)

    def fetch_search(self, *, city: str, page: int, url: str | None = None) -> FetchResult:
        url = url or self.search_url(city, page)
        result = self._request(url)
        if result.http_status == 200 and result.body:
            parsed = parse_search_page(result.body, page_url=url, city=city)
            result.listings = parsed.listings
            result.candidate_count = parsed.candidate_cards
            result.valid_listing_count = len(parsed.listings)
            result.content_hash = parsed.content_hash
            result.parser_errors = parsed.parser_errors
        return result

    def fetch_detail(self, url: str, city: str) -> FetchResult:
        result = self._request(url)
        if result.http_status == 200 and result.body:
            result.listing = parse_detail_page(result.body, detail_url=url, city=city)
            result.listings = [result.listing] if result.listing else []
            result.valid_listing_count = len(result.listings)
        return result

    def _request(self, url: str) -> FetchResult:
        time.sleep(self.delay_seconds)
        request = Request(
            url,
            headers={
                "User-Agent": "EstateIQ-responsible-research/1.0 (+local development)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        last_reason = "no response"
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    body = response.read().decode("utf-8", errors="replace")
                    status = int(response.status)
                    return FetchResult(url, status, response.geturl(), body)
            except HTTPError as error:
                last_reason = f"HTTP {error.code}"
                if error.code in (401, 403, 429):
                    return FetchResult(
                        url,
                        error.code,
                        error.url,
                        blocked=True,
                        reason=f"Public fetch blocked with HTTP {error.code}",
                    )
                if attempt >= self.retries:
                    return FetchResult(url, error.code, error.url, reason=last_reason)
            except (URLError, TimeoutError) as error:
                last_reason = str(error)
                if attempt >= self.retries:
                    return FetchResult(url, None, None, reason=last_reason)
            time.sleep(min(10.0, 2.0 ** (attempt + 1)))
        return FetchResult(url, None, None, reason=last_reason)

    @staticmethod
    def search_url(city: str, page: int = 1) -> str:
        """Return a public search URL; no hidden API or anti-bot endpoint."""
        city_slug = "gurgaon" if normalize_city(city) == "gurgaon" else normalize_city(city)
        return f"https://www.99acres.com/property-in-{city_slug}-ffid?preference=S&page={page}"
