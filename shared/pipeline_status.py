#!/usr/bin/env python3
"""Scan university folders on disk for pipeline dashboard status."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


class PipelineStatusConfig:
    """Shared constants for pipeline status scanning."""

    SKIP_FOLDERS = frozenset({"shared", "dashboard", "_university_template"})
    CLOUDFLARE_UNIS = frozenset(
        {
            "University of South Wales",
            "University of Wales Trinity Saint David",
            "University of West London",
        }
    )
    UNI_REQ_FILES = ("bangladesh-entry.html", "english-requirements.html", "scholarships.html")


class StatusLabel:
    """Map boolean progress flags to dashboard status strings."""

    @staticmethod
    def from_flags(*, done: bool, partial: bool = False, in_progress: bool = False) -> str:
        if done:
            return "done"
        if in_progress:
            return "in_progress"
        if partial:
            return "partial"
        return "not_started"


class PipelineStatusIO:
    """Low-level file/CSV helpers for status detection."""

    @staticmethod
    def read_json(path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def count_csv_rows(path: Path) -> int:
        if not path.is_file():
            return 0
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                return sum(1 for _ in csv.DictReader(handle))
        except OSError:
            return 0

    @staticmethod
    def scrape_error(log_path: Path) -> bool:
        if not log_path.is_file():
            return False
        try:
            tail = log_path.read_text(encoding="utf-8", errors="replace")[-8000:]
        except OSError:
            return False
        return "[ERROR]" in tail or "[END] status=error" in tail

    @staticmethod
    def clean_source_urls(courses_dir: Path) -> set[str]:
        if not courses_dir.is_dir():
            return set()
        from study_level import iter_course_markdown, normalize_url

        found: set[str] = set()
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


class UniversityStatusDetector:
    """Detect pipeline phase status for one university folder."""

    def __init__(self, config: PipelineStatusConfig | None = None):
        self.config = config or PipelineStatusConfig()
        self.io = PipelineStatusIO()
        self.labels = StatusLabel()

    def detect(self, repo_root: Path, uni_dir: Path) -> dict:
        name = uni_dir.name
        output = uni_dir / "output"
        uni_req = uni_dir / "uni_req"
        if not uni_req.is_dir():
            uni_req = uni_dir / "code" / "uni_req"

        setup_files = sum(
            1 for filename in self.config.UNI_REQ_FILES if (uni_req / filename).is_file()
        )
        setup = (
            "done"
            if setup_files == len(self.config.UNI_REQ_FILES)
            else ("partial" if setup_files else "missing")
        )

        course_urls_csv = output / "course_urls.csv"
        url_count = self.io.count_csv_rows(course_urls_csv)
        progress = self.io.read_json(output / "scrape_progress.json")
        phase = str(progress.get("phase") or "")
        urls_done = url_count > 0 and phase in {"urls_complete", "download_complete", "downloading"}
        urls = self.labels.from_flags(
            done=urls_done,
            in_progress=phase == "extracting_urls" and url_count > 0,
        )

        uni_md_dir = output / "clean" / "uni"
        uni_md_count = len(list(uni_md_dir.glob("*.md"))) if uni_md_dir.is_dir() else 0
        uni_clean = self.labels.from_flags(done=uni_md_count >= 3, partial=0 < uni_md_count < 3)

        from study_level import (
            PRESETUP_CLEAN_SUBDIR,
            count_presetup_scrape_urls,
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
        execute_selection = self.io.read_json(output / "execute_selection.json")
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
        clean_urls = self.io.clean_source_urls(presetup_dir) if sample_urls else set()
        sample_clean = sum(1 for url in sample_urls if normalize_url(url) in clean_urls)
        if sample_urls and sample_clean >= len(sample_urls):
            presetup = "done"
        elif sample_urls or sample_clean:
            presetup = "partial"
        else:
            presetup = "not_started"

        extract_progress = self.io.read_json(output / "extracted" / "extraction_progress.json")
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

        presetup_scrape_count = count_presetup_scrape_urls(output)

        return {
            "name": name,
            "path": str(uni_dir),
            "setup": setup,
            "urls": urls,
            "url_count": url_count,
            "presetup_scrape_count": presetup_scrape_count,
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
            "scrape_error": self.io.scrape_error(output / "scrape.log"),
            "cloudflare": name in self.config.CLOUDFLARE_UNIS,
            "level_counts": level_url_counts(output) if url_count else {},
            "can_uni_clean": setup != "missing",
            "can_download": urls_done or url_count > 0,
            "can_presetup": url_count > 0 or presetup_scrape_count > 0,
            "can_presetup_llm": bool(sample_urls) and sample_clean > 0,
            "can_execute": url_count > 0,
            "can_llm": course_md > 0,
        }


class PipelineStatusScanner:
    """Scan all university folders under a repo root."""

    def __init__(self, config: PipelineStatusConfig | None = None):
        self.config = config or PipelineStatusConfig()
        self.detector = UniversityStatusDetector(self.config)

    def scan_all(self, repo_root: Path) -> list[dict]:
        rows: list[dict] = []
        for entry in sorted(repo_root.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name in self.config.SKIP_FOLDERS:
                continue
            if not (entry / "code" / "ENV.MD").is_file():
                continue
            rows.append(self.detector.detect(repo_root, entry))
        return rows

    @staticmethod
    def summarize(rows: list[dict]) -> dict:
        return {
            "universities": len(rows),
            "urls_done": sum(1 for row in rows if row["urls"] == "done"),
            "download_done": sum(1 for row in rows if row["download"] == "done"),
            "csv_done": sum(1 for row in rows if row["csv"] == "done"),
        }


class PipelineStatusCLI:
    """Command-line entry point for pipeline status scanning."""

    @staticmethod
    def build_arg_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="Scan pipeline status for all universities.")
        parser.add_argument(
            "--repo-root",
            type=Path,
            default=Path(__file__).resolve().parents[1],
            help="Repository root (default: parent of shared/)",
        )
        parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
        return parser

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = cls.build_arg_parser().parse_args(argv)
        scanner = PipelineStatusScanner()
        rows = scanner.scan_all(args.repo_root.resolve())
        if args.json:
            print(json.dumps({"summary": scanner.summarize(rows), "universities": rows}, indent=2))
            return 0

        summary = scanner.summarize(rows)
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


# Backward-compatible module-level aliases
SKIP_FOLDERS = PipelineStatusConfig.SKIP_FOLDERS
CLOUDFLARE_UNIS = PipelineStatusConfig.CLOUDFLARE_UNIS
UNI_REQ_FILES = PipelineStatusConfig.UNI_REQ_FILES
_status = StatusLabel.from_flags
_read_json = PipelineStatusIO.read_json
_count_csv_rows = PipelineStatusIO.count_csv_rows
_scrape_error = PipelineStatusIO.scrape_error
_clean_source_urls = PipelineStatusIO.clean_source_urls
detect_university_status = UniversityStatusDetector().detect
scan_all_universities = PipelineStatusScanner().scan_all
summarize = PipelineStatusScanner.summarize
main = PipelineStatusCLI.main


if __name__ == "__main__":
    raise SystemExit(PipelineStatusCLI.main())
