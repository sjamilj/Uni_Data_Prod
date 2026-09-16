"""University of Derby — reshape key facts + entry for Stage 1 parser."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from bs4 import BeautifulSoup

from course_markdown_cleanup import _normalize_blank_lines, main

_KEY_SECTION = "## Key course details"


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """When both intake tabs exist, keep only #entry-year2 (latest entry year)."""
    if soup.select_one("#entry-year2"):
        for node in soup.select("#entry-year1"):
            node.decompose()


_ENTRY_SECTION = "## Entry requirements"

_ENTRY_YEAR_RE = re.compile(
    r"(?:September|January|February|March|April|May|June|July|August|October|November|December)\s+(\d{4})\s+entry",
    re.I,
)
_IELTS_CELL_RE = re.compile(
    r"IELTS:\s*([\d.]+)\s*\([^)]*?([\d.]+)[^)]*\)",
    re.I,
)
_IELTS_INLINE_RE = re.compile(
    r"IELTS[:\s]+([\d.]+)\s*\([^)]*?([\d.]+)[^)]*\)",
    re.I,
)
_IELTS_COMPONENT_RE = re.compile(
    r"IELTS\s+([\d.]+)\s+with\s+no\s+individual\s+component\s+below\s+([\d.]+)",
    re.I,
)
_FEE_AMOUNT_PATTERNS = (
    re.compile(r"£([\d,]+)\s*per year", re.I),
    re.compile(r"£([\d,]+)\s*for the full course", re.I),
)
_IELTS_OR_EQUIV_RE = re.compile(r"IELTS\s+([\d.]+)\s+or\s+equivalent", re.I)


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            return line.strip()
    return None


def _section_body(markdown: str, heading: str) -> str | None:
    marker = heading
    if marker not in markdown:
        return None
    _, tail = markdown.split(marker, 1)
    next_section = re.search(r"\n## ", tail)
    body = tail[: next_section.start()] if next_section else tail
    return body.strip()


def _next_nonempty_line(lines: list[str], start: int) -> int:
    j = start
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j


def _parse_key_details_labels(body: str) -> dict[str, str]:
    lines = [ln.strip() for ln in body.splitlines()]
    labels: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith("[") or line.startswith("!"):
            i += 1
            continue
        if line.startswith("If you do not achieve"):
            break
        value_index = _next_nonempty_line(lines, i + 1)
        if value_index < len(lines) and not lines[value_index].startswith("|"):
            labels[line.lower()] = lines[value_index]
            i = value_index + 1
            continue
        i += 1
    return labels


def _label_value(labels: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = labels.get(key.lower())
        if value:
            return value
    return ""


def _international_fee_amount(intl_fee: str) -> str | None:
    for pattern in _FEE_AMOUNT_PATTERNS:
        match = pattern.search(intl_fee)
        if match:
            return match.group(1).replace(",", "")
    return None


def _primary_full_time_duration(study_options: str) -> str:
    text = study_options.strip()
    match = re.search(
        r"Full-time:\s*([^,]+?)(?:\s*,\s*Part-time:|$)",
        text,
        re.I,
    )
    if match:
        return match.group(1).strip()
    return text.split(",")[0].strip() if text else ""


def _intake_year(entry_body: str, start_label: str) -> str:
    year_match = _ENTRY_YEAR_RE.search(entry_body or "")
    year = year_match.group(1) if year_match else ""
    month = re.sub(r"[^\w\s,]", "", start_label).strip() or "September"
    if not year:
        return month
    if re.search(r"\b\d{4}\b", month):
        return month
    return f"{month} {year}"


def _format_stage1_key_block(
    labels: dict[str, str],
    entry_body: str,
) -> list[str]:
    study = labels.get("study options", "")
    duration = _primary_full_time_duration(study)
    start = _intake_year(
        entry_body,
        _label_value(labels, "start dates", "start date") or "September",
    )
    fee_amount = _international_fee_amount(labels.get("international fee", ""))

    lines: list[str] = ["## Key course information", ""]
    if duration:
        lines.append(f"**Duration:** {duration}")
    lines.append(f"- **Start date:** {start}")
    if fee_amount:
        amount = fee_amount
        lines.extend(
            [
                "",
                "### International students",
                "",
                f"Annual tuition fees: | £{amount}",
            ]
        )
    return lines


def _normalize_ielts_line(entry_body: str) -> str | None:
    for pattern in (_IELTS_CELL_RE, _IELTS_INLINE_RE, _IELTS_COMPONENT_RE):
        match = pattern.search(entry_body)
        if match:
            overall, section = match.group(1), match.group(2)
            return (
                f"IELTS {overall} overall with no less than {section} in each band"
            )
    equiv = _IELTS_OR_EQUIV_RE.search(entry_body)
    if equiv:
        overall = equiv.group(1)
        section = "5.5" if float(overall) <= 6.5 else "6.5"
        return (
            f"IELTS {overall} overall with no less than {section} in each band"
        )
    return None


def cleanup_course_markdown_uni(markdown: str) -> str:
    title = _extract_title(markdown)
    key_body = _section_body(markdown, _KEY_SECTION)
    entry_body = _section_body(markdown, _ENTRY_SECTION)

    if not key_body and not entry_body:
        return markdown

    labels = _parse_key_details_labels(key_body or "")
    parts: list[str] = []
    if title:
        parts.extend([title, ""])

    if labels or entry_body:
        parts.extend(_format_stage1_key_block(labels, entry_body or ""))
        parts.append("")

    if entry_body:
        ielts = _normalize_ielts_line(entry_body)
        parts.extend([_ENTRY_SECTION, ""])
        if ielts:
            parts.append(ielts)
            parts.append("")
        parts.append(entry_body.strip())

    return _normalize_blank_lines("\n".join(parts))


if __name__ == "__main__":
    raise SystemExit(main())
