#!/usr/bin/env python3
"""Add Essex Foundation Year PTE/TOEFL to foundation course JSON blocks (keep Kaplan IELTS)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]
_SHARED = _REPO / "shared"

if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from inject_english_requirements_md import (
    inject_english_requirements_into_markdown,
    load_foundation_year_english_program,
    merge_foundation_pte_toefl_preserving_ielts,
)
from llm_extract import Stage2Enricher
from uni_pages import split_frontmatter
from uni_paths import resolve_code_dir, resolve_output_dir

DEFAULT_FOUND_DIR = (
    _UNI_DIR / "output"
    / "clean"
    / "courses"
    / "foundation"
)
DEFAULT_REPORT = (
    _UNI_DIR / "output"
    / "foundation_pte_toefl_report.json"
)


def run(
    foundation_dir: Path,
    output_dir: Path,
    *,
    dry_run: bool = True,
    report_path: Path | None = None,
) -> int:
    program = load_foundation_year_english_program(output_dir)
    if not program:
        print("Error: Foundation Year entry program not found in english-requirements.md", file=sys.stderr)
        return 1

    rows: list[dict] = []
    updated = 0
    skipped = 0

    for md_path in sorted(foundation_dir.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        _, body = split_frontmatter(raw)
        existing = Stage2Enricher.parse_course_english_mapped_json(body)
        if not existing:
            skipped += 1
            rows.append({"file": md_path.name, "status": "skipped_no_json"})
            continue

        merged = merge_foundation_pte_toefl_preserving_ielts(existing, program)
        new_body, changed = inject_english_requirements_into_markdown(body, merged)
        if not changed:
            skipped += 1
            rows.append({"file": md_path.name, "status": "skipped_no_english_section"})
            continue

        if not dry_run:
            parts = raw.split("---", 2)
            prefix = f"---{parts[1]}---\n" if raw.startswith("---") and len(parts) >= 3 else ""
            md_path.write_text(prefix + new_body, encoding="utf-8")

        updated += 1
        rows.append(
            {
                "file": md_path.name,
                "status": "would_update" if dry_run else "updated",
                "ieltsMinOverall": merged.get("ieltsMinOverall", ""),
                "ieltsMinSection": merged.get("ieltsMinSection", ""),
                "pteMinOverall": merged.get("pteMinOverall", ""),
                "pteMinSection": merged.get("pteMinSection", ""),
                "toeflMinOverall": merged.get("toeflMinOverall", ""),
                "toeflMinSection": merged.get("toeflMinSection", ""),
            }
        )

    print("=== Essex foundation PTE/TOEFL merge (IELTS unchanged) ===")
    print("Source: english-requirements.md -> Foundation Year entry")
    print(f"PTE: {program.get('TestRequirements', [{}])[1] if len(program.get('TestRequirements', [])) > 1 else 'n/a'}")
    print(f"Updated: {updated} | Skipped: {skipped} | Dry run: {dry_run}")
    print()
    for row in rows:
        if row["status"].startswith("skipped"):
            print(f"{row['status']:28} | {row['file']}")
        else:
            print(
                f"{row['status']:28} | {row['file']} | "
                f"IELTS {row['ieltsMinOverall']}/{row['ieltsMinSection']} | "
                f"PTE {row['pteMinOverall']}/{row['pteMinSection']} | "
                f"TOEFL {row['toeflMinOverall']}/{row['toeflMinSection']}"
            )

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"dryRun": dry_run, "updated": updated, "skipped": skipped, "courses": rows}, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"Wrote report: {report_path}")

    return 0 if skipped == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-dir", type=Path, default=_CODE_DIR)
    parser.add_argument("--foundation-dir", type=Path, default=DEFAULT_FOUND_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    code_dir = resolve_code_dir(args.code_dir)
    output_dir = resolve_output_dir(code_dir)
    foundation_dir = args.foundation_dir
    return run(foundation_dir, output_dir, dry_run=not args.apply, report_path=args.report)


if __name__ == "__main__":
    raise SystemExit(main())
