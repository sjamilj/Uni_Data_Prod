#!/usr/bin/env python3
"""Backfill Duration + IELTS on course .md from matched english-requirements.md rows.

Only updates courses that map to a programme row and gain at least one new field.

Example::

    python backfill_course_from_english.py
    python backfill_course_from_english.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_ROOT = _CODE_DIR.parent
_SHARED = _UNI_ROOT.parent / "shared"
_code_str = str(_CODE_DIR)
if _code_str in sys.path:
    sys.path.remove(_code_str)
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if _code_str not in sys.path:
    sys.path.append(_code_str)

from study_level import CLEAN_COURSES_SUBDIR
from uni_pages import split_frontmatter

from ulaw_english_program_map import (
    duration_display_from_program,
    load_english_programs,
    match_english_program,
)

_NORMALIZED = "## Key facts (normalized)"
_DURATION_RE = re.compile(r"^-\s*\*\*Duration:\*\*", re.I)
_IELTS_IN_BODY = re.compile(
    r"IELTS\s+[\d.]+\s+overall\s+with\s+no\s+element\s+below\s+[\d.]+",
    re.I,
)


def _format_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _course_title(body: str) -> str:
    for line in body.splitlines():
        if re.match(r"^#\s+[^#]", line):
            return line.lstrip("#").strip()
    return ""


def _course_has_ielts(body: str) -> bool:
    if _IELTS_IN_BODY.search(body):
        return True
    return bool(re.search(r"\*\*IELTS:\*\*", body, re.I))


def _ielts_line_for_body(program: dict) -> str:
    for test in program.get("TestRequirements") or []:
        if not isinstance(test, dict):
            continue
        if "ielts" not in str(test.get("TestName", "")).casefold():
            continue
        overall = str(test.get("ieltsMinOverall", "") or "").strip()
        section = str(test.get("ieltsMinSection", "") or "").strip()
        if overall and section:
            return f"IELTS {overall} overall with no element below {section}"
        if overall:
            return f"IELTS {overall} overall"
    return ""


def _upsert_normalized_bullets(body: str, new_bullets: list[str]) -> str:
    if _NORMALIZED not in body:
        return body
    head, rest = body.split(_NORMALIZED, 1)
    end = re.search(r"\r?\n##\s", rest)
    section = rest[: end.start()] if end else rest
    tail = rest[end.start() :] if end else ""

    existing = [ln for ln in section.splitlines() if ln.strip().startswith("- **")]
    labels = {re.match(r"-\s*\*\*([^:*]+):", ln.strip(), re.I).group(1).casefold() for ln in existing if re.match(r"-\s*\*\*", ln.strip())}

    merged = list(existing)
    for bullet in new_bullets:
        label_match = re.match(r"-\s*\*\*([^:*]+):", bullet.strip(), re.I)
        if not label_match:
            continue
        label = label_match.group(1).casefold()
        if label in labels:
            merged = [
                bullet if re.match(r"-\s*\*\*([^:*]+):", ln.strip(), re.I)
                and re.match(r"-\s*\*\*([^:*]+):", ln.strip(), re.I).group(1).casefold() == label
                else ln
                for ln in merged
            ]
        else:
            merged.append(bullet)
            labels.add(label)

    block = "\n".join(merged) + "\n"
    return f"{head.rstrip()}\n\n{_NORMALIZED}\n\n{block}{tail.lstrip()}"


def _inject_ielts_sentence(body: str, ielts_line: str) -> str:
    if _IELTS_IN_BODY.search(body):
        return body
    if _NORMALIZED in body:
        head, tail = body.split(_NORMALIZED, 1)
        end = re.search(r"\r?\n##\s", tail)
        section_end = end.start() if end else len(tail)
        return (
            f"{head}{_NORMALIZED}{tail[:section_end].rstrip()}\n\n{ielts_line}\n{tail[section_end:]}"
        )
    return body.rstrip() + f"\n\n{ielts_line}\n"


def process_file(
    path: Path,
    programs: list[dict],
    *,
    dry_run: bool,
) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(raw)
    study_level = meta.get("study_level", path.parent.name)
    title = _course_title(body)
    program = match_english_program(
        programs,
        study_level=study_level,
        course_url=meta.get("course_url", ""),
        title=title,
    )
    if program is None:
        return False, "no_program_match"

    updates: list[str] = []
    new_bullets: list[str] = []

    duration = duration_display_from_program(program)
    if duration and not _DURATION_RE.search(body):
        new_bullets.append(f"- **Duration:** {duration}")
        updates.append(f"duration={duration}")

    ielts_line = ""
    if not _course_has_ielts(body):
        ielts_line = _ielts_line_for_body(program)
        if ielts_line:
            updates.append("ielts")

    if not new_bullets and not ielts_line:
        return False, "nothing_to_add"

    new_body = body
    if new_bullets:
        new_body = _upsert_normalized_bullets(new_body, new_bullets)
    if ielts_line:
        new_body = _inject_ielts_sentence(new_body, ielts_line)

    meta["english_program"] = str(program.get("ProgramName", ""))
    meta["cleaned_at"] = date.today().isoformat()
    output = _format_frontmatter(meta) + new_body.rstrip() + "\n"

    if not dry_run:
        path.write_text(output, encoding="utf-8")
    return True, ", ".join(updates)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--courses-dir",
        type=Path,
        default=_UNI_ROOT / "output" / "clean" / CLEAN_COURSES_SUBDIR,
    )
    parser.add_argument(
        "--english-md",
        type=Path,
        default=_UNI_ROOT / "output" / "clean" / "uni" / "english-requirements.md",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    programs = load_english_programs(args.english_md)
    updated = 0
    skipped = 0
    for path in sorted(args.courses_dir.rglob("*.md")):
        changed, reason = process_file(path, programs, dry_run=args.dry_run)
        if changed:
            updated += 1
            action = "would update" if args.dry_run else "updated"
            print(f"  {action} {path.relative_to(args.courses_dir)} ({reason})")
        else:
            skipped += 1

    suffix = " (dry run)" if args.dry_run else ""
    print(f"Done{suffix}: {updated} updated, {skipped} unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
