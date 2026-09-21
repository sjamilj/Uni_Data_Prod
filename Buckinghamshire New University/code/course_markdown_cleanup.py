"""University-specific course markdown cleanup for Buckinghamshire New University.

Keeps only:
  - Key course facts (UCAS code, tariff, study mode, location, duration, start date)
  - ### What are the course entry requirements?
  - #### What are the tuition fees → ###### International only

Configure additional heading removal in code/.env (COURSE_MARKDOWN_REMOVE_SECTIONS).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlparse

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from bs4 import BeautifulSoup

from course_markdown_cleanup import _normalize_blank_lines, main

_ENTRY_HEADING = re.compile(r"^what are the course entry requirements\??$", re.I)
_FEES_HEADING_RE = re.compile(r"^what are the tuition fees\??$", re.I)
_INTERNATIONAL_HEADING = "international"
_HOME_HEADING = "home"

_SLUG_WORDS = {
    "ma": "MA",
    "msc": "MSc",
    "mba": "MBA",
    "llm": "LLM",
    "bsc": "BSc",
    "ba": "BA",
    "beng": "BEng",
    "phd": "PhD",
    "pgdip": "PGDip",
    "pgcert": "PGCert",
    "3d": "3D",
    "2d": "2D",
    "hons": "Hons",
}

_UCAS_RE = re.compile(
    r"\*\*UCAS CODE:\*\*\s*(.+?)(?=\*\*TARIFF:\*\*|\*\*Study Mode:\*\*|Jump to:|$)",
    re.I,
)
_TARIFF_RE = re.compile(
    r"\*\*TARIFF:\*\*\s*(.+?)(?=Jump to:|\*\*Study Mode:\*\*|$)",
    re.I,
)
_STUDY_FIELD_RES = {
    "Study Mode": re.compile(r"\*\*Study Mode:\*\*\s*(.+)"),
    "Location": re.compile(r"\*\*Location:\*\*\s*(.+)"),
    "Duration": re.compile(r"\*\*Duration:\*\*\s*(.+)"),
    "Start Date": re.compile(r"\*\*Start Date:\*\*\s*(.+)"),
}

_FEE_FOOTNOTE_STARTS = (
    "please note",
    "following the government",
    "tuition fees for",
    "tuition fees are expected",
    "distance learning and international fees",
    "we understand",
    "the following factors",
    "additional course costs",
    "additional costs",
    "contact us",
    "what are my career",
)

_OVERSEAS_FEE_RE = re.compile(
    r"Overseas/International[^£\n]*£([\d,]+)",
    re.I,
)


def _heading_level_and_text(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _course_slug_from_markdown(markdown: str) -> str | None:
    url = None
    fm_match = re.search(r"^course_url:\s*(\S+)\s*$", markdown, re.M)
    if fm_match:
        url = fm_match.group(1).strip()
    else:
        pipe_match = re.search(
            r"<!--\s*pipeline:.*\bcourse_url=(\S+)",
            markdown,
            re.I,
        )
        if pipe_match:
            url = pipe_match.group(1).strip()
        else:
            src_match = re.search(r"^source_url:\s*(\S+)\s*$", markdown, re.M)
            if src_match:
                url = src_match.group(1).strip()
    if not url:
        return None
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[-1]


def _humanize_course_slug(slug: str) -> str:
    parts = [part for part in slug.split("-") if part]
    words: list[str] = []
    for part in parts:
        key = part.lower()
        if key in _SLUG_WORDS:
            words.append(_SLUG_WORDS[key])
        elif part.isdigit():
            words.append(part)
        else:
            words.append(part.capitalize())
    return " ".join(words)


def _is_spaced_letter_title(title: str) -> bool:
    text = title.lstrip("#").strip()
    tokens = text.split()
    if len(tokens) < 4:
        return False
    single = sum(1 for token in tokens if len(token) == 1)
    return single / len(tokens) >= 0.55


def _fix_spaced_title(markdown: str) -> str:
    slug = _course_slug_from_markdown(markdown)
    if not slug:
        return markdown
    human = _humanize_course_slug(slug)
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("# ") and not line.startswith("## "):
            if _is_spaced_letter_title(line):
                lines[index] = f"# {human}"
            break
    return "\n".join(lines)


def _flatten_broken_fee_markdown(markdown: str) -> str:
    """Join fee amounts split across lines inside bold markers."""
    text = markdown
    text = re.sub(
        r"\*\*£([\d,]+)\s*\n\s*per year\s*\n\s*\*+\s*",
        r"**£\1** per year",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"\*\*£([\d,]+)\s*\n\s*per year",
        r"**£\1** per year",
        text,
        flags=re.I,
    )
    text = re.sub(r"\n\s*\*{3,}\s*", "\n", text)
    return text


def preprocess_course_html_uni(soup: BeautifulSoup) -> None:
    """Remove BNU fee footnotes (parliamentary / additional costs) before HTML→markdown."""
    for selector in (
        "section#fees .bnu-full-width-text-fees",
        ".bnu-full-width-text-fees",
    ):
        for node in soup.select(selector):
            node.decompose()


def preprocess_course_markdown_uni(markdown: str) -> str:
    """Run before .env section removal (title + fee line breaks)."""
    cleaned = _flatten_broken_fee_markdown(markdown)
    return _fix_spaced_title(cleaned)


def _fees_funding_slice(markdown: str) -> str:
    match = re.search(
        r"^##\s+Fees and funding\s*$(.*?)(?=^##\s+|\Z)",
        markdown,
        re.S | re.M | re.I,
    )
    return match.group(1) if match else markdown


def _format_international_fees_block(amount: str, *, label: str | None = None) -> str:
    line_label = label or "Overseas/International"
    return (
        "#### What are the tuition fees\n"
        "###### International\n\n"
        f"- {line_label}: **£{amount}** per year\n"
        f"Annual tuition fees: | £{amount}"
    )


def _extract_title(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if re.match(r"^# [^#]", line):
            return line.strip()
    return None


def _clean_inline_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s*Jump to:.*$", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def _extract_key_info(markdown: str) -> str | None:
    ucas = tariff = None
    for match in _UCAS_RE.finditer(markdown):
        ucas = _clean_inline_value(match.group(1))
    for match in _TARIFF_RE.finditer(markdown):
        tariff = _clean_inline_value(match.group(1))

    study_fields: list[str] = []
    seen_labels: set[str] = set()
    for line in markdown.splitlines():
        for label, pattern in _STUDY_FIELD_RES.items():
            if label in seen_labels:
                continue
            field_match = pattern.search(line)
            if field_match:
                value = _clean_inline_value(field_match.group(1))
                study_fields.append(f"- **{label}:** {value}")
                seen_labels.add(label)

    if not any([ucas, tariff, study_fields]):
        return None

    lines: list[str] = []
    if ucas:
        lines.append(f"**UCAS CODE:** {ucas}")
    if tariff:
        lines.append(f"**TARIFF:** {tariff}")
    lines.extend(study_fields)
    return "\n".join(lines)


def _is_entry_stop(line: str) -> bool:
    parsed = _heading_level_and_text(line)
    if parsed:
        level, text = parsed
        text_l = text.lower()
        if level <= 2:
            return True
        if level in {3, 4, 5}:
            if _ENTRY_HEADING.match(text):
                return False
            if _FEES_HEADING_RE.match(text):
                return True
            return True
    stripped = line.strip()
    if stripped.lower() in {"modules", "modal structure"}:
        return True
    if stripped.startswith("Modal Structure"):
        return True
    return False


def _extract_entry_requirements(markdown: str) -> str | None:
    lines = markdown.splitlines()
    start = None
    for index, line in enumerate(lines):
        parsed = _heading_level_and_text(line)
        if parsed and parsed[0] in {3, 4, 5} and _ENTRY_HEADING.match(parsed[1]):
            start = index
            break
    if start is None:
        return None

    kept = ["### What are the course entry requirements?"]
    for line in lines[start + 1 :]:
        if _is_entry_stop(line):
            break
        kept.append(line)

    body = "\n".join(kept).strip()
    return body or None


def _is_fee_footnote(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("- "):
        return False
    parsed = _heading_level_and_text(line)
    if parsed:
        return False
    lowered = stripped.lower()
    return any(lowered.startswith(prefix) for prefix in _FEE_FOOTNOTE_STARTS)


def _extract_international_fees(markdown: str) -> str | None:
    search_text = _fees_funding_slice(markdown)
    amount_match = _OVERSEAS_FEE_RE.search(search_text)
    if not amount_match and search_text == markdown:
        amount_match = _OVERSEAS_FEE_RE.search(markdown)

    lines = search_text.splitlines()
    fees_start = None
    for index, line in enumerate(lines):
        parsed = _heading_level_and_text(line)
        if parsed and parsed[0] in {3, 4, 5} and _FEES_HEADING_RE.match(parsed[1]):
            fees_start = index
            break

    if fees_start is None:
        if not amount_match:
            return None
        return _format_international_fees_block(amount_match.group(1))

    output = ["#### What are the tuition fees"]
    index = fees_start + 1
    while index < len(lines):
        parsed = _heading_level_and_text(lines[index])
        if parsed:
            level, text = parsed
            text_l = text.lower()
            if level in {5, 6} and text_l == _HOME_HEADING:
                index += 1
                while index < len(lines):
                    nested = _heading_level_and_text(lines[index])
                    if nested and nested[0] <= 6:
                        break
                    index += 1
                continue
            if level in {5, 6} and text_l == _INTERNATIONAL_HEADING:
                output.append("###### International")
                index += 1
                while index < len(lines):
                    if _is_fee_footnote(lines[index]):
                        break
                    nested = _heading_level_and_text(lines[index])
                    if nested and nested[0] <= 6 and nested[1].lower() != _INTERNATIONAL_HEADING:
                        break
                    output.append(lines[index])
                    index += 1
                break
            if level <= 4 and not _FEES_HEADING_RE.match(text):
                break
        index += 1

    body = "\n".join(output).strip()
    has_intl_heading = "###### international" in body.lower()
    if not has_intl_heading and amount_match:
        body = _format_international_fees_block(amount_match.group(1))
    elif not has_intl_heading:
        return None

    body = _flatten_broken_fee_markdown(body)
    cleaned_lines: list[str] = []
    for line in body.splitlines():
        if _is_fee_footnote(line):
            break
        trimmed = re.sub(r"(per year)\s*Please note.*$", r"\1", line, flags=re.I)
        cleaned_lines.append(trimmed)
    body = "\n".join(cleaned_lines).strip()
    amount_match = _OVERSEAS_FEE_RE.search(body)
    if amount_match:
        amount = amount_match.group(1)
        if "Annual tuition fees:" not in body:
            body = f"{body}\nAnnual tuition fees: | £{amount}"
    return body


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Keep only key facts, entry requirements, and international fees."""
    working = preprocess_course_markdown_uni(markdown)
    title = _extract_title(working)
    key_info = _extract_key_info(working)
    entry = _extract_entry_requirements(working)
    fees = _extract_international_fees(working)

    if not any([title, key_info, entry, fees]):
        return markdown

    parts: list[str] = []
    if title:
        parts.extend([title, ""])
    if key_info:
        parts.extend([key_info, ""])
    if entry:
        parts.extend([entry, ""])
    if fees:
        parts.append(fees)

    if not parts:
        return markdown
    return _normalize_blank_lines("\n".join(parts))


if __name__ == "__main__":
    raise SystemExit(main())
