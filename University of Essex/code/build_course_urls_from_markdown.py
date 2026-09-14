#!/usr/bin/env python3
"""Build course_urls.csv and per-level CSVs from course markdown frontmatter."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

sys.path.insert(0, str(_REPO / "shared"))

from study_level import UrlLevelMap, write_level_csvs  # noqa: E402
from uni_pages import split_frontmatter  # noqa: E402

COURSE_URLS_CSV = "course_urls.csv"
_FOUNDATION_HEAD_RE = re.compile(
    r"(?:^|\n)#{1,4}\s*[^\n]*\(Including Foundation Year\)",
    re.I,
)
_ESSEX_CODE_RE = re.compile(r"/courses/(UG|PG|PR)", re.I)

SCOPE_BY_LEVEL = {
    "foundation": "FOUNDATION",
    "undergraduate": "UNDERGRADUATE",
    "postgraduate": "POSTGRADUATE",
    "postgraduate_research": "POSTGRADUATE_RESEARCH",
    "other": "OTHER",
}


def source_url_from_markdown(path: Path) -> str:
    meta, _body = split_frontmatter(path.read_text(encoding="utf-8"))
    url = (meta.get("source_url") or meta.get("course_url") or "").strip()
    if url:
        return url
    match = re.search(r"^source_url:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
    return match.group(1).strip() if match else ""


def is_foundation_course(body: str) -> bool:
    return bool(_FOUNDATION_HEAD_RE.search(body[:4000]))


def classify_essex(url: str, body: str) -> str:
    match = _ESSEX_CODE_RE.search(url)
    code = match.group(1).upper() if match else ""
    if code == "PR":
        return "postgraduate_research"
    if code == "PG":
        return "postgraduate"
    if code == "UG":
        if is_foundation_course(body):
            return "foundation"
        return "undergraduate"
    if is_foundation_course(body):
        return "foundation"
    return "other"


def classify_url(url: str, body: str, *, university: str) -> str:
    if "essex.ac.uk" in url.casefold() or university.casefold().startswith("university of essex"):
        return classify_essex(url, body)
    body_cf = body.casefold()
    if "postgraduate research course" in body_cf or re.search(r"/courses/pr", url, re.I):
        return "postgraduate_research"
    if "postgraduate course" in body_cf or re.search(r"/courses/pg", url, re.I):
        return "postgraduate"
    if is_foundation_course(body):
        return "foundation"
    if "undergraduate course" in body_cf or re.search(r"/courses/ug", url, re.I):
        return "undergraduate"
    return "other"


def collect_urls(courses_dir: Path, *, university: str) -> UrlLevelMap:
    url_levels = UrlLevelMap()
    missing: list[str] = []
    for path in sorted(courses_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        _meta, body = split_frontmatter(text)
        url = source_url_from_markdown(path)
        if not url:
            missing.append(path.name)
            continue
        level = classify_url(url, body, university=university)
        scope = SCOPE_BY_LEVEL.get(level, "OTHER")
        url_levels.add(url, level, scope)
    if missing:
        print(f"Warning: {len(missing)} markdown file(s) missing source_url", file=sys.stderr)
    return url_levels


def write_course_urls_csv(output_dir: Path, urls: list[str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / COURSE_URLS_CSV
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(["course_url"])
        for url in urls:
            writer.writerow([url])
    return path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build course_urls.csv and per-level CSVs from course markdown."
    )
    parser.add_argument(
        "--uni-dir",
        type=Path,
        default=_UNI_DIR,
        help="University folder (default: University of Essex)",
    )
    parser.add_argument(
        "--courses-dir",
        type=Path,
        default=None,
        help="Directory of course markdown files (default: <uni-dir>/output/clean/courses, else <uni-dir>/courses)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: <uni-dir>/output)",
    )
    args = parser.parse_args()

    uni_dir = args.uni_dir.resolve()
    if args.courses_dir:
        courses_dir = args.courses_dir.resolve()
    else:
        clean_courses = uni_dir / "output" / "clean" / "courses"
        legacy_courses = uni_dir / "courses"
        courses_dir = clean_courses if clean_courses.is_dir() else legacy_courses
    output_dir = (args.output_dir or uni_dir / "output").resolve()
    university = uni_dir.name

    if not courses_dir.is_dir():
        raise SystemExit(f"Courses directory not found: {courses_dir}")

    url_levels = collect_urls(courses_dir, university=university)
    urls = url_levels.urls()
    course_urls_path = write_course_urls_csv(output_dir, urls)
    write_level_csvs(output_dir, url_levels)

    print(f"University: {university}")
    print(f"Input: {courses_dir}")
    print(f"Wrote {len(urls)} unique URLs -> {course_urls_path}")
    for level in ("foundation", "undergraduate", "postgraduate", "postgraduate_research", "other"):
        count = sum(1 for record in url_levels.records() if record["study_level"] == level)
        if count:
            print(f"  {level}_course_urls.csv: {count}")


if __name__ == "__main__":
    main()
