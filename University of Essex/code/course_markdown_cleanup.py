"""University of Essex course markdown cleanup.

Presetup/execute markdown keeps title, key course details, entry requirements,
English requirements, and fees. Marketing prose, modules, teaching, and apply
noise are removed via ENV heading rules plus the helpers below.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

_spec = importlib.util.spec_from_file_location(
    "shared_course_markdown_cleanup",
    _SHARED / "course_markdown_cleanup.py",
)
_shared_cleanup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared_cleanup)
CourseMarkdownCleaner = _shared_cleanup.CourseMarkdownCleaner

_DETAILS_LINE_RE = re.compile(
    r"^(?:Apply now|How to apply)?The details.+$",
    re.M | re.I,
)
_ENTRY_HEADING_RE = re.compile(
    r"^###\s+(?:UK entry requirements|Clearing entry requirements|International & EU entry requirements)\s*$",
    re.M | re.I,
)
_TAB_NAV_RE = re.compile(
    r"^(?:Apply now)?- Overview\s*\n(?:- [^\n]+\n)+",
    re.M,
)
_SUBTITLE_LINE_RE = re.compile(r"^####\s*\([^)]+\)\s*$", re.M)
_CLEARING_APPLY_RE = re.compile(
    r"^Now In Clearing\s*\n(?:Apply now[^\n]*\n)+(?:Apply now- Overview\s*\n(?:- [^\n]+\n)+)?",
    re.M | re.I,
)
_WHY_GREAT_RE = re.compile(
    r"^Why we're great\..*?(?=^###\s|\Z)",
    re.M | re.S | re.I,
)
_MODULE_LINK_RE = re.compile(
    r"^\[View .+ on our Module Directory\]\([^\)]+\)\s*\n?",
    re.M | re.I,
)
_COMPONENT_LINE_RE = re.compile(
    r"^(?:Year \d+|COMPONENT \d+:|(?:\(\d+ CREDITS\)))\s*$",
    re.M | re.I,
)
_TRAILING_BOILERPLATE_RE = re.compile(
    r"\nAt Essex we pride ourselves on being a welcoming and inclusive student community\..*",
    re.S | re.I,
)
_PLACEMENT_ABROAD_FEE_INTRO_RE = re.compile(
    r"If your course has the option to include a placement year or study abroad[^\n]*\n+",
    re.I,
)
_HOME_UK_FEE_RE = re.compile(
    r"^### Home/UK fee\s*\n.*?(?=^### |\Z)",
    re.M | re.S | re.I,
)
_DETAILS_FIELDS = (
    ("Course", "Course"),
    ("UCAS code", "UCAS code"),
    ("Start date", "Start date"),
    ("Study mode", "Study mode"),
    ("Duration", "Duration"),
    ("Location", "Location"),
    ("Based in", "Based in"),
)


def _parse_details_line(line: str) -> dict[str, str]:
    text = re.sub(r"^.*The details", "", line, count=1, flags=re.I).strip()
    if not text:
        return {}
    text = re.sub(r"Clearing entry requirements\s*$", "", text, flags=re.I).strip()
    facts: dict[str, str] = {}
    markers = [f"{label}:" for label, _ in _DETAILS_FIELDS]
    positions: list[tuple[int, str, str]] = []
    for label, output in _DETAILS_FIELDS:
        marker = f"{label}:"
        index = text.find(marker)
        if index >= 0:
            positions.append((index, label, output))
    positions.sort(key=lambda item: item[0])
    for idx, (start, label, output) in enumerate(positions):
        value_start = start + len(f"{label}:")
        value_end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        value = text[value_start:value_end].strip()
        if value:
            facts[output] = value
    return facts


def _format_key_course_information(facts: dict[str, str]) -> str:
    if not facts:
        return ""
    lines = ["## Key course information", ""]
    for label, value in facts.items():
        lines.append(f"- **{label}:** {value}")
    return "\n".join(lines)


def _inject_key_course_information(markdown: str, facts_markdown: str) -> str:
    if not facts_markdown:
        return markdown
    if "## Key course information" in markdown:
        return markdown
    title_match = re.search(r"^#\s+.+$", markdown, re.M)
    insert_at = title_match.end() if title_match else 0
    suffix = markdown[insert_at:].lstrip("\n")
    prefix = markdown[:insert_at].rstrip("\n")
    return f"{prefix}\n\n{facts_markdown}\n\n{suffix}"


def strip_essex_marketing_before_entry(markdown: str) -> str:
    """Drop overview/modules prose before the first entry-requirements heading."""
    details_match = _DETAILS_LINE_RE.search(markdown)
    if not details_match:
        return markdown
    entry_match = _ENTRY_HEADING_RE.search(markdown, details_match.end())
    if not entry_match:
        return markdown
    before = markdown[: details_match.end()].rstrip()
    after = markdown[entry_match.start() :].lstrip("\n")
    return f"{before}\n\n{after}"


def strip_essex_inline_noise(markdown: str) -> str:
    markdown = _TAB_NAV_RE.sub("", markdown)
    markdown = _CLEARING_APPLY_RE.sub("", markdown)
    markdown = _WHY_GREAT_RE.sub("", markdown)
    markdown = _MODULE_LINK_RE.sub("", markdown)
    markdown = _COMPONENT_LINE_RE.sub("", markdown)
    markdown = _HOME_UK_FEE_RE.sub("", markdown)
    markdown = _PLACEMENT_ABROAD_FEE_INTRO_RE.sub("", markdown)
    markdown = _TRAILING_BOILERPLATE_RE.sub("\n", markdown)
    markdown = _DETAILS_LINE_RE.sub("", markdown)
    markdown = _SUBTITLE_LINE_RE.sub("", markdown)
    markdown = re.sub(r"^How to apply", "", markdown, flags=re.M | re.I)
    return markdown


def preprocess_course_markdown_uni(markdown: str) -> str:
    details_match = _DETAILS_LINE_RE.search(markdown)
    if details_match:
        facts = _parse_details_line(details_match.group(0))
        key_info = _format_key_course_information(facts)
        if key_info:
            markdown = _inject_key_course_information(markdown, key_info)
    return strip_essex_marketing_before_entry(markdown)


def cleanup_course_markdown_uni(markdown: str) -> str:
    markdown = strip_essex_inline_noise(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown.strip())
    return markdown + "\n"


def _course_markdown_dirs(code_dir: Path) -> list[Path]:
    uni_dir = code_dir.resolve().parent
    clean_dir = uni_dir / "output" / "clean" / "courses"
    if clean_dir.is_dir():
        return [clean_dir]
    legacy = uni_dir / "courses"
    return [legacy] if legacy.is_dir() else []


def main(argv: list[str] | None = None) -> int:
    code_dir = Path(__file__).resolve().parent
    cleaner = CourseMarkdownCleaner()
    targets = _course_markdown_dirs(code_dir)
    if not targets:
        raise SystemExit("No course markdown directories found.")

    updated = 0
    total = 0
    for courses_dir in targets:
        print(f"Cleaning course markdown in {courses_dir}...")
        from study_level import iter_course_markdown

        for path in iter_course_markdown(courses_dir):
            total += 1
            raw = path.read_text(encoding="utf-8")
            meta, body = cleaner.parse_frontmatter(raw)
            cleaned_body = cleaner.cleanup_course_markdown(body.rstrip("\n"), code_dir=code_dir)
            output = cleaner.format_frontmatter(meta) + cleaned_body
            if not output.endswith("\n"):
                output += "\n"
            if output != raw:
                path.write_text(output, encoding="utf-8")
                updated += 1
                print(f"  updated {path.relative_to(courses_dir.parent)}")
    print(f"Done: {updated}/{total} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
