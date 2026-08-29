#!/usr/bin/env python3
"""Run LLM extract → normalize → dev CSV for one university (portable, no PowerShell).

Examples (from repo root, any machine):
  python shared/run_llm_to_dev_csv.py --code-dir "Aston University/code" --resume
  python shared/run_llm_to_dev_csv.py --university "Aston University" --resume
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED_DIR.parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from uni_paths import resolve_code_dir, resolve_output_dir
from study_level import PRESETUP_CLEAN_SUBDIR, clean_courses_root, iter_course_markdown


def utc_python() -> str:
    return sys.executable or "python"


def run_step(label: str, command: list[str], cwd: Path) -> None:
    print()
    print(f"==> {label}")
    print(" ".join(command))
    result = subprocess.run(command, cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(f"Step failed ({label}): exit {result.returncode}")


def ollama_ok(host: str) -> bool:
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def resolve_university_code_dir(args: argparse.Namespace) -> Path:
    if args.code_dir:
        return resolve_code_dir(Path(args.code_dir))
    if args.university:
        return resolve_code_dir(_REPO_ROOT / args.university / "code")
    return resolve_code_dir(Path.cwd())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LLM extract, normalize, and export dev_courses CSV."
    )
    parser.add_argument("--code-dir", type=Path, help="University code/ folder")
    parser.add_argument("--university", help="University folder name under the repo root")
    parser.add_argument("--resume", action="store_true", help="Skip already-extracted courses")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--skip-extract", action="store_true")
    parser.add_argument("--skip-normalize", action="store_true")
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--skip-stage1", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--host", default="")
    parser.add_argument(
        "--study-level",
        action="append",
        default=[],
        metavar="LEVEL",
        help="Restrict extract/normalize/export to a study level (repeatable)",
    )
    parser.add_argument(
        "--presetup",
        action="store_true",
        help="Extract only the presetup_sample.json courses",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code_dir = resolve_university_code_dir(args)
    output_dir = resolve_output_dir(code_dir)
    python = utc_python()
    extract_script = _SHARED_DIR / "llm_extract.py"
    normalize_script = _SHARED_DIR / "normalize_admission_data.py"
    export_script = _SHARED_DIR / "export_dev_courses.py"
    host = (args.host or "http://localhost:11434").rstrip("/")

    courses_dir = clean_courses_root(output_dir, presetup=args.presetup)
    md_count = len(iter_course_markdown(courses_dir)) if courses_dir.is_dir() else 0
    if not args.skip_extract and md_count == 0:
        label = f"clean/{PRESETUP_CLEAN_SUBDIR}" if args.presetup else "clean/courses"
        print(f"No {label} markdown in {courses_dir}. Run download/clean first.", file=sys.stderr)
        return 1
    if not args.skip_extract and not ollama_ok(host):
        print(f"Ollama is not reachable at {host}. Start Ollama, then re-run.", file=sys.stderr)
        return 1

    print(f"University : {code_dir.parent.name}")
    print(f"Code dir   : {code_dir}")
    if args.resume:
        print("Mode       : RESUME")

    if not args.skip_extract:
        index_csv = output_dir / "courses.csv"
        if not args.presetup and (args.build_index or not index_csv.exists()):
            run_step(
                "Build courses.csv index",
                [python, "-u", str(extract_script), str(code_dir), "--build-index"],
                _REPO_ROOT,
            )
        extract_cmd = [python, "-u", str(extract_script), str(code_dir)]
        if args.resume:
            extract_cmd.append("--resume")
        if args.limit > 0:
            extract_cmd.extend(["--limit", str(args.limit)])
        if args.skip_stage1:
            extract_cmd.append("--skip-stage1")
        if args.model:
            extract_cmd.extend(["--model", args.model])
        if args.host:
            extract_cmd.extend(["--host", host])
        if args.presetup:
            extract_cmd.append("--presetup")
        for level in args.study_level or []:
            extract_cmd.extend(["--study-level", level])
        run_step("Phase 3 - LLM extract", extract_cmd, _REPO_ROOT)

    if args.extract_only:
        print("Done (--extract-only).")
        return 0

    limit_args = ["--limit", str(args.limit)] if args.limit > 0 else []
    if not args.skip_normalize:
        run_step(
            "Phase 4 - normalize",
            [python, "-u", str(normalize_script), str(code_dir), *limit_args],
            _REPO_ROOT,
        )
    run_step(
        "Phase 5 - export CSV",
        [python, "-u", str(export_script), str(code_dir), *limit_args],
        _REPO_ROOT,
    )
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
