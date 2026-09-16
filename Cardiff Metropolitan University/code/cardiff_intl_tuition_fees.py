"""Resolve international tuition fee lines from output/clean/uni/international-tuition-fees.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from uni_pages import split_frontmatter

_FEE_MD = (
    Path(__file__).resolve().parents[1] / "output" / "clean" / "uni" / "international-tuition-fees.md"
)


def _load_bands() -> list[dict[str, Any]]:
    if not _FEE_MD.is_file():
        return []
    text = _FEE_MD.read_text(encoding="utf-8")
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return []
    payload = json.loads(match.group(1))
    bands = payload.get("bands")
    return bands if isinstance(bands, list) else []


def _band_matches(
    band: dict[str, Any],
    *,
    course_url: str,
    study_level: str,
) -> bool:
    url_cf = course_url.casefold()
    patterns = band.get("urlPatterns") or []
    levels = [str(x).casefold() for x in (band.get("studyLevels") or [])]
    if patterns:
        if not any(p.casefold() in url_cf for p in patterns):
            return False
    if levels:
        if not study_level or study_level not in levels:
            return False
    return bool(patterns or levels)


def _pipeline_context(markdown: str) -> tuple[str, str]:
    match = re.search(
        r"<!--\s*pipeline:\s*course_url=([^\s>]+)(?:\s+study_level=([^\s>]+))?\s*-->",
        markdown,
        re.I,
    )
    if match:
        return match.group(1).strip(), (match.group(2) or "").strip().casefold()
    meta, _body = split_frontmatter(markdown)
    course_url = str(meta.get("course_url") or meta.get("source_url") or "").strip()
    study_level = str(meta.get("study_level") or "").strip().casefold()
    return course_url, study_level


def strip_pipeline_comment(markdown: str) -> str:
    return re.sub(r"<!--\s*pipeline:.*?-->\n?", "", markdown, count=1, flags=re.I)


def resolve_international_fee_line(markdown: str) -> str:
    """Return a Stage-1-friendly fee line, or '' if already present / unmapped."""
    if re.search(r"(?:Annual tuition fees|First year tuition fee):\s*\|", markdown, re.I):
        return ""
    course_url, study_level = _pipeline_context(markdown)

    chosen: dict[str, Any] | None = None
    for band in _load_bands():
        if _band_matches(band, course_url=course_url, study_level=study_level):
            chosen = band
            break

    if not chosen:
        return ""

    fee_line = str(chosen.get("feeLine") or "").strip()
    if fee_line:
        return fee_line
    fee = str(chosen.get("tuitionFee") or "").strip()
    if not fee:
        return ""
    try:
        display = f"£{int(fee.replace(',', '')):,}"
    except ValueError:
        display = f"£{fee}"
    return f"Annual tuition fees: | {display} per year"
