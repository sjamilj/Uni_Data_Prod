"""University-specific course markdown cleanup (optional)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

_shared_cleanup_spec = importlib.util.spec_from_file_location(
    "shared_course_markdown_cleanup",
    _SHARED / "course_markdown_cleanup.py",
)
assert _shared_cleanup_spec and _shared_cleanup_spec.loader
_shared_cleanup = importlib.util.module_from_spec(_shared_cleanup_spec)
_shared_cleanup_spec.loader.exec_module(_shared_cleanup)
main = _shared_cleanup.main
remove_markdown_heading_section = _shared_cleanup.remove_markdown_heading_section

_UG_YEAR_VARIANT_SELECTORS = (
    ".ug-2026-only",
    ".ug-2027-only",
    ".ug-fees-27-only",
)


def preprocess_course_html_uni(soup) -> None:
    """Unwrap year-variant spans so international fee lines convert to markdown."""
    for selector in _UG_YEAR_VARIANT_SELECTORS:
        for span in soup.select(selector):
            span.unwrap()
    fees = soup.select_one(".fees-details")
    if fees is None:
        return
    for li in fees.select("li.ug-international-fee"):
        text = li.get_text(" ", strip=True)
        if not text:
            continue
        parent = li.parent
        if parent and parent.name == "ul":
            continue
        ul = fees.find("ul")
        if ul is None:
            ul = soup.new_tag("ul")
            fees.insert(0, ul)
        li.extract()
        ul.append(li)

_ENTRY_SECTION = "## Entry requirements"
_OVERVIEW_SECTIONS = {"## Course overview", "## Key information"}
_KEEP_ENTRY_H4 = frozenset({"bangladesh"})
_KEEP_ENTRY_H3 = frozenset({"english language requirements"})
_KEY_FACT_HEADINGS = {
    "month of entry",
    "mode of study",
    "location",
    "subject area",
    "duration of study",
    "year of entry",
    "ucas code",
}


def _is_key_fact_heading(heading: str) -> bool:
    text = heading.casefold().strip()
    if text.startswith("fees for"):
        return True
    return text in _KEY_FACT_HEADINGS


def _keep_bangladesh_country_entry_only(markdown: str) -> str:
    """Within Entry requirements, keep only Bangladesh + English language (Group) blocks."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_entry = False
    keep_block = False

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            in_entry = line.strip() == _ENTRY_SECTION
            keep_block = False
            out.append(line)
            continue

        if not in_entry:
            out.append(line)
            continue

        if line.startswith("#### "):
            heading = line[5:].strip().casefold()
            keep_block = heading in _KEEP_ENTRY_H4
            if keep_block:
                out.append(line)
            continue

        if line.startswith("### "):
            heading = line[4:].strip().casefold()
            keep_block = heading in _KEEP_ENTRY_H3
            if keep_block:
                out.append(line)
            continue

        if keep_block:
            out.append(line)

    return "\n".join(out)


