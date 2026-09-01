#!/usr/bin/env python3
"""Move clean/courses/{level}/*.md into {level}/{intake year}/*.md subfolders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED_DIR.parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from study_level import (
    STUDY_LEVELS,
    clean_course_md_relative_path,
    intake_year_folder_from_stem,
    is_intake_year_folder,
    iter_course_markdown,
    study_level_folder_from_path,
)
from uni_paths import resolve_output_dir


class IntakeYearRetrofit:
    """Move course markdown into intake-year subfolders."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT

    def resolve_university_code_dir(self, name: str) -> Path:
        code_dir = self.repo_root / name / "code"
        if not code_dir.is_dir():
            raise FileNotFoundError(f"University code folder not found: {code_dir}")
        return code_dir

    def split_intake_years(self, output_dir: Path, *, dry_run: bool) -> tuple[int, int]:
        courses_dir = output_dir / "clean" / "courses"
        if not courses_dir.is_dir():
            return 0, 0

        moved = 0
        skipped = 0
        for md_path in iter_course_markdown(courses_dir):
            if is_intake_year_folder(md_path.parent.name):
                skipped += 1
                continue
            level = study_level_folder_from_path(md_path, courses_dir=courses_dir)
            if level not in STUDY_LEVELS:
                skipped += 1
                continue
            year_folder = intake_year_folder_from_stem(md_path.stem)
            if not year_folder:
                skipped += 1
                continue
            dest_dir = courses_dir / level / year_folder
            dest = dest_dir / md_path.name
            if dest.resolve() == md_path.resolve():
                skipped += 1
                continue
            if dest.exists() and dest.read_bytes() != md_path.read_bytes():
                raise FileExistsError(f"Conflict moving {md_path} -> {dest}")
            print(f"  {md_path.relative_to(output_dir)} -> {dest.relative_to(output_dir)}")
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    md_path.unlink()
                else:
                    md_path.replace(dest)
            moved += 1
        return moved, skipped

    def update_manifest(self, output_dir: Path, *, dry_run: bool) -> int:
        path = output_dir / "clean" / "manifest.json"
        if not path.exists():
            return 0
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        courses = manifest.get("courses")
        if not isinstance(courses, list):
            return 0
        updated = 0
        for entry in courses:
            if not isinstance(entry, dict):
                continue
            clean_md = (entry.get("clean_md") or "").strip()
            if not clean_md:
                continue
            slug = Path(clean_md).stem
            level = (entry.get("study_level") or study_level_folder_from_path(
                output_dir / clean_md, courses_dir=output_dir / "clean" / "courses"
            )).strip()
            if not level:
                continue
            new_path = clean_course_md_relative_path(level, slug)
            if entry.get("clean_md") != new_path:
                entry["clean_md"] = new_path
                updated += 1
        if updated and not dry_run:
            path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return updated

    def retrofit_university(self, name: str, *, dry_run: bool) -> None:
        code_dir = self.resolve_university_code_dir(name)
        output_dir = resolve_output_dir(code_dir)
        label = "DRY-RUN " if dry_run else ""
        print(f"\n=== {label}{name} ===")
        moved, skipped = self.split_intake_years(output_dir, dry_run=dry_run)
        print(f"  moved: {moved}, skipped: {skipped}")
        manifest_updates = self.update_manifest(output_dir, dry_run=dry_run)
        print(f"  manifest clean_md updates: {manifest_updates}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split clean/courses/{level}/*.md into intake-year subfolders"
    )
    parser.add_argument(
        "--university",
        required=True,
        help='University folder name, e.g. "Birmingham City University"',
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    IntakeYearRetrofit().retrofit_university(args.university, dry_run=args.dry_run)
    return 0


# Backward-compatible module-level aliases
resolve_university_code_dir = IntakeYearRetrofit().resolve_university_code_dir
split_intake_years = IntakeYearRetrofit().split_intake_years
update_manifest = IntakeYearRetrofit().update_manifest
retrofit_university = IntakeYearRetrofit().retrofit_university


if __name__ == "__main__":
    raise SystemExit(main())
