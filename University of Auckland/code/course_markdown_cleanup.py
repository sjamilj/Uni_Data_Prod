"""University of Auckland course markdown cleanup (conditional rules).

Simple heading removal can also be configured in code/.env via
COURSE_MARKDOWN_REMOVE_SECTIONS ("level :: heading"). This module handles the
Auckland-specific structure that .env cannot express cleanly:

  * the same heading emitted twice in a row (COURSE_CLEAN_BLOCKS heading +
    the page's own <h2>), and headings left with no body
  * link-only / widget-only sections that add nothing to the markdown
  * postgraduate entry requirements repeated per applicant type (keep the last)
  * undergraduate entry requirements: keep only GCE A Level / GPE (+ IELTS) bullets, bolded
  * widget leftovers ("Select your study option") and domestic fee lines

Edit SECTIONS_TO_DROP below to change what is removed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main

# Headings whose whole section (heading + body, up to the next heading of the
# same or higher level) is removed. Matched case-insensitively, any level.
SECTIONS_TO_DROP = {
    "programme overview",
    "programme structure",
    "sample programme structure",
    "student loans and allowances",
    "cost of living",
    "other important dates",
    "portfolio guidelines",
    "careers and further study",
    "where could this programme take you",
    "jobs related to this programme",
    "further study options",
    "student career planning service",
}

# Headings whose heading LINE is removed but whose body text is kept.
# Matched case-insensitively, any level, trailing ':' ignored.
HEADINGS_TO_STRIP = {
    "secondary school qualifications",
    "you need to have one of the following",
    "you need to have the following",
    "further requirements",
    "tertiary qualifications",
    "further programme requirements",
    "other pathways to study",
    "find out about financial support",
    "find out about financial support information",
}

# Pattern-based drops, e.g. "Year 1 120 points", "Year one 120 points".
SECTION_PATTERNS_TO_DROP = (
    re.compile(r"^year\s+(?:one|two|three|four|five|six|\d+)\s+\d+\s+points$", re.I),
)

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = _HEADING.match(line.strip())
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _key(text: str) -> str:
    return re.sub(r"[\s:.!?*_`]+$", "", text.strip()).casefold()


def _drop_sections(markdown: str) -> str:
    """Remove each SECTIONS_TO_DROP section including its body and sub-headings."""
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        heading = _parse_heading(lines[index])
        if heading and (
            _key(heading[1]) in {_key(x) for x in SECTIONS_TO_DROP}
            or any(p.match(_key(heading[1])) for p in SECTION_PATTERNS_TO_DROP)
        ):
            level = heading[0]
            index += 1
            while index < len(lines):
                nxt = _parse_heading(lines[index])
                if nxt and nxt[0] <= level:
                    break
                index += 1
            continue
        kept.append(lines[index])
        index += 1
    return "\n".join(kept)


def _keep_last_programme_requirements(markdown: str) -> str:
    """Postgraduate pages render the entry requirements once per applicant type
    (University of Auckland graduates first, 'Another tertiary institution'
    last). Keep only the last '### Programme requirements' set: drop everything
    from the first occurrence up to (not including) the last one."""
    lines = markdown.splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if (h := _parse_heading(line)) and h[0] == 3 and _key(h[1]) == "programme requirements"
    ]
    if len(starts) < 2:
        return markdown
    return "\n".join(lines[: starts[0]] + lines[starts[-1] :])


_DOMESTIC_FEE_LINE = re.compile(r"^\s*[-*]\s+\**\s*Domestic students\b.*$", re.I)
_TAB_LABEL_LINE = re.compile(r"^(?:[A-Za-z][A-Za-z ]*?\s\d+\s+points\s*)+$", re.I)


def _drop_domestic_fee_lines(markdown: str) -> str:
    """Remove '- **Domestic students:** NZ$…' fee bullets (international focus)."""
    return "\n".join(
        line for line in markdown.splitlines() if not _DOMESTIC_FEE_LINE.match(line)
    )


def _drop_select_study_option(markdown: str) -> str:
    """Remove the '#### Select your study option:' widget heading and the tab
    labels under it (e.g. 'Research 120 points Research 180 points')."""
    lines = markdown.splitlines()
    kept: list[str] = []
    i = 0
    while i < len(lines):
        heading = _parse_heading(lines[i])
        if heading and _key(heading[1]) == "select your study option":
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            i = j + 1 if j < len(lines) and _TAB_LABEL_LINE.match(lines[j].strip()) else i + 1
            continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept)


_REQ_BULLET_START = re.compile(r"^\s*-\s+(?:Qualification|Grade required)\b", re.I)
_PG_TITLE = re.compile(r"^#\s+.*\b(?:Master|Doctor|Postgraduate|Graduate)\b", re.I | re.M)
_ENTRY_HEADING_KEY = re.compile(r"(?:^|\s)entry requirements$")
_A_LEVEL = re.compile(r"GCE\s+A\s+Levels?", re.I)
_A_LEVEL_LONG = re.compile(
    r"(GCE A Levels?)(?:/CIE)?\s+General Certificate of Education \(GCE\) Advanced Level"
    r"\s+Score required\s+(.+?)(?=\s+\+)",
    re.I,
)
_IELTS_SCORE = re.compile(r"(IELTS Academic\b.*?Score required\s+)(\d+(?:\.\d+)?)", re.I)
_GPE_SCORE = re.compile(r"(Grade Point Equivalent\s+)(\d+(?:\.\d+)?)", re.I)
_TRAILING_LINK = re.compile(r"\s*\[[^\]]*\]\([^)]*\)\s*$")
_IELTS_ONLY = re.compile(r"^\s*-\s+Qualification\s+IELTS\b", re.I)
_GPE_BULLET = re.compile(r"^\s*-\s+Grade required\s+GPE\b", re.I)


def _compact_ug_entry_requirements(markdown: str) -> str:
    """Undergraduate pages only. Inside '## ... entry requirements' keep just:
      * the GCE A Level + IELTS bullet,
      * the GPE bullet and its IELTS bullet,
    each with its continuation line (e.g. 'No bands less than 5.5'), and bold
    the A Level grade, GPE and IELTS scores. Everything else in the section
    (intros, headings, links, IB/CIE lists, pathways) is dropped, and the
    heading becomes '## Entry requirements'. If no such bullets are found the
    section is left untouched."""
    if _PG_TITLE.search(markdown) or re.search(r"^\s*-\s+Study option\b", markdown, re.M):
        return markdown
    lines = markdown.splitlines()
    start = None
    for i, line in enumerate(lines):
        h = _parse_heading(line)
        if h and h[0] == 2 and _ENTRY_HEADING_KEY.search(_key(h[1])):
            start = i
            break
    if start is None:
        return markdown
    end = len(lines)
    for i in range(start + 1, len(lines)):
        h = _parse_heading(lines[i])
        if h and h[0] <= 2:
            end = i
            break

    body = lines[start + 1 : end]
    out: list[str] = []
    i = 0
    while i < len(body):
        if not _REQ_BULLET_START.match(body[i]):
            i += 1
            continue
        j = i + 1
        while (
            j < len(body)
            and body[j].strip()
            and not body[j].lstrip().startswith(("- ", "#", "["))
        ):
            j += 1
        block = body[i:j]
        first = block[0]
        i = j
        if _A_LEVEL.search(first):
            text = re.sub(r"^\s*-\s+", "", first)
            text = _A_LEVEL_LONG.sub(lambda m: f"{m.group(1)} **{m.group(2).strip()}**", text)
            text = _IELTS_SCORE.sub(lambda m: f"{m.group(1)}**{m.group(2)}**", text)
            out.extend([text, *block[1:], ""])
        elif _GPE_BULLET.match(first):
            text = _TRAILING_LINK.sub("", re.sub(r"^\s*-\s+", "", first)).rstrip()
            text = _GPE_SCORE.sub(lambda m: f"{m.group(1)}**{m.group(2)}**", text)
            out.extend([text, *block[1:]])
        elif _IELTS_ONLY.match(first):
            text = _IELTS_SCORE.sub(lambda m: f"{m.group(1)}**{m.group(2)}**", first)
            out.extend([text, *block[1:]])
    if not out:
        return markdown
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(lines[:start] + ["## Entry requirements", ""] + out + [""] + lines[end:])


def _strip_headings(markdown: str) -> str:
    """Remove the heading line for each HEADINGS_TO_STRIP entry; keep the body."""
    strip = {_key(h) for h in HEADINGS_TO_STRIP}
    kept = []
    for line in markdown.splitlines():
        heading = _parse_heading(line)
        if heading and _key(heading[1]) in strip:
            continue
        kept.append(line)
    return "\n".join(kept)


def _drop_empty_headings(markdown: str) -> str:
    """Drop a heading with no body before the next heading of the same or higher
    level (e.g. '## Programme overview' followed by '## Programme overview').
    Repeats until stable so stacked empty headings collapse fully."""
    lines = markdown.splitlines()
    while True:
        kept: list[str] = []
        changed = False
        for i, line in enumerate(lines):
            heading = _parse_heading(line)
            if heading:
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                nxt = _parse_heading(lines[j]) if j < len(lines) else None
                if j >= len(lines) or (nxt and nxt[0] <= heading[0]):
                    changed = True
                    continue
            kept.append(line)
        lines = kept
        if not changed:
            return "\n".join(lines)


def _drop_duplicate_adjacent_lines(markdown: str) -> str:
    """Collapse a non-blank line repeated immediately (ignoring blank lines)."""
    out: list[str] = []
    last = None
    for line in markdown.splitlines():
        s = line.strip()
        if s and s == last:
            continue
        out.append(line)
        if s:
            last = s
    return "\n".join(out)


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip()) + "\n"


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Auckland-only rules applied after shared .env section removal."""
    cleaned = _keep_last_programme_requirements(markdown)
    cleaned = _drop_sections(cleaned)
    cleaned = _drop_select_study_option(cleaned)
    cleaned = _drop_domestic_fee_lines(cleaned)
    cleaned = _compact_ug_entry_requirements(cleaned)
    cleaned = _strip_headings(cleaned)
    cleaned = _drop_empty_headings(cleaned)
    cleaned = _drop_duplicate_adjacent_lines(cleaned)
    return _normalize_blank_lines(cleaned)


if __name__ == "__main__":
    raise SystemExit(main())