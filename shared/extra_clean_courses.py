#!/usr/bin/env python3
"""Manual second-pass cleanup for existing clean/courses/{level}/*.md.

Not part of the download/clean pipeline. Run after pipeline clean when pages
need folder-specific rules or a second pass.

Rules (in code/.env):
  EXTRA_CLEAN_REMOVE_SECTIONS              — all study-level folders
  EXTRA_CLEAN_REMOVE_SECTIONS_UNDERGRADUATE — foundation, undergraduate, etc.

Optional Python hook in {University}/code/course_markdown_cleanup.py:
  extra_clean_course_markdown_uni(markdown, *, study_level: str) -> str

Examples:
  python shared/extra_clean_courses.py --code-dir "Birmingham City University/code"
  python shared/extra_clean_courses.py --code-dir "Birmingham City University/code" --level foundation undergraduate
  python shared/extra_clean_courses.py --code-dir "Birmingham City University/code" --passes 2
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from course_markdown_cleanup import (
    CourseMarkdownCleaner,
    _format_frontmatter,
    _load_uni_course_cleanup_module,
    apply_env_remove_sections_for_key,
)
from scrape_course_urls import add_code_dir_argument
from study_level import (
    STUDY_LEVELS,
    folder_for_level,
    iter_course_markdown,
    relative_course_md,
    study_level_folder_from_path,
    study_level_from_markdown,
)
from uni_paths import resolve_code_dir, resolve_output_dir

_EXTRA_CLEAN_REMOVE_SECTIONS_KEY = "EXTRA_CLEAN_REMOVE_SECTIONS"


class ExtraCourseCleaner:
    """Manual second-pass cleanup for existing clean/courses/{level}/*.md."""

    EXTRA_CLEAN_REMOVE_SECTIONS_KEY = _EXTRA_CLEAN_REMOVE_SECTIONS_KEY

    @staticmethod
    def extra_clean_env_key_for_level(study_level: str) -> str:
        level = study_level.strip().upper().replace("-", "_")
        return f"{_EXTRA_CLEAN_REMOVE_SECTIONS_KEY}_{level}"

    def extra_clean_course_markdown(
        self,
        markdown: str,
        *,
        code_dir: Path,
        study_level: str,
    ) -> str:
        """Apply extra .env section rules, then optional per-uni Python hook."""
        cleaned = markdown
        code_dir = resolve_code_dir(code_dir)
        for env_key in (
            self.extra_clean_env_key_for_level(study_level),
            self.EXTRA_CLEAN_REMOVE_SECTIONS_KEY,
        ):
            cleaned = apply_env_remove_sections_for_key(cleaned, code_dir, env_key)

        module = _load_uni_course_cleanup_module(code_dir)
        if module is not None:
            extra = getattr(module, "extra_clean_course_markdown_uni", None)
            if callable(extra):
                cleaned = extra(cleaned, study_level=study_level)
        return cleaned

    @staticmethod
    def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
        return CourseMarkdownCleaner.parse_frontmatter(raw)

    def select_levels(self, courses_dir: Path, requested: list[str]) -> list[str]:
        if requested:
            return [folder_for_level(level) for level in requested]
        found = sorted(
            {
                study_level_folder_from_path(path, courses_dir=courses_dir)
                for path in iter_course_markdown(courses_dir)
                if path.parent != courses_dir
            }
        )
        return found or list(STUDY_LEVELS)

    def apply_to_dir(
        self,
        courses_dir: Path,
        code_dir: Path,
        *,
        levels: list[str],
        passes: int = 1,
        dry_run: bool = False,
    ) -> tuple[int, int]:
        if not courses_dir.is_dir():
            raise FileNotFoundError(f"Course markdown directory not found: {courses_dir}")

        selected = set(levels)
        updated = 0
        total = 0
        for path in iter_course_markdown(courses_dir):
            study_level = study_level_from_markdown(path, courses_dir=courses_dir)
            if study_level not in selected:
                continue

            total += 1
            raw = path.read_text(encoding="utf-8")
            meta, body = self.parse_frontmatter(raw)
            cleaned_body = body.rstrip("\n")
            for _ in range(max(1, passes)):
                cleaned_body = self.extra_clean_course_markdown(
                    cleaned_body,
                    code_dir=code_dir,
                    study_level=study_level,
                )

            meta["cleaned_at"] = date.today().isoformat()
            output = _format_frontmatter(meta) + cleaned_body + "\n"
            rel = relative_course_md(path, courses_dir)
            if output == raw:
                print(f"  unchanged {rel}")
                continue
            if dry_run:
                print(f"  would update {rel}")
            else:
                path.write_text(output, encoding="utf-8")
                print(f"  updated {rel}")
            updated += 1
        return updated, total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manual second-pass cleanup for output/clean/courses/{level}/*.md"
    )
    add_code_dir_argument(parser)
    parser.add_argument(
        "--level",
        action="append",
        default=[],
        metavar="LEVEL",
        nargs="+",
        help="Study-level folder(s) to clean (repeatable). Default: all folders found.",
    )
    parser.add_argument(
        "--passes",
        type=int,
        default=1,
        help="Number of cleanup passes per file (default: 1). Use 2 when rules interact.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report files that would change without writing.",
    )
    args = parser.parse_args(argv)

    cleaner = ExtraCourseCleaner()
    code_dir = resolve_code_dir(args.code_dir)
    courses_dir = resolve_output_dir(code_dir) / "clean" / "courses"
    levels = cleaner.select_levels(courses_dir, [level for group in args.level for level in group])
    if not levels:
        print("No study-level folders to clean.")
        return 1

    print(
        f"Extra-cleaning {courses_dir} "
        f"(levels: {', '.join(levels)}, passes: {args.passes})..."
    )
    updated, total = cleaner.apply_to_dir(
        courses_dir,
        code_dir,
        levels=levels,
        passes=args.passes,
        dry_run=args.dry_run,
    )
    action = "would update" if args.dry_run else "updated"
    print(f"Done: {updated}/{total} file(s) {action}")
    return 0


# Backward-compatible module-level aliases
extra_clean_env_key_for_level = ExtraCourseCleaner.extra_clean_env_key_for_level
extra_clean_course_markdown = ExtraCourseCleaner().extra_clean_course_markdown
_parse_frontmatter = ExtraCourseCleaner.parse_frontmatter
_select_levels = ExtraCourseCleaner().select_levels
apply_extra_clean_to_dir = ExtraCourseCleaner().apply_to_dir


if __name__ == "__main__":
    raise SystemExit(main())
