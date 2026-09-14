#!/usr/bin/env python3
"""Move University of Essex/courses into output/clean/courses/{level}/."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

sys.path.insert(0, str(_REPO / "shared"))
sys.path.insert(0, str(_CODE_DIR))

from build_course_urls_from_markdown import classify_url, source_url_from_markdown  # noqa: E402
from study_level import (  # noqa: E402
    clean_course_md_relative_path,
    folder_for_level,
    read_level_csvs,
)
from uni_pages import course_slug_from_url, split_frontmatter  # noqa: E402

UNI_DIR = _UNI_DIR
LEGACY_DIR = UNI_DIR / "courses"
OUTPUT_DIR = UNI_DIR / "output"
CLEAN_COURSES_DIR = OUTPUT_DIR / "clean" / "courses"


def format_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    if not LEGACY_DIR.is_dir():
        raise SystemExit(f"Legacy courses directory not found: {LEGACY_DIR}")

    url_levels = read_level_csvs(OUTPUT_DIR)
    CLEAN_COURSES_DIR.mkdir(parents=True, exist_ok=True)

    manifest_courses: list[dict[str, str]] = []
    moved = 0
    skipped = 0

    for src in sorted(LEGACY_DIR.glob("*.md")):
        raw = src.read_text(encoding="utf-8")
        meta, body = split_frontmatter(raw)
        source_url = (
            meta.get("source_url")
            or meta.get("course_url")
            or source_url_from_markdown(src)
        ).strip()
        if not source_url:
            print(f"  skip (no source_url): {src.name}")
            skipped += 1
            continue

        levels = url_levels.levels_for(source_url)
        study_level = levels[0] if levels else classify_url(
            source_url,
            body,
            university=UNI_DIR.name,
        )
        folder = folder_for_level(study_level)
        slug = course_slug_from_url(source_url)
        dest_dir = CLEAN_COURSES_DIR / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{slug}.md"

        meta["source_url"] = source_url
        meta["course_url"] = source_url
        meta["study_level"] = folder
        meta["university"] = meta.get("university") or "University of Essex"
        meta["page_type"] = meta.get("page_type") or "course"
        meta["cleaned_at"] = date.today().isoformat()

        output = format_frontmatter(meta) + body.rstrip("\n") + "\n"
        dest.write_text(output, encoding="utf-8")
        moved += 1

        clean_md = clean_course_md_relative_path(
            folder,
            slug,
            courses_subdir="courses",
        )
        manifest_courses.append(
            {
                "course_url": source_url,
                "source_html": meta.get("source_html", ""),
                "clean_md": clean_md,
                "source_url": source_url,
                "study_level": folder,
            }
        )

    manifest = {
        "university": "University of Essex",
        "cleaned_at": date.today().isoformat(),
        "courses": sorted(manifest_courses, key=lambda row: row["clean_md"]),
    }
    manifest_path = OUTPUT_DIR / "clean" / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if moved and skipped == 0:
        shutil.rmtree(LEGACY_DIR)

    print(f"Moved {moved} course markdown file(s) -> {CLEAN_COURSES_DIR}")
    if skipped:
        print(f"Skipped {skipped} file(s); legacy folder kept")
    print(f"Wrote manifest -> {manifest_path}")
    for level in ("foundation", "undergraduate", "postgraduate", "postgraduate_research", "other"):
        count = len(list((CLEAN_COURSES_DIR / level).glob("*.md"))) if (CLEAN_COURSES_DIR / level).is_dir() else 0
        if count:
            print(f"  {level}: {count}")


if __name__ == "__main__":
    main()
