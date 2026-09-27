#!/usr/bin/env python3
"""Pick one non-excluded course URL per university for dashboard E2E (writes e2e_course_pins.json)."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SHARED = REPO_ROOT / "shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from course_type_filter import CourseTypeFilter  # noqa: E402
from study_level import LEVEL_CSV_NAMES  # noqa: E402

LEVEL_ORDER = (
    "undergraduate",
    "postgraduate",
    "foundation",
    "postgraduate_research",
)
SKIP_FOLDERS = frozenset({"shared", "dashboard", "_university_template"})


def _read_urls_from_csv(path: Path) -> list[str]:
    if not path.is_file():
        return []
    urls: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or row.get("url") or "").strip()
            if url:
                urls.append(url)
    return urls


def _pick_url(uni_dir: Path, *, preferred_levels: list[str]) -> dict | None:
    code_dir = uni_dir / "code"
    if not (code_dir / "ENV.MD").is_file():
        return None
    output_dir = uni_dir / "output"
    filt = CourseTypeFilter.from_code_dir(code_dir)

    for level in preferred_levels:
        level_csv = output_dir / LEVEL_CSV_NAMES.get(level, f"{level}_course_urls.csv")
        urls = _read_urls_from_csv(level_csv)
        for url in urls:
            if filt.url_is_excluded(url):
                continue
            return {
                "study_level": level,
                "course_url": url,
                "source": level_csv.name,
            }

    catalogue = output_dir / "course_urls.csv"
    for url in _read_urls_from_csv(catalogue):
        if filt.url_is_excluded(url):
            continue
        return {
            "study_level": preferred_levels[0] if preferred_levels else "undergraduate",
            "course_url": url,
            "source": catalogue.name,
        }
    return None


def _slug_from_registry(repo: Path, folder: str) -> str:
    # Reuse dashboard registry parser when run from repo; avoid importing app package here.
    reg = repo / "UNIVERSITIES_REGISTRY.md"
    if not reg.is_file():
        return ""
    import re

    row = re.compile(
        r"^\|\s*(unit-\d{2})\s*\|\s*([a-z0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
    )
    for line in reg.read_text(encoding="utf-8").splitlines():
        match = row.match(line)
        if match and match.group(3).strip() == folder:
            return match.group(2).strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-calculate E2E course pins per university.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--uni", help="Single university folder name only")
    parser.add_argument(
        "--level",
        action="append",
        default=[],
        help="Preferred study level order (repeatable). Default: ug, pg, foundation, pgr",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output JSON (default dashboard/e2e_course_pins.json)")
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    levels = [s.strip().lower() for s in args.level] if args.level else list(LEVEL_ORDER)
    out_path = args.out or (repo / "dashboard" / "e2e_course_pins.json")

    existing: dict = {}
    if out_path.is_file():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
    pins: dict = dict(existing.get("pins") or {})

    uni_dirs: list[Path] = []
    if args.uni:
        uni_dirs = [repo / args.uni]
    else:
        for entry in sorted(repo.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_FOLDERS:
                continue
            if (entry / "code" / "ENV.MD").is_file():
                uni_dirs.append(entry)

    today = date.today().isoformat()
    picked = 0
    for uni_dir in uni_dirs:
        name = uni_dir.name
        choice = _pick_url(uni_dir, preferred_levels=levels)
        if not choice:
            print(f"SKIP {name}: no URL in output/*_course_urls.csv (run scrape first)", flush=True)
            continue
        pins[name] = {
            "slug": _slug_from_registry(repo, name),
            "study_level": choice["study_level"],
            "course_url": choice["course_url"],
            "source": choice["source"],
            "precalc_at": today,
        }
        picked += 1
        print(f"OK   {name} [{choice['study_level']}] {choice['course_url']}", flush=True)

    payload = {
        "description": "Pinned courses for dashboard step (5) Run Full Pipeline with One Course. Regenerate: python dashboard/precalc_e2e_pins.py",
        "pins": pins,
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {picked} pin(s) -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