def _trim_overview_to_key_facts(markdown: str) -> str:
    """Keep only intake/fees/duration key facts under overview (PG pgt-* / UG key-facts)."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_overview = False
    keep_block = False

    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            section = line.strip()
            if section in _OVERVIEW_SECTIONS:
                in_overview = True
                keep_block = False
                out.append("## Key information")
                continue
            if in_overview:
                heading = line[3:].strip()
                if _is_key_fact_heading(heading):
                    keep_block = True
                    out.append(f"### {heading}")
                    continue
                in_overview = False
                keep_block = False
                out.append(line)
                continue
            in_overview = False
            keep_block = False
            out.append(line)
            continue

        if not in_overview:
            out.append(line)
            continue

        if line.startswith("### "):
            keep_block = _is_key_fact_heading(line[4:].strip())
            if keep_block:
                out.append(line)
            continue

        if keep_block:
            out.append(line)

    return "\n".join(out)


def _normalize_keele_year_of_entry(text: str) -> str:
    years = sorted({int(year) for year in re.findall(r"\b(20\d{2})\b", text)}, reverse=True)
    if not years:
        return text.strip()
    if len(years) == 1:
        return f"September {years[0]}"
    intake_months = ("January", "September")
    return ", ".join(f"{intake_months[index]} {year}" for index, year in enumerate(years[: len(intake_months)]))


def _normalize_keele_duration(text: str) -> str:
    year_values = [int(match.group(1)) for match in re.finditer(r"(\d+)\s*years?", text, re.I)]
    if year_values:
        return f"{min(year_values)} years"
    month_values = [int(match.group(1)) for match in re.finditer(r"(\d+)\s*months?", text, re.I)]
    if month_values:
        return f"{min(month_values)} months"
    return text.strip()


def _normalize_key_information_values(markdown: str) -> str:
    """Normalize Keele Key information bullets (intake years, minimum duration)."""
    academic_year = ""
    acad_match = re.search(r"### Fees for (\d{4})/\d{2}", markdown, re.I)
    if acad_match:
        academic_year = acad_match.group(1)

    lines = markdown.splitlines()
    out: list[str] = []
    current_heading = ""

    for line in lines:
        if line.startswith("### "):
            current_heading = line[4:].strip().casefold()
            out.append(line)
            continue

        if line.startswith("- ") and current_heading == "year of entry":
            out.append(f"- {_normalize_keele_year_of_entry(line[2:])}")
            continue

        if line.startswith("- ") and current_heading == "duration of study":
            out.append(f"- {_normalize_keele_duration(line[2:])}")
            continue

        if line.startswith("- ") and current_heading == "month of entry":
            month_text = line[2:].strip()
            if academic_year and not re.search(r"\b(19|20)\d{2}\b", month_text):
                primary_month = month_text.split(",")[0].strip()
                out.append(f"- {primary_month} {academic_year}")
                continue

        out.append(line)

    return "\n".join(out)


def _has_international_fee(text: str) -> bool:
    return bool(re.search(r"international\s*[-:]", text, re.I))


def _trim_fees_to_international(markdown: str) -> str:
    """Under Fees and funding, keep only international tuition fee line(s)."""
    match = re.search(
        r"^## Fees and funding\s*\n(.*?)(?=^## |\Z)",
        markdown,
        re.S | re.M,
    )
    if not match:
        return markdown

    body = match.group(1)
    international_lines: list[str] = []
    seen: set[str] = set()

    for line in body.splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if not re.search(r"international", text, re.I):
            continue
        if not re.search(r"£[\d,]+", text):
            continue
        if re.search(r"have not yet been confirmed|fee bands visit", text, re.I):
            continue
        bullet = text if text.startswith("-") else f"- {text}"
        if bullet not in seen:
            seen.add(bullet)
            international_lines.append(bullet)

    if not international_lines:
        for found in re.finditer(
            r"International[^.\n]*£[\d,]+[^.\n]*",
            body,
            re.I,
        ):
            bullet = f"- {found.group(0).strip()}"
            if bullet not in seen:
                seen.add(bullet)
                international_lines.append(bullet)

    replacement = "## Fees and funding\n\n" + "\n".join(international_lines) + "\n"
    if not international_lines:
        replacement = ""
    return markdown[: match.start()] + replacement + markdown[match.end() :]


def _drop_duplicate_fees_section(markdown: str) -> str:
    """Remove Fees and funding when international fees already appear in Key information."""
    key_section = ""
    match = re.search(
        r"^## Key information\s*\n(.*?)(?=^## |\Z)",
        markdown,
        re.S | re.M,
    )
    if match:
        key_section = match.group(1)
    if not _has_international_fee(key_section):
        return markdown
    return remove_markdown_heading_section(
        markdown,
        heading="Fees and funding",
        level=2,
        until_level=2,
    )


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Keele: key facts, Bangladesh entry, drop marketing/duplicate sections."""
    cleaned = markdown
    for heading in (
        "Course overview",
        "Course content",
        "Course summary",
        "Additional opportunities",
    ):
        cleaned = remove_markdown_heading_section(
            cleaned,
            heading=heading,
            level=2,
            until_level=2,
        )
    cleaned = _trim_overview_to_key_facts(cleaned)
    cleaned = _normalize_key_information_values(cleaned)
    cleaned = _keep_bangladesh_country_entry_only(cleaned)
    cleaned = _trim_fees_to_international(cleaned)
    cleaned = _drop_duplicate_fees_section(cleaned)

    lines: list[str] = []
    title = ""
    seen_h3: set[str] = set()
    for line in cleaned.splitlines():
        stripped = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            title = stripped[2:].strip()
            lines.append(line)
            continue
        if title and stripped == title:
            continue
        if title and stripped.startswith(f"{title} - "):
            continue
        if title and stripped.startswith("## ") and title.casefold() in stripped.casefold() and " - " in stripped:
            continue
        if line.startswith("### "):
            heading = line[4:].strip()
            if heading in seen_h3:
                continue
            seen_h3.add(heading)
        lines.append(line)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text.strip())


if __name__ == "__main__":
    raise SystemExit(main())
