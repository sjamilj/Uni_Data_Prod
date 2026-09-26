#!/usr/bin/env python3
"""Split ULaw undergraduate course markdown that lists a Foundation Year intake into foundation/ copies.

When ``## Course Start Dates`` includes a variant such as
``BSc (Hons) Computer Science with Foundation Year``, this writes a sibling file under
``output/clean/courses/foundation/`` and removes those lines from the undergraduate markdown.

Example::

    python split_foundation_year_courses.py
    python split_foundation_year_courses.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_ROOT = _CODE_DIR.parent
_SHARED = _UNI_ROOT.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from study_level import CLEAN_COURSES_SUBDIR
from uni_pages import split_frontmatter

_START_DATES_SECTION = "## Course Start Dates"
_FOUNDATION_YEAR_RE = re.compile(r"foundation\s+year", re.I)
_START_DATE_BULLET_RE = re.compile(r"^-\s+\*\*(.+?)\*\*\s+-\s+(.+)$")
_FOUNDATION_SUFFIX = "-with-foundation-year"


def _format_frontmatter(meta: dict[str, str]) -> str:
    order = (
        "source_html",
        "source_url",
        "page_type",
        "university",
        "cleaned_at",
        "course_url",
        "study_level",
        "source_undergraduate_md",
    )
    seen: set[str] = set()
    lines = ["---"]
    for key in order:
        if key in meta:
            lines.append(f"{key}: {meta[key]}")
            seen.add(key)
    for key, value in meta.items():
        if key not in seen:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _is_foundation_bullet(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("- ") and bool(_FOUNDATION_YEAR_RE.search(stripped))


def _filter_start_dates_section(section: str, *, keep_foundation: bool) -> str:
    lines = section.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("#### "):
            if line.strip():
                out.append(line)
            i += 1
            continue
        block_prefix: list[str] = [line]
        i += 1
        bullets: list[str] = []
        while i < len(lines) and not lines[i].startswith("#### "):
            if lines[i].strip().startswith("- "):
                bullets.append(lines[i])
            elif lines[i].strip():
                block_prefix.append(lines[i])
            i += 1
        kept = [b for b in bullets if _is_foundation_bullet(b) == keep_foundation]
        if kept:
            out.extend(block_prefix)
            out.extend(kept)
            out.append("")
    while out and not out[-1].strip():
        out.pop()
    text = "\n".join(out)
    return text + ("\n" if text else "")


def _extract_start_dates(markdown: str) -> tuple[str, str, str] | None:
    if _START_DATES_SECTION not in markdown:
        return None
    head, rest = markdown.split(_START_DATES_SECTION, 1)
    end = re.search(r"\r?\n##\s", rest)
    if end:
        section, tail = rest[: end.start()], rest[end.start() :]
    else:
        section, tail = rest, ""
    return head, section, tail


def _rebuild_start_dates(head: str, section: str, tail: str) -> str:
    block = section.strip()
    if block:
        block = f"\n\n{block}\n"
    else:
        block = "\n"
    if tail and not tail.startswith("\n"):
        tail = "\n" + tail
    return f"{head.rstrip()}\n\n{_START_DATES_SECTION}{block}{tail}"


def _foundation_title_from_lines(lines: list[str]) -> str:
    titles: list[str] = []
    for line in lines:
        match = _START_DATE_BULLET_RE.match(line.strip())
        if match and _FOUNDATION_YEAR_RE.search(match.group(1)):
            titles.append(match.group(1).strip())
    if not titles:
        return ""
    plain = [t for t in titles if "blended" not in t.casefold()]
    return (plain or titles)[-1]


def _foundation_output_name(ug_path: Path) -> str:
    stem = ug_path.stem
    if stem.endswith(_FOUNDATION_SUFFIX):
        return f"{stem}.md"
    return f"{stem}{_FOUNDATION_SUFFIX}.md"


def _update_pipeline_comment(body: str, study_level: str) -> str:
    return re.sub(
        r"(study_level=)\w+",
        rf"\g<1>{study_level}",
        body,
        count=1,
    )


def _rewrite_h1(body: str, title: str) -> str:
    if not title:
        return body
    return re.sub(r"^#\s+.+$", f"# {title}", body, count=1, flags=re.M)


def process_undergraduate_md(
    ug_path: Path,
    foundation_dir: Path,
    *,
    dry_run: bool,
) -> tuple[bool, bool]:
    """Return (foundation_written, undergraduate_updated)."""
    raw = ug_path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw)
    parts = _extract_start_dates(body)
    if parts is None:
        return False, False
    head, section, tail = parts
    foundation_section = _filter_start_dates_section(section, keep_foundation=True)
    if not foundation_section.strip():
        return False, False
    foundation_lines = [
        ln for ln in foundation_section.splitlines() if _is_foundation_bullet(ln)
    ]

    foundation_title = _foundation_title_from_lines(foundation_lines)
    foundation_meta = deepcopy(meta)
    foundation_meta["study_level"] = "foundation"
    foundation_meta["cleaned_at"] = date.today().isoformat()
    foundation_meta["source_undergraduate_md"] = ug_path.name

    standard_section = _filter_start_dates_section(section, keep_foundation=False)
    foundation_body = _rebuild_start_dates(head, foundation_section, tail)
    foundation_body = _rewrite_h1(foundation_body, foundation_title)
    foundation_body = _update_pipeline_comment(foundation_body, "foundation")

    ug_body = _rebuild_start_dates(head, standard_section, tail)
    ug_output = _format_frontmatter(meta) + ug_body.rstrip() + "\n"
    foundation_output = _format_frontmatter(foundation_meta) + foundation_body.rstrip() + "\n"

    foundation_path = foundation_dir / _foundation_output_name(ug_path)
    if not dry_run:
        foundation_dir.mkdir(parents=True, exist_ok=True)
        foundation_path.write_text(foundation_output, encoding="utf-8")
        ug_path.write_text(ug_output, encoding="utf-8")

    return True, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--courses-dir",
        type=Path,
        default=_UNI_ROOT / "output" / "clean" / CLEAN_COURSES_SUBDIR,
        help="Root clean/courses directory (default: ../output/clean/courses)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report actions without writing files",
    )
    args = parser.parse_args(argv)

    ug_dir = args.courses_dir / "undergraduate"
    foundation_dir = args.courses_dir / "foundation"
    if not ug_dir.is_dir():
        print(f"Undergraduate folder not found: {ug_dir}", file=sys.stderr)
        return 1

    created = 0
    updated = 0
    for path in sorted(ug_dir.glob("*.md")):
        wrote, changed = process_undergraduate_md(
            path, foundation_dir, dry_run=args.dry_run
        )
        if wrote:
            created += 1
            name = _foundation_output_name(path)
            action = "would write" if args.dry_run else "wrote"
            print(f"  {action} foundation/{name} from {path.name}")
        if changed:
            updated += 1

    suffix = " (dry run)" if args.dry_run else ""
    print(f"Done{suffix}: {created} foundation file(s), {updated} undergraduate file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
