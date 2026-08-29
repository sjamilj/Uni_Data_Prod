#!/usr/bin/env python3
"""Scan university folders on disk for pipeline dashboard status."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

SKIP_FOLDERS = frozenset({"shared", "dashboard", "_university_template"})
CLOUDFLARE_UNIS = frozenset(
    {
        "University of South Wales",
        "University of Wales Trinity Saint David",
        "University of West London",
    }
)
UNI_REQ_FILES = ("bangladesh-entry.html", "english-requirements.html", "scholarships.html")


def _status(done: bool, *, partial: bool = False, in_progress: bool = False) -> str:
    if done:
        return "done"
    if in_progress:
        return "in_progress"
    if partial:
        return "partial"
    return "not_started"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _count_csv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return sum(1 for _ in csv.DictReader(handle))
    except OSError:
        return 0


def _scrape_error(log_path: Path) -> bool:
    if not log_path.is_file():
        return False
    try:
        tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
    except OSError:
        return False
    return "[ERROR]" in tail or "[END] status=error" in tail


def _clean_source_urls(courses_dir: Path) -> set[str]:
    if not courses_dir.is_dir():
        return set()
    found: set[str] = set()
    from study_level import iter_course_markdown, normalize_url

    for md_path in iter_course_markdown(courses_dir):
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines()[:40]:
            if line.startswith("source_url:"):
                found.add(normalize_url(line.split(":", 1)[1].strip()))
                break
    return found


def detect_university_status(repo_root: Path, uni_dir: Path) -> dict:
    name = uni_dir.name
    output = uni_dir / "output"
    uni_req = uni_dir / "uni_req"
    if not uni_req.is_dir():
        uni_req = uni_dir / "code" / "uni_req"

    setup_files = sum(1 for filename in UNI_REQ_FILES if (uni_req / filename).is_file())
    setup = "done" if setup_files == len(UNI_REQ_FILES) else ("partial" if setup_files else "missing")

    course_urls_csv = output / "course_urls.csv"
    url_count = _count_csv_rows(course_urls_csv)
    progress = _read_json(output / "scrape_progress.json")
    phase = str(progress.get("phase") or "")
    urls_done = url_count > 0 and phase in {"urls_complete", "download_complete", "downloading"}
    urls = _status(urls_done, in_progress=phase == "extracting_urls" and url_count > 0)

    uni_md_dir = output / "clean" / "uni"
    uni_md_count = len(list(uni_md_dir.glob("*.md"))) if uni_md_dir.is_dir() else 0
    uni_clean = _status(uni_md_count >= 3, partial=0 < uni_md_count < 3)

    from study_level import (
        PRESETUP_CLEAN_SUBDIR,
        iter_course_markdown,
        iter_extracted_json,
        level_url_counts,
        load_presetup_sample,
        normalize_url,
        presetup_sample_urls,
    )

    courses_dir = output / "clean" / "courses"
    course_md = len(iter_course_markdown(courses_dir)) if courses_dir.is_dir() else 0
    presetup_dir = output / "clean" / PRESETUP_CLEAN_SUBDIR
    downloaded = len(progress.get("downloaded_urls") or [])
    download_target = url_count or len(progress.get("course_urls") or [])
    execute_selection = _read_json(output / "execute_selection.json")
    execute_urls = [
        str(item.get("course_url") or "")
        for item in (execute_selection.get("courses") or [])
        if isinstance(item, dict)
    ]
    if execute_urls:
        download_target = len(execute_urls)
    if course_md > 0 and (download_target == 0 or course_md >= download_target):
        download = "done"
    elif downloaded > 0 or course_md > 0:
        download = "partial" if course_md < download_target else "done"
    else:
        download = "not_started"

    sample = load_presetup_sample(output)
    sample_urls = presetup_sample_urls(sample)
    clean_urls = _clean_source_urls(presetup_dir) if sample_urls else set()
    sample_clean = sum(1 for url in sample_urls if normalize_url(url) in clean_urls)
    if sample_urls and sample_clean >= len(sample_urls):
        presetup = "done"
    elif sample_urls or sample_clean:
        presetup = "partial"
    else:
        presetup = "not_started"

    extract_progress = _read_json(output / "extracted" / "extraction_progress.json")
    llm_completed = len(extract_progress.get("completed") or [])
    llm_failed = len(extract_progress.get("failed") or [])
    llm_total = course_md
    if llm_total > 0 and llm_completed >= llm_total:
        llm = "done"
    elif llm_completed > 0 or llm_failed > 0:
        llm = "partial"
    elif llm_total > 0:
        llm = "not_started"
    else:
        llm = "missing"

    extracted_root = output / "extracted"
    output_json = iter_extracted_json(extracted_root, "output.json")
    normalized_json = iter_extracted_json(extracted_root, "normalized.json")
    if output_json and len(normalized_json) >= len(output_json):
        normalize = "done"
    elif normalized_json:
        normalize = "partial"
    elif output_json:
        normalize = "not_started"
    else:
        normalize = "missing"

    dev_csv = list(output.glob("dev_courses_*.csv"))
    csv_status = "done" if dev_csv else "not_started"

    return {
        "name": name,
        "path": str(uni_dir),
        "setup": setup,
        "urls": urls,
        "url_count": url_count,
        "uni_clean": uni_clean,
        "presetup": presetup,
        "presetup_clean": sample_clean,
        "presetup_total": len(sample_urls),
        "download": download,
        "course_md": course_md,
        "llm": llm,
        "llm_completed": llm_completed,
        "llm_failed": llm_failed,
        "llm_total": llm_total,
        "normalize": normalize,
        "csv": csv_status,
        "scrape_error": _scrape_error(output / "scrape.log"),
        "cloudflare": name in CLOUDFLARE_UNIS,
        "level_counts": level_url_counts(output) if url_count else {},
        "can_uni_clean": setup != "missing",
        "can_download": urls_done or url_count > 0,
        "can_presetup": url_count > 0,
        "can_presetup_llm": bool(sample_urls) and sample_clean > 0,
        "can_execute": url_count > 0,
        "can_llm": course_md > 0,
    }


def scan_all_universities(repo_root: Path) -> list[dict]:
    rows: list[dict] = []
    for entry in sorted(repo_root.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP_FOLDERS:
            continue
        if not (entry / "code" / "ENV.MD").is_file():
            continue
        rows.append(detect_university_status(repo_root, entry))
    return rows


def summarize(rows: list[dict]) -> dict:
    return {
        "universities": len(rows),
        "urls_done": sum(1 for row in rows if row["urls"] == "done"),
        "download_done": sum(1 for row in rows if row["download"] == "done"),
        "csv_done": sum(1 for row in rows if row["csv"] == "done"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan pipeline status for all universities.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root (default: parent of shared/)",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    args = parser.parse_args(argv)

    rows = scan_all_universities(args.repo_root.resolve())
    if args.json:
        print(json.dumps({"summary": summarize(rows), "universities": rows}, indent=2))
        return 0

    summary = summarize(rows)
    print(
        f"{summary['universities']} universities | "
        f"{summary['urls_done']} URLs done | "
        f"{summary['download_done']} download done | "
        f"{summary['csv_done']} CSV done"
    )
    for row in rows:
        print(
            f"{row['name']}: setup={row['setup']} urls={row['url_count']} "
            f"presetup={row['presetup_clean']}/{row['presetup_total'] or '-'} "
            f"download={row['course_md']}/{row['url_count'] or '-'} "
            f"llm={row['llm_completed']}/{row['llm_total'] or '-'} csv={row['csv']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
