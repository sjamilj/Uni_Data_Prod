#!/usr/bin/env python3
"""Inject Kaplan International College IELTS (Spring 2027 PDF) into foundation course markdown."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]
_SHARED = _REPO / "shared"

if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from inject_english_requirements_md import (
    ENGLISH_SUBSECTION_RE,
    MAPPED_BLOCK_RE,
    inject_english_requirements_into_markdown,
    load_foundation_year_english_program,
    merge_foundation_pte_toefl_preserving_ielts,
    normalize_english_requirements_payload,
)
from uni_pages import split_frontmatter
from uni_paths import resolve_output_dir

SCRIPT_DIR = _CODE_DIR
DRY_RUN_MODULE = SCRIPT_DIR / "dry_run_essex_foundation_pathway_map.py"
DEFAULT_FOUND_DIR = (
    _UNI_DIR / "output"
    / "clean"
    / "courses"
    / "foundation"
)
DEFAULT_REPORT = (
    _UNI_DIR / "output"
    / "foundation_kaplan_ielts_report.json"
)

IELTS_LINE_RE = re.compile(r"IELTS\s+[\d.]+\s+overall[^\n]*", re.I)


def load_pathway_module():
    spec = importlib.util.spec_from_file_location("essex_foundation_pathway_map", DRY_RUN_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {DRY_RUN_MODULE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_kaplan_english_json(
    *,
    pathway: str,
    overall: str,
    min_section: str,
    pathway_mod,
    foundation_program: dict[str, object] | None = None,
) -> dict[str, object]:
    description = pathway_mod.format_kaplan_ielts_bullet(overall, min_section)
    base = normalize_english_requirements_payload(
        {
            "AcademicRequirementsMetaData": [
                {
                    "subtitle": "English Requirement",
                    "description": [
                        description,
                        f"Kaplan pathway: {pathway}",
                        pathway_mod.KAPLAN_IELTS_SOURCE,
                    ],
                }
            ],
            "ieltsMinOverall": overall,
            "ieltsMinSection": min_section,
        }
    )
    if foundation_program:
        return merge_foundation_pte_toefl_preserving_ielts(base, foundation_program)
    return base


def inject_kaplan_ielts(
    body: str,
    *,
    english_json: dict[str, object],
    pathway_mod,
) -> tuple[str, bool]:
    overall = str(english_json.get("ieltsMinOverall", "") or "")
    min_section = str(english_json.get("ieltsMinSection", "") or "")
    match = ENGLISH_SUBSECTION_RE.search(body)
    if not match:
        return body, False

    heading = match.group(1)
    section_body = MAPPED_BLOCK_RE.sub("", match.group(2)).rstrip()
    prose = pathway_mod.format_kaplan_ielts_prose(overall, min_section)

    if IELTS_LINE_RE.search(section_body):
        section_body = IELTS_LINE_RE.sub(prose, section_body, count=1)
    else:
        section_body = f"{section_body.rstrip()}\n\n{prose}"

    interim = body[: match.start()] + f"{heading}{section_body}\n\n" + body[match.end() :]
    return inject_english_requirements_into_markdown(interim, english_json)


def run(
    foundation_dir: Path,
    *,
    dry_run: bool = True,
    report_path: Path | None = None,
) -> int:
    pathway_mod = load_pathway_module()
    output_dir = resolve_output_dir(_CODE_DIR)
    foundation_program = load_foundation_year_english_program(output_dir)
    rows: list[dict] = []
    updated = 0
    skipped = 0

    for md_path in sorted(foundation_dir.glob("*.md")):
        title = pathway_mod.course_title(md_path)
        pathways, _, _ = pathway_mod.match_pathways(title)
        pathway = pathway_mod.ielts_pathway_for_foundation_course(pathways)
        ielts = pathway_mod.kaplan_ielts_for_pathway(pathway) if pathway else None

        if not ielts:
            skipped += 1
            rows.append(
                {
                    "file": md_path.name,
                    "title": title,
                    "status": "skipped_no_pathway",
                    "pathway": pathway,
                }
            )
            continue

        overall, min_section = ielts
        raw = md_path.read_text(encoding="utf-8")
        _, body = split_frontmatter(raw)
        english_json = build_kaplan_english_json(
            pathway=pathway,
            overall=overall,
            min_section=min_section,
            pathway_mod=pathway_mod,
            foundation_program=foundation_program,
        )
        new_body, changed = inject_kaplan_ielts(
            body,
            english_json=english_json,
            pathway_mod=pathway_mod,
        )
        if not changed:
            skipped += 1
            rows.append(
                {
                    "file": md_path.name,
                    "title": title,
                    "status": "skipped_no_english_section",
                    "pathway": pathway,
                    "ieltsOverall": overall,
                    "ieltsMinSection": min_section,
                }
            )
            continue

        if not dry_run:
            parts = raw.split("---", 2)
            prefix = f"---{parts[1]}---\n" if raw.startswith("---") and len(parts) >= 3 else ""
            md_path.write_text(prefix + new_body, encoding="utf-8")

        updated += 1
        rows.append(
            {
                "file": md_path.name,
                "title": title,
                "status": "would_inject" if dry_run else "injected",
                "pathway": pathway,
                "ieltsOverall": overall,
                "ieltsMinSection": min_section,
            }
        )

    print("=== Essex foundation Kaplan IELTS inject ===")
    print(f"Directory: {foundation_dir}")
    print(f"Updated: {updated} | Skipped: {skipped} | Dry run: {dry_run}")
    print()
    for row in rows:
        ielts = ""
        if row.get("ieltsOverall"):
            ielts = f" | IELTS {row['ieltsOverall']}/{row['ieltsMinSection']}"
        print(f"{row['status']:24} | {row['file']} | {row.get('pathway', '-')}{ielts}")

    payload = {
        "dryRun": dry_run,
        "updated": updated,
        "skipped": skipped,
        "source": pathway_mod.KAPLAN_IELTS_SOURCE,
        "courses": rows,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print()
        print(f"Wrote report: {report_path}")

    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation-dir", type=Path, default=DEFAULT_FOUND_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true", help="Write changes to markdown files")
    args = parser.parse_args()
    return run(args.foundation_dir, dry_run=not args.apply, report_path=args.report)


if __name__ == "__main__":
    raise SystemExit(main())
