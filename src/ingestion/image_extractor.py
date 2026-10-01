"""Extract an image only when it is present on the exact listing response."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any

from .base import ImageEvidence


def extract_exact_image(html: str, *, listing_url: str) -> ImageEvidence | None:
    """Read JSON-LD/OpenGraph/known embedded image fields from one page only."""

    images = extract_exact_images(html, listing_url=listing_url)
    return images[0] if images else None


def extract_exact_images(html: str, *, listing_url: str) -> list[ImageEvidence]:
    """Return all exact-page image candidates, preserving source evidence."""

    candidates: list[tuple[str, str]] = []
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        property_match = re.search(r"(?:property|name)=[\"']([^\"']+)[\"']", tag, re.I)
        content_match = re.search(r"content=[\"']([^\"']+)[\"']", tag, re.I)
        if (
            property_match
            and content_match
            and property_match.group(1).lower() in {"og:image", "twitter:image"}
        ):
            candidates.append((unescape(content_match.group(1)), property_match.group(1).lower()))
    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.I | re.S
    ):
        try:
            payload: Any = json.loads(unescape(block).strip())
        except json.JSONDecodeError:
            continue
        for image in _json_images(payload):
            candidates.append((image, "json-ld:image"))
    for match in re.finditer(
        r'(?i)["\'](?:image|imageUrl|thumbnailUrl)["\']\s*:\s*["\'](https?://[^"\']+)', html
    ):
        candidates.append((unescape(match.group(1)), "embedded:image"))
    output: list[ImageEvidence] = []
    seen: set[str] = set()
    for url, source in candidates:
        if _is_http_image(url) and url != listing_url:
            if url not in seen:
                output.append(
                    ImageEvidence(
                        url=url,
                        source=source,
                        verified_at=datetime.now(timezone.utc).isoformat(),
                        match_confidence=1.0,
                    )
                )
                seen.add(url)
    return output


def _json_images(value: Any) -> list[str]:
    if isinstance(value, dict):
        images = value.get("image") or value.get("images")
        if isinstance(images, str):
            return [images]
        if isinstance(images, list):
            return [
                item if isinstance(item, str) else item.get("url", "")
                for item in images
                if isinstance(item, (str, dict))
            ]
        output: list[str] = []
        for nested in value.values():
            output.extend(_json_images(nested))
        return output
    if isinstance(value, list):
        output: list[str] = []
        for nested in value:
            output.extend(_json_images(nested))
        return output
    return []


def _is_http_image(url: str) -> bool:
    return bool(re.match(r"^https?://", url)) and len(url) < 2048
