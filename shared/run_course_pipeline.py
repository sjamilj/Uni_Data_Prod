#!/usr/bin/env python3
"""Presetup sample + per-course execute orchestrator.

Presetup downloads and cleans a stratified sample of 10 courses (no LLM).
After you review HTML / markdown / .env, --presetup-llm extracts those 10.
Execute then downloads, cleans, and LLM-extracts one course at a time.

Examples (from repo root):
  python shared/run_course_pipeline.py --code-dir "Aston University/code" --presetup
  python shared/run_course_pipeline.py --code-dir "Aston University/code" --presetup-llm --resume
  python shared/run_course_pipeline.py --code-dir "Aston University/code" --execute --study-level foundation --all
  python shared/run_course_pipeline.py --code-dir "Aston University/code" --execute --study-level foundation --limit 25
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_SHARED_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED_DIR.parent
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from download_and_clean_course_pages import (  # noqa: E402
    download_and_clean_course_pages,
    load_strategy_config,
)
from llm_extract import configure_code_dir, load_progress, run_extraction  # noqa: E402
from scrape_course_urls import add_code_dir_argument, resolve_work_dir  # noqa: E402
from study_level import (  # noqa: E402
    CLEAN_COURSES_SUBDIR,
    PRESETUP_CLEAN_SUBDIR,
    PRESETUP_SAMPLE_SIZE,
    is_resume_completed,
    load_presetup_sample,
    load_url_levels,
    parse_study_levels,
    presetup_sample_path,
    presetup_sample_urls,
    save_presetup_sample,
    sample_urls_stratified,
    unique_urls,
    urls_for_levels,
)
from uni_pages import course_slug_from_url  # noqa: E402
from uni_paths import resolve_code_dir, resolve_output_dir  # noqa: E402

EXECUTE_SELECTION_JSON = "execute_selection.json"


def utc_python() -> str:
    return sys.executable or "python"


def ollama_ok(host: str) -> bool:
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _slug(url: str) -> str:
    return course_slug_from_url(url)


def _print(message: str) -> None:
    print(message, flush=True)


def _save_execute_selection(
    output_dir: Path,
    *,
    study_levels: list[str],
    mode: str,
    limit: int | None,
    courses: list[dict[str, str]],
) -> None:
    payload = {
        "study_levels": study_levels,
        "mode": mode,
        "limit": limit,
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "courses": courses,
    }
    path = output_dir / EXECUTE_SELECTION_JSON
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _completed_keys(output_dir: Path) -> set[str]:
    progress = load_progress(output_dir)
    return {str(key) for key in progress.get("completed") or []}


def _already_extracted(output_dir: Path, url: str, study_level: str, resume: bool) -> bool:
    if not resume:
        return False
    slug = _slug(url)
    completed = _completed_keys(output_dir)
    return is_resume_completed(completed, study_level=study_level, slug=slug)


def _download_and_clean_urls(
    code_dir: Path,
    urls: list[str],
    *,
    fresh: bool = False,
    presetup_clean: bool = False,
) -> dict:
    config = load_strategy_config(code_dir)
    return download_and_clean_course_pages(
        code_dir,
        config,
        fresh=fresh,
        urls=urls,
        courses_subdir=PRESETUP_CLEAN_SUBDIR if presetup_clean else CLEAN_COURSES_SUBDIR,
    )


def run_presetup(
    code_dir: Path,
    *,
    sample_size: int = PRESETUP_SAMPLE_SIZE,
    seed: int | None = None,
    fresh: bool = False,
) -> int:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    existing = load_presetup_sample(output_dir)
    existing_urls = presetup_sample_urls(existing)

    if existing_urls and not fresh:
        courses = list(existing.get("courses") or [])
        used_seed = int(existing.get("seed") or 0)
        _print(
            f"Presetup: reusing {len(courses)} URLs from {presetup_sample_path(output_dir).name} "
            f"(seed={used_seed}). Pass --fresh to resample."
        )
    else:
        mapping = load_url_levels(output_dir)
        if not mapping.urls():
            print(
                f"Error: no study-level URLs in {output_dir}. Run scrape_course_urls.py first.",
                file=sys.stderr,
            )
            return 1
        used_seed = seed if seed is not None else random.randrange(1, 2**31)
        courses = sample_urls_stratified(mapping, n=sample_size, seed=used_seed)
        if not courses:
            print("Error: stratified sample produced no URLs.", file=sys.stderr)
            return 1
        path = save_presetup_sample(output_dir, courses, seed=used_seed, n=sample_size)
        _print(f"Presetup: sampled {len(courses)} URLs (seed={used_seed}) -> {path}")
        for row in courses:
            _print(f"  [{row.get('study_level')}] {row.get('course_url')}")

    urls = unique_urls([str(row.get("course_url") or "") for row in courses])
    _print(f"Presetup: download + clean {len(urls)} course(s) (no LLM).")
    _print("After this finishes, review output/course_pages/ and output/clean/pre_setup_course/,")
    _print("edit code/.env and code/course_markdown_cleanup.py if needed, then run --presetup-llm.")
    _download_and_clean_urls(code_dir, urls, fresh=False, presetup_clean=True)
    _print("Presetup download/clean done. Human review next, then --presetup-llm.")
    return 0


def run_presetup_llm(
    code_dir: Path,
    *,
    resume: bool = False,
    model: str = "",
    host: str = "",
    skip_stage1: bool = False,
) -> int:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    sample = load_presetup_sample(output_dir)
    urls = presetup_sample_urls(sample)
    if not urls:
        print(
            f"Error: {presetup_sample_path(output_dir)} missing. Run --presetup first.",
            file=sys.stderr,
        )
        return 1
    ollama_host = (host or "http://localhost:11434").rstrip("/")
    if not ollama_ok(ollama_host):
        print(f"Ollama is not reachable at {ollama_host}. Start Ollama, then re-run.", file=sys.stderr)
        return 1
    configure_code_dir(code_dir)
    _print(f"Presetup LLM: {len(urls)} sampled course(s).")
    run_extraction(
        code_dir,
        resume=resume,
        model=model or None,
        host=host or None,
        skip_stage1=skip_stage1,
        presetup=True,
    )
    _print("Presetup LLM done. If extraction looks right, run --execute.")
    return 0


def _select_execute_courses(
    output_dir: Path,
    study_levels: list[str],
    *,
    all_urls: bool,
    limit: int | None,
) -> list[dict[str, str]]:
    mapping = load_url_levels(output_dir)
    records = urls_for_levels(mapping, study_levels)
    if not all_urls and limit is not None:
        records = records[:limit]
    return records


def _normalize_and_export(code_dir: Path) -> None:
    python = utc_python()
    for label, script in (
        ("Phase 4 - normalize", "normalize_admission_data.py"),
        ("Phase 5 - export CSV", "export_dev_courses.py"),
    ):
        command = [python, "-u", str(_SHARED_DIR / script), str(code_dir)]
        _print(f"==> {label}")
        _print(" ".join(command))
        result = subprocess.run(command, cwd=str(_REPO_ROOT))
        if result.returncode != 0:
            raise SystemExit(f"Step failed ({label}): exit {result.returncode}")


def run_execute(
    code_dir: Path,
    *,
    study_levels: list[str],
    all_urls: bool,
    limit: int | None,
    resume: bool = True,
    model: str = "",
    host: str = "",
    skip_stage1: bool = False,
    skip_export: bool = False,
) -> int:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    if not study_levels:
        print("Error: --execute requires --study-level at least once.", file=sys.stderr)
        return 1
    if not all_urls and (limit is None or limit <= 0):
        print("Error: --execute requires --all or --limit N.", file=sys.stderr)
        return 1

    ollama_host = (host or "http://localhost:11434").rstrip("/")
    if not ollama_ok(ollama_host):
        print(f"Ollama is not reachable at {ollama_host}. Start Ollama, then re-run.", file=sys.stderr)
        return 1

    courses = _select_execute_courses(
        output_dir, study_levels, all_urls=all_urls, limit=limit
    )
    if not courses:
        print(
            f"Error: no URLs for study level(s): {', '.join(study_levels)}. "
            "Run scrape first and check *_course_urls.csv.",
            file=sys.stderr,
        )
        return 1

    mode = "all" if all_urls else "limit"
    _save_execute_selection(
        output_dir,
        study_levels=study_levels,
        mode=mode,
        limit=None if all_urls else limit,
        courses=courses,
    )
    configure_code_dir(code_dir)
    _print(
        f"Execute: {len(courses)} course(s) "
        f"[{', '.join(study_levels)}] mode={mode} "
        f"(download -> clean -> LLM per course)"
    )

    failed = 0
    skipped = 0
    done = 0
    for index, row in enumerate(courses, start=1):
        url = str(row.get("course_url") or "").strip()
        level = str(row.get("study_level") or "").strip()
        if not url:
            continue
        _print(f"[{index}/{len(courses)}] {level}  {url}")
        if _already_extracted(output_dir, url, level, resume):
            skipped += 1
            _print("  skip (already extracted)")
            continue
        try:
            _download_and_clean_urls(code_dir, [url], fresh=False)
            run_extraction(
                code_dir,
                resume=resume,
                model=model or None,
                host=host or None,
                skip_stage1=skip_stage1,
                urls=[url],
            )
            done += 1
        except Exception as exc:
            failed += 1
            print(f"  ERROR: {exc}", file=sys.stderr, flush=True)
            continue

    _print(f"Execute loop done: extracted={done} skipped={skipped} failed={failed}")
    if skip_export:
        _print("Skipping normalize/export (--skip-export).")
        return 0 if failed == 0 else 1
    if done == 0 and skipped == 0:
        print("Nothing extracted; skip normalize/export.", file=sys.stderr)
        return 1 if failed else 0
    _normalize_and_export(code_dir)
    _print("Execute complete.")
    return 0 if failed == 0 else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Presetup sample (10 mixed levels) then per-course execute."
    )
    add_code_dir_argument(parser)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--presetup",
        action="store_true",
        help="Sample 10 mixed-level URLs, download HTML, and clean to markdown (no LLM)",
    )
    mode.add_argument(
        "--presetup-llm",
        action="store_true",
        help="LLM-extract the presetup sample after you have reviewed markdown/.env",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Per-course download, clean, then LLM for selected study levels",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Presetup: draw a new random sample (ignore existing presetup_sample.json)",
    )
    parser.add_argument("--resume", action="store_true", help="Skip courses already extracted")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=PRESETUP_SAMPLE_SIZE,
        help=f"Presetup sample size (default: {PRESETUP_SAMPLE_SIZE})",
    )
    parser.add_argument("--seed", type=int, default=None, help="Presetup RNG seed")
    parser.add_argument(
        "--study-level",
        action="append",
        default=[],
        metavar="LEVEL",
        help="Execute: study level to include (repeatable)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_urls",
        help="Execute: all URLs in the selected study level(s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Execute: process N URLs from the selected study level(s)",
    )
    parser.add_argument("--model", default="", help="Ollama model")
    parser.add_argument("--host", default="", help="Ollama host")
    parser.add_argument("--skip-stage1", action="store_true")
    parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Execute: skip normalize + dev CSV export at the end",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    code_dir = resolve_work_dir(args.code_dir)
    try:
        if args.presetup:
            return run_presetup(
                code_dir,
                sample_size=args.sample_size,
                seed=args.seed,
                fresh=args.fresh,
            )
        if args.presetup_llm:
            return run_presetup_llm(
                code_dir,
                resume=args.resume,
                model=args.model,
                host=args.host,
                skip_stage1=args.skip_stage1,
            )
        levels = parse_study_levels(args.study_level)
        return run_execute(
            code_dir,
            study_levels=levels,
            all_urls=args.all_urls,
            limit=args.limit,
            resume=args.resume or not args.fresh,
            model=args.model,
            host=args.host,
            skip_stage1=args.skip_stage1,
            skip_export=args.skip_export,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
