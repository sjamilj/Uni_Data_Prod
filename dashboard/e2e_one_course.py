#!/usr/bin/env python3
"""Dashboard-only: pinned or presetup URL → download/clean → LLM → normalize → export.

Uses existing shared CLIs. Pin file: dashboard/e2e_course_pins.json (see precalc_e2e_pins.py).
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

if str((Path(__file__).resolve().parent.parent / "shared")) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))

from study_level import normalize_url  # noqa: E402

DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
SHARED = REPO_ROOT / "shared"
PRESETUP_URLS_CSV = "presetup_urls.csv"
DEFAULT_PINS_FILE = "e2e_course_pins.json"


def _run(command: list[str], *, cwd: Path) -> int:
    print("==>", " ".join(command), flush=True)
    return subprocess.run(command, cwd=str(cwd)).returncode


def _load_pin(repo_root: Path, folder_name: str, pins_file: str) -> dict | None:
    path = repo_root / "dashboard" / pins_file
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pin = (data.get("pins") or {}).get(folder_name)
    return pin if isinstance(pin, dict) and pin.get("course_url") else None


def _read_presetup_urls(output_dir: Path, study_levels: list[str]) -> list[dict[str, str]]:
    path = output_dir / PRESETUP_URLS_CSV
    if not path.is_file():
        return []
    allowed = set(study_levels) if study_levels else None
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or row.get("url") or "").strip()
            level = (row.get("study_level") or "").strip()
            if not url:
                continue
            if allowed is not None and level not in allowed:
                continue
            rows.append({"course_url": url, "study_level": level})
    return rows


def _resolve_clean_md_rel(output_dir: Path, url: str, study_level: str) -> str:
    """Path under clean/courses/ matching courses.csv md_file (for llm_extract --md-file)."""
    courses_dir = output_dir / "clean" / "courses"
    if not courses_dir.is_dir():
        return ""
    target = normalize_url(url)
    newest_rel = ""
    newest_mtime = 0.0
    for md_path in courses_dir.rglob("*.md"):
        rel = md_path.relative_to(courses_dir).as_posix()
        parts = md_path.relative_to(courses_dir).parts
        if parts and parts[0] != study_level:
            continue
        mtime = md_path.stat().st_mtime
        if mtime > newest_mtime:
            newest_mtime = mtime
            newest_rel = rel
        try:
            head = md_path.read_text(encoding="utf-8", errors="replace")[:5000]
        except OSError:
            continue
        for line in head.splitlines()[:50]:
            if not line.startswith(("source_url:", "course_url:")):
                continue
            if normalize_url(line.split(":", 1)[1].strip()) == target:
                return rel
    return newest_rel


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E smoke: one course through full pipeline.")
    parser.add_argument("--code-dir", required=True, help="University code/ folder")
    parser.add_argument(
        "--study-level",
        action="append",
        default=[],
        metavar="LEVEL",
        help="foundation, undergraduate, postgraduate, postgraduate_research",
    )
    parser.add_argument("--fresh", action="store_true", help="Re-download HTML (and presetup scrape if no pin)")
    parser.add_argument("--resume", action="store_true", help="Skip LLM if already extracted")
    parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Ignore e2e_course_pins.json and presetup-scrape 1 random URL",
    )
    parser.add_argument(
        "--pins-file",
        default=DEFAULT_PINS_FILE,
        help="JSON file under dashboard/ (default e2e_course_pins.json)",
    )
    args = parser.parse_args()

    code_dir = Path(args.code_dir).resolve()
    output_dir = code_dir.parent / "output"
    folder_name = code_dir.parent.name
    study_levels = [s.strip().lower() for s in args.study_level if s.strip()]

    pin = None if args.force_scrape else _load_pin(REPO_ROOT, folder_name, args.pins_file)
    url = ""
    level = ""

    if pin:
        url = str(pin["course_url"]).strip()
        level = str(pin.get("study_level") or "undergraduate").strip().lower()
        if study_levels and level not in study_levels:
            print(
                f"Warning: pin study_level={level} not in --study-level {study_levels}; using pin level.",
                flush=True,
            )
        if not study_levels:
            study_levels = [level]
        print(f"E2E pinned course: [{level}] {url}", flush=True)
    else:
        if not study_levels:
            print(
                "Error: no pin in e2e_course_pins.json — pass --study-level or run "
                "python dashboard/precalc_e2e_pins.py after scrape.",
                file=sys.stderr,
            )
            return 1

        py = sys.executable or "python"
        scrape_cmd = [
            py,
            "-u",
            str(SHARED / "scrape_course_urls.py"),
            "--code-dir",
            str(code_dir),
            "--presetup",
            "--presetup-per-level",
            "1",
        ]
        if args.fresh:
            scrape_cmd.append("--fresh")
        for lv in study_levels:
            scrape_cmd.extend(["--study-level", lv])

        if _run(scrape_cmd, cwd=REPO_ROOT) != 0:
            return 1

        courses = _read_presetup_urls(output_dir, study_levels)
        if not courses:
            print(f"Error: no rows in {output_dir / PRESETUP_URLS_CSV}", file=sys.stderr)
            return 1
        course = courses[0]
        url = course["course_url"]
        level = course.get("study_level") or study_levels[0]
        print(f"E2E presetup course: [{level}] {url}", flush=True)

    py = sys.executable or "python"
    dl_cmd = [
        py,
        "-u",
        str(SHARED / "download_and_clean_course_pages.py"),
        "--code-dir",
        str(code_dir),
        "--url",
        url,
    ]
    dl_cmd.append("--fresh")
    if _run(dl_cmd, cwd=REPO_ROOT) != 0:
        return 1

    md_rel = _resolve_clean_md_rel(output_dir, url, level)
    if not md_rel:
        print("Error: could not find cleaned markdown for E2E URL.", file=sys.stderr)
        return 1
    print(f"E2E clean md: {md_rel}", flush=True)

    llm_cmd = [py, "-u", str(SHARED / "llm_extract.py"), str(code_dir), "--md-file", md_rel]
    if args.resume:
        llm_cmd.append("--resume")
    if _run(llm_cmd, cwd=REPO_ROOT) != 0:
        return 1

    for script in ("normalize_admission_data.py", "export_dev_courses.py"):
        if _run([py, "-u", str(SHARED / script), str(code_dir)], cwd=REPO_ROOT) != 0:
            return 1

    print("E2E one course complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
