#!/usr/bin/env python3
"""One-off retrofit: split existing Aston / ARU artifacts by study level.

Does not re-scrape or re-run the LLM. Classifies URLs already in course_urls.csv
with StudyLevelClassifier (.env *_URL_PATTERNS), then:

  1. Writes undergraduate / postgraduate / research / foundation CSVs and
     scrape_progress.json url_levels
  2. Moves clean/courses/*.md into clean/courses/{level}/{slug}.md
     (one canonical file per URL; slug.md wins over slug-2.md)
  3. Moves extracted/{slug}/ into extracted/{level}/{slug}/
  4. Rewrites extraction_progress.json keys to {level}::{slug}
  5. Rebuilds courses.csv

ARU caveats:
  - Foundation listings reuse /study/undergraduate/ URLs. Without persisted
    listing scopes, only paths matching FOUNDATION_URL_PATTERNS become
    foundation. Dual-listed UG+foundation URLs are tagged undergraduate only.
  - Research pages usually live under /study/postgraduate/*-research; this
    script retags that suffix as postgraduate_research.

Run from repo root:
  python shared/retrofit_study_level_split.py
  python shared/retrofit_study_level_split.py --university "Aston University"
  python shared/retrofit_study_level_split.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

_SHARED_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED_DIR.parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from scrape_course_urls import COURSE_URLS_CSV, ProgressStore
from study_level import (
    LEVEL_CSV_NAMES,
    STUDY_LEVELS,
    StudyLevelClassifier,
    UrlLevelMap,
    clean_course_md_relative_path,
    extraction_resume_key,
    folder_for_level,
    levels_for_url,
    write_level_csvs,
)
from uni_pages import course_slug_from_url, split_frontmatter
from uni_paths import resolve_output_dir

DEFAULT_UNIVERSITIES = (
    "Aston University",
    "Anglia Ruskin University - ARU",
)

PROGRESS_FILENAMES = (
    "extraction_progress.json",
    "entry_rerun_progress.json",
)

_ARU_RESEARCH_SUFFIX_RE = re.compile(r"(?:-research|/research)$", re.I)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve_university_code_dir(name: str) -> Path:
    folder = _REPO_ROOT / name
    code_dir = folder / "code"
    if not code_dir.is_dir():
        raise FileNotFoundError(f"University code folder not found: {code_dir}")
    return code_dir


def read_course_urls(output_dir: Path) -> list[str]:
    path = output_dir / COURSE_URLS_CSV
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    urls: list[str] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or row.get("url") or "").strip()
            if not url:
                for value in row.values():
                    candidate = (value or "").strip()
                    if candidate.startswith("http"):
                        url = candidate
                        break
            if url:
                urls.append(url)
    return urls


def is_aru(university_name: str) -> bool:
    lowered = university_name.lower()
    return "anglia ruskin" in lowered or "aru" in lowered


def apply_path_heuristics(university_name: str, url: str, level: str) -> str:
    if not is_aru(university_name):
        return level
    path = urlparse(url).path.rstrip("/")
    if level == "postgraduate" and _ARU_RESEARCH_SUFFIX_RE.search(path):
        return "postgraduate_research"
    return level


def levels_matching_url(url: str, url_levels: UrlLevelMap) -> list[str]:
    found = url_levels.levels_for(url)
    if found:
        return found
    path = urlparse(url).path.rstrip("/").lower()
    if not path:
        return []
    for mapped_url, levels in url_levels.levels.items():
        if urlparse(mapped_url).path.rstrip("/").lower() == path:
            return list(levels)
    return []


def classify_url_levels(
    urls: list[str],
    classifier: StudyLevelClassifier,
) -> UrlLevelMap:
    mapping = UrlLevelMap()
    mapping.tag_urls(urls, classifier=classifier, source_scope="ALL_COURSE")
    return mapping


def refine_university_levels(university_name: str, url_levels: UrlLevelMap) -> UrlLevelMap:
    """ARU research degrees share /study/postgraduate/ and end in -research."""
    refined = UrlLevelMap()
    for record in url_levels.records():
        level = apply_path_heuristics(
            university_name,
            record["course_url"],
            record["study_level"],
        )
        refined.add(record["course_url"], level, record["source_scope"])
    return refined


def primary_level_for_url(
    url: str,
    url_levels: UrlLevelMap,
    classifier: StudyLevelClassifier,
    university_name: str,
    *,
    course_name: str = "",
) -> str:
    found = levels_matching_url(url, url_levels)
    if not found:
        found = levels_for_url(
            url,
            url_levels=url_levels,
            classifier=classifier,
            course_name=course_name,
        )
    level = folder_for_level(found[0] if found else "undergraduate")
    return folder_for_level(apply_path_heuristics(university_name, url, level))


def upsert_study_level(text: str, study_level: str) -> str:
    if not text.startswith("---"):
        return f"---\nstudy_level: {study_level}\n---\n{text}"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return f"---\nstudy_level: {study_level}\n---\n{text}"
    frontmatter = parts[1]
    if re.search(r"(?m)^study_level:", frontmatter):
        frontmatter = re.sub(
            r"(?m)^study_level:.*$",
            f"study_level: {study_level}",
            frontmatter,
            count=1,
        )
    else:
        frontmatter = frontmatter.rstrip() + f"\nstudy_level: {study_level}\n"
    return f"---{frontmatter}---{parts[2]}"


def canonical_md_priority(md_name: str, course_url: str) -> tuple[int, int, str]:
    slug = course_slug_from_url(course_url)
    stem = Path(md_name).stem
    if stem == slug:
        return (0, 0, md_name.lower())
    match = re.fullmatch(re.escape(slug) + r"-(\d+)", stem)
    if match:
        return (1, int(match.group(1)), md_name.lower())
    return (2, 0, md_name.lower())


def url_from_extract_dir(extract_dir: Path) -> str:
    for name in ("output.json", "normalized.json", "stage1_parsed.json"):
        path = extract_dir / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        for key in ("courseUrl", "courseUrlExternal", "course_url"):
            value = (data.get(key) or "").strip()
            if value.startswith("http"):
                return value
    return ""


def split_urls(
    output_dir: Path,
    url_levels: UrlLevelMap,
    *,
    dry_run: bool,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for level in LEVEL_CSV_NAMES:
        counts[level] = sum(
            1 for record in url_levels.records() if record["study_level"] == level
        )
    if dry_run:
        return counts
    write_level_csvs(output_dir, url_levels)
    store = ProgressStore(output_dir)
    progress = store.load() or {}
    progress["url_levels"] = url_levels.to_progress()
    store.save(progress)
    return counts


def split_clean_courses(
    output_dir: Path,
    url_levels: UrlLevelMap,
    classifier: StudyLevelClassifier,
    university_name: str,
    *,
    dry_run: bool,
) -> dict[str, int]:
    courses_dir = output_dir / "clean" / "courses"
    stats = {
        "moved": 0,
        "kept_canonical": 0,
        "deleted_variants": 0,
        "already_nested": 0,
        "relocated": 0,
        "skipped_no_url": 0,
    }
    if not courses_dir.is_dir():
        return stats

    nested_existing = [
        path
        for path in courses_dir.rglob("*.md")
        if path.is_file() and path.parent != courses_dir
    ]
    stats["already_nested"] = len(nested_existing)

    for md_path in nested_existing:
        meta, _body = split_frontmatter(md_path.read_text(encoding="utf-8"))
        course_url = (meta.get("source_url") or "").strip().rstrip("/")
        if not course_url:
            continue
        level = primary_level_for_url(
            course_url, url_levels, classifier, university_name
        )
        dest = courses_dir / level / md_path.name
        if md_path.resolve() == dest.resolve() and meta.get("study_level") == level:
            continue
        stats["relocated"] += 1
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            upsert_study_level(md_path.read_text(encoding="utf-8"), level),
            encoding="utf-8",
        )
        if dest.resolve() != md_path.resolve():
            md_path.unlink(missing_ok=True)

    flat_files = sorted(
        path for path in courses_dir.glob("*.md") if path.is_file()
    )
    by_url: dict[str, dict] = {}
    for md_path in flat_files:
        meta, _body = split_frontmatter(md_path.read_text(encoding="utf-8"))
        course_url = (meta.get("source_url") or "").strip().rstrip("/")
        if not course_url:
            stats["skipped_no_url"] += 1
            continue
        record = by_url.setdefault(course_url, {"paths": [], "levels": []})
        record["paths"].append(md_path)
        level = primary_level_for_url(
            course_url, url_levels, classifier, university_name
        )
        if level not in record["levels"]:
            record["levels"].append(level)

    planned: list[tuple[str, Path, list[Path], list[Path]]] = []
    used_dests: set[Path] = set()
    for course_url, record in by_url.items():
        paths = record["paths"]
        canonical = min(paths, key=lambda path: canonical_md_priority(path.name, course_url))
        dests: list[Path] = []
        slug = course_slug_from_url(course_url)
        for level in record["levels"] or ["undergraduate"]:
            dest = courses_dir / level / f"{slug}.md"
            if dest in used_dests:
                dest = courses_dir / level / f"{canonical.stem}.md"
            used_dests.add(dest)
            dests.append(dest)
        planned.append((course_url, canonical, paths, dests))
        stats["kept_canonical"] += 1
        stats["deleted_variants"] += max(0, len(paths) - 1)

    stats["moved"] += sum(len(item[3]) for item in planned)
    if dry_run:
        return stats

    for course_url, canonical, paths, dests in planned:
        original = canonical.read_text(encoding="utf-8")
        written: set[Path] = set()
        for dest in dests:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(upsert_study_level(original, dest.parent.name), encoding="utf-8")
            written.add(dest.resolve())
        for extra in paths:
            if extra.resolve() not in written:
                extra.unlink(missing_ok=True)

    return stats


def build_slug_level_map(
    url_levels: UrlLevelMap,
    classifier: StudyLevelClassifier,
    extracted_dir: Path,
    university_name: str,
) -> dict[str, str]:
    slug_to_level: dict[str, str] = {}
    for record in url_levels.records():
        slug = course_slug_from_url(record["course_url"])
        slug_to_level[slug] = folder_for_level(record["study_level"])
    if not extracted_dir.is_dir():
        return slug_to_level
    for child in extracted_dir.iterdir():
        if not child.is_dir() or child.name in STUDY_LEVELS:
            continue
        if child.name in slug_to_level:
            continue
        url = url_from_extract_dir(child)
        if url:
            slug_to_level[child.name] = primary_level_for_url(
                url, url_levels, classifier, university_name
            )
        else:
            slug_to_level[child.name] = primary_level_for_url(
                child.name,
                url_levels,
                classifier,
                university_name,
                course_name=child.name,
            )
    return slug_to_level


def split_extracted(
    output_dir: Path,
    slug_to_level: dict[str, str],
    *,
    dry_run: bool,
) -> dict[str, int]:
    extracted_dir = output_dir / "extracted"
    stats = {"moved": 0, "already_nested": 0, "skipped": 0, "conflicts": 0}
    if not extracted_dir.is_dir():
        return stats

    for child in sorted(extracted_dir.iterdir()):
        if child.is_file():
            continue
        if child.name in STUDY_LEVELS:
            nested = sum(1 for path in child.iterdir() if path.is_dir())
            stats["already_nested"] += nested
            continue
        level = slug_to_level.get(child.name)
        if not level:
            stats["skipped"] += 1
            continue
        dest = extracted_dir / level / child.name
        if dest.exists():
            stats["conflicts"] += 1
            continue
        stats["moved"] += 1
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(child), str(dest))
    return stats


def rewrite_progress_keys(progress: dict, slug_to_level: dict[str, str]) -> dict:
    updated = dict(progress)

    def map_key(key: str) -> list[str]:
        raw = (key or "").strip()
        if not raw:
            return []
        if "::" in raw:
            return [raw]
        level = slug_to_level.get(raw)
        if not level:
            return [raw]
        return [extraction_resume_key(level, raw), raw]

    for field in ("completed", "failed"):
        values = progress.get(field)
        if not isinstance(values, list):
            continue
        seen: list[str] = []
        for key in values:
            for mapped in map_key(str(key)):
                if mapped not in seen:
                    seen.append(mapped)
        updated[field] = seen
    updated["updated_at"] = utc_now()
    return updated


def split_extract_progress(
    output_dir: Path,
    slug_to_level: dict[str, str],
    *,
    dry_run: bool,
) -> dict[str, int]:
    extracted_dir = output_dir / "extracted"
    stats = {"files": 0, "keys": 0}
    for name in PROGRESS_FILENAMES:
        path = extracted_dir / name
        if not path.exists():
            continue
        try:
            progress = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        rewritten = rewrite_progress_keys(progress, slug_to_level)
        stats["files"] += 1
        stats["keys"] += len(rewritten.get("completed", []) or [])
        if not dry_run:
            path.write_text(json.dumps(rewritten, indent=2), encoding="utf-8")
    return stats


def update_manifest(
    output_dir: Path,
    url_levels: UrlLevelMap,
    classifier: StudyLevelClassifier,
    university_name: str,
    *,
    dry_run: bool,
) -> int:
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
        url = (entry.get("source_url") or entry.get("course_url") or "").strip()
        if not url:
            continue
        level = primary_level_for_url(url, url_levels, classifier, university_name)
        slug = course_slug_from_url(url)
        entry["clean_md"] = clean_course_md_relative_path(level, slug)
        entry["study_level"] = level
        updated += 1
    if not dry_run:
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return updated


def rebuild_index(code_dir: Path, *, dry_run: bool) -> int:
    if dry_run:
        return 0
    from llm_extract import build_course_index

    index_path = build_course_index(code_dir)
    with index_path.open(newline="", encoding="utf-8-sig") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def retrofit_university(name: str, *, dry_run: bool) -> None:
    code_dir = resolve_university_code_dir(name)
    output_dir = resolve_output_dir(code_dir)
    classifier = StudyLevelClassifier.from_code_dir(code_dir)
    urls = read_course_urls(output_dir)
    url_levels = refine_university_levels(
        name,
        classify_url_levels(urls, classifier),
    )

    label = "DRY-RUN " if dry_run else ""
    print(f"\n=== {label}{name} ===")
    print(f"  unique URLs: {len(urls)}")

    url_counts = split_urls(output_dir, url_levels, dry_run=dry_run)
    for level, filename in LEVEL_CSV_NAMES.items():
        print(f"  {filename}: {url_counts.get(level, 0)}")

    clean_stats = split_clean_courses(
        output_dir,
        url_levels,
        classifier,
        name,
        dry_run=dry_run,
    )
    print(
        "  clean: "
        f"moved={clean_stats['moved']} variants_removed={clean_stats['deleted_variants']} "
        f"already_nested={clean_stats['already_nested']} "
        f"relocated={clean_stats['relocated']} "
        f"no_url={clean_stats['skipped_no_url']}"
    )

    extracted_dir = output_dir / "extracted"
    slug_to_level = build_slug_level_map(
        url_levels, classifier, extracted_dir, name
    )
    extract_stats = split_extracted(output_dir, slug_to_level, dry_run=dry_run)
    print(
        "  extracted: "
        f"moved={extract_stats['moved']} already_nested={extract_stats['already_nested']} "
        f"skipped={extract_stats['skipped']} conflicts={extract_stats['conflicts']}"
    )

    progress_stats = split_extract_progress(output_dir, slug_to_level, dry_run=dry_run)
    print(
        f"  progress files={progress_stats['files']} "
        f"completed_keys={progress_stats['keys']}"
    )

    manifest_n = update_manifest(
        output_dir,
        url_levels,
        classifier,
        name,
        dry_run=dry_run,
    )
    print(f"  manifest courses updated: {manifest_n}")

    index_n = rebuild_index(code_dir, dry_run=dry_run)
    if dry_run:
        print("  courses.csv: skipped (dry-run)")
    else:
        print(f"  courses.csv: {index_n} rows")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrofit existing Aston/ARU scrape+clean+extract output into study-level folders."
    )
    parser.add_argument(
        "--university",
        action="append",
        dest="universities",
        metavar="NAME",
        help="University folder name. Repeatable. Default: Aston and ARU.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = tuple(args.universities) if args.universities else DEFAULT_UNIVERSITIES
    for name in names:
        retrofit_university(name, dry_run=args.dry_run)
    return 0


class StudyLevelRetrofit:
    """One-off retrofit: split existing artifacts by study level."""

    DEFAULT_UNIVERSITIES = DEFAULT_UNIVERSITIES
    PROGRESS_FILENAMES = PROGRESS_FILENAMES
    ARU_RESEARCH_SUFFIX_RE = _ARU_RESEARCH_SUFFIX_RE

    utc_now = staticmethod(utc_now)
    resolve_university_code_dir = staticmethod(resolve_university_code_dir)
    read_course_urls = staticmethod(read_course_urls)
    is_aru = staticmethod(is_aru)
    apply_path_heuristics = staticmethod(apply_path_heuristics)
    levels_matching_url = staticmethod(levels_matching_url)
    classify_url_levels = staticmethod(classify_url_levels)
    refine_university_levels = staticmethod(refine_university_levels)
    primary_level_for_url = staticmethod(primary_level_for_url)
    upsert_study_level = staticmethod(upsert_study_level)
    canonical_md_priority = staticmethod(canonical_md_priority)
    url_from_extract_dir = staticmethod(url_from_extract_dir)
    split_urls = staticmethod(split_urls)
    split_clean_courses = staticmethod(split_clean_courses)
    build_slug_level_map = staticmethod(build_slug_level_map)
    split_extracted = staticmethod(split_extracted)
    rewrite_progress_keys = staticmethod(rewrite_progress_keys)
    split_extract_progress = staticmethod(split_extract_progress)
    update_manifest = staticmethod(update_manifest)
    rebuild_index = staticmethod(rebuild_index)
    retrofit_university = staticmethod(retrofit_university)


# Backward-compatible module-level aliases (functions above remain canonical)
if __name__ == "__main__":
    raise SystemExit(main())
