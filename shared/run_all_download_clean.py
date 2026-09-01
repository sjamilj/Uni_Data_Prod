#!/usr/bin/env python3
"""Run download_and_clean_course_pages.py for every university, one by one.

Aston, ARU, and Birmingham City University are skipped by default (already done). Re-run with --resume after a
crash: universities listed in all_download_clean_progress.json are skipped, and
the current university resumes from scrape_progress.json downloaded_urls.

Examples (from repo root):
  python shared/run_all_download_clean.py --resume
  python shared/run_all_download_clean.py --resume --university "Keele University"
  python shared/run_all_download_clean.py --clean-only --resume
  python shared/run_all_download_clean.py --fresh
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED_DIR.parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

SKIP_FOLDERS = frozenset({"shared", "dashboard", "_university_template"})
DEFAULT_EXCLUDE = (
    "Aston University",
    "Anglia Ruskin University - ARU",
    "Birmingham City University",
)
PROGRESS_NAME = "all_download_clean_progress.json"
DOWNLOAD_SCRIPT = _SHARED_DIR / "download_and_clean_course_pages.py"


class BatchDownloadCleanRunner:
    """Batch download and clean course pages across all universities."""

    SKIP_FOLDERS = SKIP_FOLDERS
    DEFAULT_EXCLUDE = DEFAULT_EXCLUDE
    PROGRESS_NAME = PROGRESS_NAME
    DOWNLOAD_SCRIPT = DOWNLOAD_SCRIPT

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def progress_path(self) -> Path:
        return self.repo_root / self.PROGRESS_NAME

    def load_progress(self) -> dict:
        path = self.progress_path()
        if not path.exists():
            return {
                "completed": [],
                "failed": [],
                "skipped": [],
                "in_progress": "",
                "updated_at": "",
            }
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        data.setdefault("completed", [])
        data.setdefault("failed", [])
        data.setdefault("skipped", [])
        data.setdefault("in_progress", "")
        return data

    def save_progress(self, progress: dict) -> None:
        progress["updated_at"] = self.utc_now()
        self.progress_path().write_text(
            json.dumps(progress, indent=2),
            encoding="utf-8",
        )

    def discover_universities(self) -> list[Path]:
        found: list[Path] = []
        for entry in sorted(self.repo_root.iterdir(), key=lambda path: path.name.lower()):
            if not entry.is_dir() or entry.name.startswith(".") or entry.name in self.SKIP_FOLDERS:
                continue
            code_dir = entry / "code"
            if (code_dir / ".env").is_file() or (code_dir / "ENV.MD").is_file():
                found.append(entry)
        return found

    @staticmethod
    def count_course_urls(uni_dir: Path) -> int:
        path = uni_dir / "output" / "course_urls.csv"
        if not path.is_file():
            return 0
        try:
            lines = [
                line
                for line in path.read_text(encoding="utf-8-sig").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
        except OSError:
            return 0
        return max(0, len(lines) - 1)

    def build_command(
        self,
        code_dir: Path,
        *,
        fresh: bool,
        clean_only: bool,
        download_only: bool,
        limit: int,
    ) -> list[str]:
        command = [
            sys.executable,
            str(self.DOWNLOAD_SCRIPT),
            "--code-dir",
            str(code_dir),
        ]
        if fresh:
            command.append("--fresh")
        if clean_only:
            command.append("--clean-only")
        if download_only:
            command.append("--download-only")
        if limit > 0:
            command.extend(["--limit", str(limit)])
        return command

    def run(self, args: argparse.Namespace) -> int:
        if args.resume and args.fresh:
            print("Error: --resume and --fresh cannot be used together.", file=sys.stderr)
            return 1
        if args.clean_only and args.download_only:
            print("Error: --clean-only and --download-only cannot be used together.", file=sys.stderr)
            return 1
        if not self.DOWNLOAD_SCRIPT.is_file():
            print(f"Error: missing {self.DOWNLOAD_SCRIPT}", file=sys.stderr)
            return 1

        self.repo_root = args.repo_root.resolve()
        exclude = set() if args.include_done else set(self.DEFAULT_EXCLUDE)
        for name in args.skip or []:
            if name.strip():
                exclude.add(name.strip())

        only = {name.strip() for name in (args.universities or []) if name.strip()}
        progress = self.load_progress()
        completed = {str(name) for name in progress.get("completed", [])}

        targets: list[Path] = []
        skipped: list[tuple[str, str]] = []
        for uni_dir in self.discover_universities():
            name = uni_dir.name
            if only and name not in only:
                continue
            if name in exclude:
                skipped.append((name, "excluded (already done)"))
                continue
            if (
                args.resume
                and not args.clean_only
                and name in completed
                and name != progress.get("in_progress")
            ):
                skipped.append((name, "resume: already completed"))
                continue
            if not (uni_dir / "code").is_dir():
                skipped.append((name, "no code/ folder"))
                continue
            if self.count_course_urls(uni_dir) <= 0 and not args.clean_only:
                skipped.append((name, "no output/course_urls.csv — scrape first"))
                continue
            targets.append(uni_dir)

        print(f"Universities to process: {len(targets)}")
        for uni_dir in targets:
            urls = self.count_course_urls(uni_dir)
            print(f"  - {uni_dir.name} ({urls} URLs)")
        if skipped:
            print("Skipped:")
            for name, reason in skipped:
                print(f"  - {name}: {reason}")

        if args.dry_run:
            return 0
        if not targets:
            print("Nothing to run.")
            return 0

        progress.setdefault("skipped", [])
        for name, _reason in skipped:
            if name not in progress["skipped"]:
                progress["skipped"].append(name)
        self.save_progress(progress)

        failed: list[str] = []
        for index, uni_dir in enumerate(targets, start=1):
            name = uni_dir.name
            code_dir = uni_dir / "code"
            command = self.build_command(
                code_dir,
                fresh=args.fresh,
                clean_only=args.clean_only,
                download_only=args.download_only,
                limit=args.limit,
            )
            print()
            print("=" * 72)
            print(f"[{index}/{len(targets)}] {name}")
            if args.resume and not args.clean_only:
                print("Mode: RESUME (skips already-downloaded URLs in scrape_progress.json)")
            elif args.clean_only:
                print("Mode: CLEAN-ONLY (re-cleans all universities except excluded)")
            print(" ".join(command))

            progress["in_progress"] = name
            if name in progress.get("failed", []):
                progress["failed"] = [item for item in progress["failed"] if item != name]
            self.save_progress(progress)

            result = subprocess.run(command, cwd=str(self.repo_root))
            if result.returncode != 0:
                print(f"FAILED: {name} (exit {result.returncode})", file=sys.stderr)
                if name not in progress["failed"]:
                    progress["failed"].append(name)
                progress["in_progress"] = ""
                self.save_progress(progress)
                failed.append(name)
                if args.fail_fast:
                    return result.returncode or 1
                continue

            completed_list = [item for item in progress.get("completed", []) if item != name]
            completed_list.append(name)
            progress["completed"] = completed_list
            progress["failed"] = [item for item in progress.get("failed", []) if item != name]
            progress["in_progress"] = ""
            self.save_progress(progress)
            print(f"OK: {name}")

        print()
        if failed:
            print("Failed universities:")
            for name in failed:
                print(f"  - {name}")
            return 1
        print("All universities completed.")
        return 0


class BatchDownloadCleanCLI:
    """Command-line entry point for batch download/clean."""

    @staticmethod
    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description=(
                "Download and clean course pages for every university except Aston, ARU, and Birmingham City University. "
                "Use --resume after a crash."
            )
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help=(
                "Skip universities already marked completed in "
                f"{PROGRESS_NAME} (download runs only; --clean-only re-processes all). "
                "The current university still resumes URL downloads."
            ),
        )
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Re-download all course HTML for each university (cannot combine with --resume).",
        )
        parser.add_argument(
            "--clean-only",
            action="store_true",
            help="Clean existing HTML only; skip download.",
        )
        parser.add_argument(
            "--download-only",
            action="store_true",
            help="Download HTML only; skip cleaning.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Pass --limit N through to download_and_clean_course_pages.py.",
        )
        parser.add_argument(
            "--university",
            action="append",
            dest="universities",
            metavar="NAME",
            help="Only these university folder names. Repeatable.",
        )
        parser.add_argument(
            "--skip",
            action="append",
            dest="skip",
            metavar="NAME",
            help="Extra university folder names to skip. Repeatable.",
        )
        parser.add_argument(
            "--include-done",
            action="store_true",
            help="Do not auto-skip Aston, ARU, and Birmingham City University.",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop the batch on the first university failure.",
        )
        parser.add_argument(
            "--repo-root",
            type=Path,
            default=_REPO_ROOT,
            help="Repo root (default: parent of shared/).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the university list without running download/clean.",
        )
        return parser.parse_args()

    @classmethod
    def main(cls) -> int:
        args = cls.parse_args()
        return BatchDownloadCleanRunner(args.repo_root).run(args)


# Backward-compatible module-level aliases
utc_now = BatchDownloadCleanRunner.utc_now
progress_path = lambda repo_root: BatchDownloadCleanRunner(repo_root).progress_path()
load_progress = lambda repo_root: BatchDownloadCleanRunner(repo_root).load_progress()
save_progress = lambda repo_root, progress: BatchDownloadCleanRunner(repo_root).save_progress(progress)
discover_universities = lambda repo_root: BatchDownloadCleanRunner(repo_root).discover_universities()
count_course_urls = BatchDownloadCleanRunner.count_course_urls
build_command = BatchDownloadCleanRunner().build_command
parse_args = BatchDownloadCleanCLI.parse_args
main = BatchDownloadCleanCLI.main


if __name__ == "__main__":
    raise SystemExit(BatchDownloadCleanCLI.main())
