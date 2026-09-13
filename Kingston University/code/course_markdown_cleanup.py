"""Kingston University course markdown cleanup.

Pipeline pass (automatic):
  - COURSE_MARKDOWN_REMOVE_SECTIONS in code/.env
  - cleanup_course_markdown_uni()

Manual extra pass (shared/extra_clean_courses.py):
  - extra_clean_course_markdown_uni(markdown, study_level=...)

Fees rules:
  - Keep only the latest ### YYYY/YY block under ## Fees and funding
  - In PG-style fee tables (Full Time / Part Time rows): drop Home (UK) rows and Part Time

Entry rules (route split):
  - foundation route: drop direct-degree #### blocks (keep "including foundation year")
  - undergraduate route: drop "including foundation year" #### blocks
  - keep only latest ### Qualifications needed for YYYY block

Fees rules (continued):
  - UG-style fee tables: drop Home (UK students) rows (including Foundation Year home fees)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main

_FEES_SECTION = "## Fees and funding"
_FEES_YEAR_HEADING = re.compile(r"^### (\d{4})/\d{1,2}\s*$")
_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
_PART_TIME_OPTIONS = re.compile(
    r"^To see the full-time and/or part-time options available for this course.*$",
    re.I,
)
_HOME_CATEGORY = re.compile(r"home|uk students", re.I)
_INTERNATIONAL_CATEGORY = re.compile(r"international", re.I)
_PART_TIME_ROW = re.compile(r"part[- ]time", re.I)
_ENTRY_SECTION = "## Entry requirements"
_H4_HEADING = re.compile(r"^#### ")
_FOUNDATION_ROUTE_HEADING = re.compile(r"^#### .*including foundation year", re.I)
_QUAL_YEAR_HEADING = re.compile(r"^### Qualifications needed for (\d{4}):\s*$")


def _fees_year_from_heading(line: str) -> int | None:
    match = _FEES_YEAR_HEADING.match(line.strip())
    return int(match.group(1)) if match else None


def _split_table_cells(line: str) -> tuple[str, str] | None:
    match = _TABLE_ROW.match(line.strip())
    if not match:
        return None
    parts = [cell.strip() for cell in match.group(1).split("|")]
    if len(parts) < 2:
        return None
    if parts[0].startswith("---"):
        return None
    return parts[0], parts[1]


def _is_pg_style_fees_table(lines: list[str]) -> bool:
    for line in lines:
        cells = _split_table_cells(line)
        if cells and _PART_TIME_ROW.search(cells[0]):
            return True
    return False


def _clean_pg_style_fee_table(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_home_rows = False
    removed_part_time = False

    for line in lines:
        cells = _split_table_cells(line)
        if cells is None:
            cleaned.append(line)
            continue

        label, value = cells
        if not value:
            if _HOME_CATEGORY.search(label):
                skip_home_rows = True
                continue
            if _INTERNATIONAL_CATEGORY.search(label):
                skip_home_rows = False
                continue
            cleaned.append(line)
            continue

        if _PART_TIME_ROW.search(label):
            removed_part_time = True
            continue
        if skip_home_rows:
            continue
        cleaned.append(line)

    if removed_part_time:
        cleaned = [line for line in cleaned if not _PART_TIME_OPTIONS.match(line.strip())]
    return cleaned


def _has_home_fee_category(lines: list[str]) -> bool:
    for line in lines:
        cells = _split_table_cells(line)
        if cells and _HOME_CATEGORY.search(cells[0]):
            return True
    return False


def _clean_home_fee_table(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    skip_home_rows = False

    for line in lines:
        cells = _split_table_cells(line)
        if cells is None:
            cleaned.append(line)
            continue

        label, value = cells
        if _HOME_CATEGORY.search(label):
            skip_home_rows = True
            continue
        if not value:
            if _INTERNATIONAL_CATEGORY.search(label):
                skip_home_rows = False
                continue
            cleaned.append(line)
            continue

        if skip_home_rows:
            continue
        cleaned.append(line)

    return cleaned


def _filter_fees_year_blocks(fees_body: str) -> str:
    lines = fees_body.splitlines()
    year_starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        year = _fees_year_from_heading(line)
        if year is not None:
            year_starts.append((index, year))

    if len(year_starts) <= 1:
        body = fees_body
    else:
        keep_year = max(year for _, year in year_starts)
        keep_index = next(index for index, year in year_starts if year == keep_year)
        next_index = next(
            (index for index, _ in year_starts if index > keep_index),
            len(lines),
        )
        body = "\n".join(lines[keep_index:next_index]).strip()

    body_lines = body.splitlines()
    if _has_home_fee_category(body_lines):
        body_lines = _clean_home_fee_table(body_lines)
    if _is_pg_style_fees_table(body_lines):
        body_lines = _clean_pg_style_fee_table(body_lines)
    return "\n".join(body_lines).strip()


def _filter_entry_qualification_years(lines: list[str]) -> list[str]:
    qual_starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = _QUAL_YEAR_HEADING.match(line.strip())
        if match:
            qual_starts.append((index, int(match.group(1))))
    if len(qual_starts) <= 1:
        return lines

    keep_year = max(year for _, year in qual_starts)
    output: list[str] = []
    index = 0
    while index < len(lines):
        match = _QUAL_YEAR_HEADING.match(lines[index].strip())
        if match:
            year = int(match.group(1))
            block_end = index + 1
            while block_end < len(lines):
                if _QUAL_YEAR_HEADING.match(lines[block_end].strip()):
                    break
                if lines[block_end].startswith("### ") and not lines[block_end].startswith("#### "):
                    break
                block_end += 1
            if year == keep_year:
                output.extend(lines[index:block_end])
            index = block_end
            continue
        output.append(lines[index])
        index += 1
    return output


def _filter_entry_qualification_years_in_markdown(markdown: str) -> str:
    marker = _ENTRY_SECTION
    if marker not in markdown:
        return markdown

    head, tail = markdown.split(marker, 1)
    next_section = re.search(r"\n## ", tail)
    if next_section:
        entry_body = tail[: next_section.start()]
        after_entry = tail[next_section.start() :]
    else:
        entry_body = tail
        after_entry = ""

    filtered = _filter_entry_qualification_years(entry_body.splitlines())
    cleaned_body = "\n".join(filtered).strip()
    while "\n\n\n" in cleaned_body:
        cleaned_body = cleaned_body.replace("\n\n\n", "\n\n")

    rebuilt = head.rstrip() + "\n\n" + marker + "\n\n" + cleaned_body
    if after_entry:
        rebuilt += "\n\n" + after_entry.lstrip("\n")
    return rebuilt.rstrip() + "\n"


def _should_keep_entry_block(heading: str, study_level: str) -> bool:
    is_foundation_route = _FOUNDATION_ROUTE_HEADING.match(heading) is not None
    if study_level == "foundation":
        return is_foundation_route
    if study_level == "undergraduate":
        return not is_foundation_route
    return True


def _filter_entry_h4_blocks(lines: list[str], study_level: str) -> list[str]:
    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _H4_HEADING.match(line):
            output.append(line)
            index += 1
            continue

        block_end = index + 1
        while block_end < len(lines) and not _H4_HEADING.match(lines[block_end]):
            if lines[block_end].startswith("### "):
                break
            block_end += 1

        if _should_keep_entry_block(line, study_level):
            output.extend(lines[index:block_end])
        index = block_end
    return output


def filter_entry_requirements_for_route(markdown: str, study_level: str) -> str:
    marker = _ENTRY_SECTION
    if marker not in markdown or study_level not in {"foundation", "undergraduate"}:
        return markdown

    head, tail = markdown.split(marker, 1)
    next_section = re.search(r"\n## ", tail)
    if next_section:
        entry_body = tail[: next_section.start()]
        after_entry = tail[next_section.start() :]
    else:
        entry_body = tail
        after_entry = ""

    filtered = _filter_entry_qualification_years(entry_body.splitlines())
    filtered = _filter_entry_h4_blocks(filtered, study_level)
    cleaned_body = "\n".join(filtered).strip()
    while "\n\n\n" in cleaned_body:
        cleaned_body = cleaned_body.replace("\n\n\n", "\n\n")

    rebuilt = head.rstrip() + "\n\n" + marker + "\n\n" + cleaned_body
    if after_entry:
        rebuilt += "\n\n" + after_entry.lstrip("\n")
    return rebuilt.rstrip() + "\n"


def inject_route_selection_markdown(
    markdown: str,
    *,
    route_course: str,
    start_year: str,
    route_mode: str,
    ucas_code: str = "",
) -> str:
    """Insert route selector values (course / start date / mode) into cleaned markdown."""
    title = f"# {route_course} ({start_year})"
    if ucas_code:
        title += f" — UCAS {ucas_code}"

    selection_block = "\n".join(
        [
            "## Key course information",
            "",
            f"- **Course:** {route_course}",
            f"- **Start date:** {start_year}",
            f"- **Mode:** {route_mode}",
            "",
        ]
    )

    body = markdown
    if body.startswith("# "):
        body = body.split("\n", 1)[1].lstrip("\n")

    if "## Key course information" in body:
        head, tail = body.split("## Key course information", 1)
        tail = re.sub(r"^[\s\S]*?(?=\n## |\Z)", "", tail, count=1)
        body = head.rstrip() + "\n\n" + selection_block.rstrip() + tail
    elif "## Entry requirements" in body:
        body = body.replace("## Entry requirements", selection_block + "## Entry requirements", 1)
    else:
        body = selection_block + body

    return f"{title}\n\n{body.rstrip()}\n"


def update_route_frontmatter(meta: dict[str, str], *, route_course: str, start_year: str, route_mode: str, md_rel: str, ucas_code: str = "") -> dict[str, str]:
    updated = dict(meta)
    updated["route_course"] = route_course
    updated["start_year"] = start_year
    updated["route_mode"] = route_mode
    updated["output_md"] = md_rel
    course_url = updated.get("course_url") or updated.get("source_url") or ""
    if course_url:
        updated["hub_url"] = course_url
    if ucas_code:
        updated["ucas_code"] = ucas_code
    return updated


def _apply_kingston_fees_cleanup(markdown: str) -> str:
    marker = _FEES_SECTION
    if marker not in markdown:
        return markdown

    head, tail = markdown.split(marker, 1)
    next_section = re.search(r"\n## ", tail)
    if next_section:
        fees_body = tail[: next_section.start()]
        after_fees = tail[next_section.start() :]
    else:
        fees_body = tail
        after_fees = ""

    cleaned_fees = _filter_fees_year_blocks(fees_body.strip())
    rebuilt = head.rstrip() + "\n\n" + marker + "\n\n" + cleaned_fees
    if after_fees:
        rebuilt += "\n\n" + after_fees.lstrip("\n")
    return rebuilt.rstrip() + "\n"


def _apply_kingston_cleanup(markdown: str, *, study_level: str | None = None) -> str:
    markdown = _filter_entry_qualification_years_in_markdown(markdown)
    if study_level in {"foundation", "undergraduate"}:
        markdown = filter_entry_requirements_for_route(markdown, study_level)
    return _apply_kingston_fees_cleanup(markdown)


def cleanup_course_markdown_uni(markdown: str) -> str:
    return _apply_kingston_cleanup(markdown)


def extra_clean_course_markdown_uni(markdown: str, *, study_level: str) -> str:
    return _apply_kingston_cleanup(markdown, study_level=study_level)


if __name__ == "__main__":
    raise SystemExit(main())
