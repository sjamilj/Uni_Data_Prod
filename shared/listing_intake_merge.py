"""Merge scrape listing_intake_month tokens with intake dates parsed from course HTML."""

from __future__ import annotations

import re
from datetime import datetime

from study_level import UrlLevelMap, normalize_listing_intake_month, normalize_url

_MONTH_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{4})\b",
    re.I,
)

_CATALOG_MONTH_ORDER = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def listing_intake_months_for_url(
    url: str,
    url_levels: UrlLevelMap | None,
    *,
    study_level: str | None = None,
) -> list[str]:
    """Distinct listing_intake_month values from per-level URL CSVs for this course URL."""
    if not url_levels or not (url or "").strip():
        return []
    target = normalize_url(url.strip())
    months: set[str] = set()
    for record in url_levels.records():
        row_url = normalize_url(record.get("course_url", ""))
        if row_url != target:
            continue
        level = (record.get("study_level") or "").strip()
        if study_level and level != study_level:
            continue
        token = normalize_listing_intake_month(record.get("listing_intake_month", ""))
        if token:
            months.add(token)
    _academic_order = {"september": 0, "january": 1}
    return sorted(
        months,
        key=lambda m: (
            _academic_order.get(m, 50),
            _CATALOG_MONTH_ORDER.index(m) if m in _CATALOG_MONTH_ORDER else 99,
        ),
    )


def _parse_month_year_tokens(text: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for match in _MONTH_RE.finditer(text or ""):
        month = match.group(1).title()
        year = int(match.group(2))
        if (month, year) not in out:
            out.append((month, year))
    return out


def _infer_year_for_catalog_month(
    catalog_month: str,
    parsed: list[tuple[str, int]],
) -> int:
    years = sorted({year for _month, year in parsed})
    if years:
        base = years[-1]
    else:
        base = datetime.now().year
        if datetime.now().month >= 9:
            base += 1

    cat = catalog_month.lower()
    if cat == "september":
        for month, year in parsed:
            if month.lower() == "september":
                return year
        return base if base >= datetime.now().year else base

    if cat == "january":
        for month, year in parsed:
            if month.lower() == "january":
                return year
        sep_years = [year for month, year in parsed if month.lower() == "september"]
        if sep_years:
            # Same calendar year as September (e.g. Sep 2027 + Jan 2027 from catalogue).
            return max(sep_years)
        return base

    return base


def merge_catalog_months_with_page_intakes(
    page_intake_text: str,
    catalog_months: list[str],
) -> str:
    """Union of HTML apply-table dates and catalogue search months (with inferred years)."""
    parsed = _parse_month_year_tokens(page_intake_text)
    present_months = {month.lower() for month, _year in parsed}

    normalized_catalog = [
        normalize_listing_intake_month(c) for c in catalog_months if normalize_listing_intake_month(c)
    ]
    dual_sep_jan = "september" in normalized_catalog and "january" in normalized_catalog

    for catalog in catalog_months:
        token = normalize_listing_intake_month(catalog)
        if not token or token in present_months:
            continue
        year = _infer_year_for_catalog_month(token, parsed)
        title = token.title()
        parsed.append((title, year))
        present_months.add(token)

    if dual_sep_jan:
        sep_years = [year for month, year in parsed if month.lower() == "september"]
        if sep_years:
            target_jan_year = max(sep_years)
            parsed = [
                (month, target_jan_year if month.lower() == "january" else year)
                for month, year in parsed
            ]

    if not parsed:
        return page_intake_text.strip()

    _display_order = {"september": 0, "january": 1}

    def _sort_key(item: tuple[str, int]) -> tuple[int, int, int]:
        month, year = item
        m = month.lower()
        return (
            year,
            _display_order.get(m, 50),
            _CATALOG_MONTH_ORDER.index(m) if m in _CATALOG_MONTH_ORDER else 99,
        )

    parsed.sort(key=_sort_key)
    return ", ".join(f"{month} {year}" for month, year in parsed)
