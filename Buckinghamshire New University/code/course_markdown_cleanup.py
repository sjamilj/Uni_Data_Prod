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

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import _normalize_blank_lines, main

_ENTRY_HEADING = "what are the course entry requirements?"
_FEES_HEADING = "what are the tuition fees"
_INTERNATIONAL_HEADING = "international"
_HOME_HEADING = "home"

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
    "we understand",
    "the following factors",
    "additional costs",
    "contact us",
    "what are my career",
)


def _heading_level_and_text(line: str) -> tuple[int, str] | None:
    match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


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
    for line in markdown.splitlines():
        for label, pattern in _STUDY_FIELD_RES.items():
            field_match = pattern.search(line)
            if field_match:
                value = _clean_inline_value(field_match.group(1))
                study_fields.append(f"- **{label}:** {value}")

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
        if level == 3 and text_l != _ENTRY_HEADING:
            return True
        if level == 4 and text_l == _FEES_HEADING:
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
        if parsed and parsed[0] == 3 and parsed[1].lower() == _ENTRY_HEADING:
            start = index
            break
    if start is None:
        return None

    kept = [lines[start]]
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
    lines = markdown.splitlines()
    fees_start = None
    for index, line in enumerate(lines):
        parsed = _heading_level_and_text(line)
        if parsed and parsed[0] == 4 and parsed[1].lower() == _FEES_HEADING:
            fees_start = index
            break
    if fees_start is None:
        return None

    output = [lines[fees_start]]
    index = fees_start + 1
    while index < len(lines):
        parsed = _heading_level_and_text(lines[index])
        if parsed:
            level, text = parsed
            text_l = text.lower()
            if level == 6 and text_l == _HOME_HEADING:
                index += 1
                while index < len(lines):
                    nested = _heading_level_and_text(lines[index])
                    if nested and nested[0] <= 6:
                        break
                    index += 1
                continue
            if level == 6 and text_l == _INTERNATIONAL_HEADING:
                output.append(lines[index])
                index += 1
                while index < len(lines):
                    if _is_fee_footnote(lines[index]):
                        break
                    nested = _heading_level_and_text(lines[index])
                    if nested and nested[0] <= 6:
                        break
                    output.append(lines[index])
                    index += 1
                break
            if level <= 4:
                break
        index += 1

    body = "\n".join(output).strip()
    if "###### International" not in body and "###### international" not in body.lower():
        return None
    return body


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Keep only key facts, Bangladesh-relevant entry requirements, and international fees."""
    title = _extract_title(markdown)
    key_info = _extract_key_info(markdown)
    entry = _extract_entry_requirements(markdown)
    fees = _extract_international_fees(markdown)

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
