#!/usr/bin/env python3
"""Tag existing *_course_urls.csv rows with listing_intake_month (e.g. september before --append-urls january)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from study_level import (
    LEVEL_CSV_NAMES,
    normalize_listing_intake_month,
    read_level_csvs,
    write_level_csvs,
)
from uni_paths import resolve_code_dir, resolve_output_dir

PROGRESS_FILE = "scrape_progress.json"


def backfill(output_dir: Path, month: str, *, only_empty: bool = True) -> int:
    token = normalize_listing_intake_month(month)
    if not token:
        raise ValueError("month is required (e.g. september, january)")

    mapping = read_level_csvs(output_dir)
    if not mapping.levels:
        raise FileNotFoundError(
            f"No rows in {output_dir} level CSVs ({', '.join(LEVEL_CSV_NAMES.values())})"
        )

    updated = 0
    for url in sorted(mapping.levels):
        for level in sorted(mapping.levels[url]):
            key = (url, level)
            existing = mapping.listing_intakes.get(key) or []
            if only_empty and existing:
                continue
            if token not in existing:
                mapping.add(
                    url,
                    level,
                    mapping.levels[url][level],
                    listing_intake_month=token,
                )
                updated += 1

    write_level_csvs(output_dir, mapping)

    progress_path = output_dir / PROGRESS_FILE
    if progress_path.is_file():
        try:
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            progress = {}
        progress["url_levels"] = mapping.to_progress()
        progress["url_listing_intakes"] = mapping.listing_intakes_to_progress()
        if progress.get("phase") != "extracting_urls":
            progress["phase"] = "urls_complete"
        progress_path.write_text(
            json.dumps(progress, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Set listing_intake_month on existing per-level course URL CSVs "
            "(before a second scrape with --append-urls --listing-start-date …)."
        )
    )
    parser.add_argument("code_dir", type=Path, help='University code dir, e.g. "University of Hertfordshire/code"')
    parser.add_argument(
        "--month",
        default="september",
        help="Intake month token for rows missing listing_intake_month (default: september)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Add month even when listing_intake_month is already set",
    )
    args = parser.parse_args(argv)

    code_dir = resolve_code_dir(args.code_dir)
    output_dir = resolve_output_dir(code_dir)
    try:
        n = backfill(output_dir, args.month, only_empty=not args.force)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Backfilled listing_intake_month={normalize_listing_intake_month(args.month)} on {n} url/level pair(s)")
    print(f"Wrote {', '.join(LEVEL_CSV_NAMES.values())} under {output_dir}")
    if (output_dir / PROGRESS_FILE).is_file():
        print(f"Updated {PROGRESS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
