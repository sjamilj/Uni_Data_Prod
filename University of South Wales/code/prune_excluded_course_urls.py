#!/usr/bin/env python3
"""Drop course_urls.csv rows whose course_pages HTML matches COURSE_EXCLUDE_HTML_CONTAINS."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_type_filter import CourseTypeFilter


def _code_dir() -> Path:
    return Path(__file__).resolve().parent


def _canonical_url_from_html(html: str) -> str | None:
    for pattern in (
        r'property="og:url"\s+content="([^"]+)"',
        r'<link rel="canonical"\s+href="([^"]+)"',
    ):
        match = re.search(pattern, html, re.I)
        if match:
            return match.group(1).strip().rstrip("/")
    return None


def main() -> int:
    code_dir = _code_dir()
    output_dir = code_dir.parent / "output"
    csv_path = output_dir / "course_urls.csv"
    pages_dir = output_dir / "course_pages"
    log_path = output_dir / "excluded_course_urls.txt"

    if not csv_path.is_file():
        print(f"Missing {csv_path}", file=sys.stderr)
        return 1

    course_filter = CourseTypeFilter.from_code_dir(code_dir)
    excluded_urls: set[str] = set()
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            url = line.strip().rstrip("/")
            if url:
                excluded_urls.add(url)
    if pages_dir.is_dir():
        for path in pages_dir.glob("*.html"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if not course_filter.html_is_excluded(text):
                continue
            url = _canonical_url_from_html(text)
            if url:
                excluded_urls.add(url.rstrip("/"))

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    kept = [
        row
        for row in rows
        if row.get("course_url", "").strip().rstrip("/") not in excluded_urls
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["course_url"])
        writer.writeheader()
        writer.writerows(kept)

    removed = len(rows) - len(kept)
    print(f"Removed {removed} URL(s) from {csv_path}")
    for url in sorted(excluded_urls):
        print(f"  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
