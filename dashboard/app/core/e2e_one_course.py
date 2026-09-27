"""Build command for dashboard/e2e_one_course.py (no shared/ edits)."""

from __future__ import annotations

import sys
from pathlib import Path


def e2e_one_course_commands(
    repo_root: Path,
    code_dir: str,
    study_levels: list[str],
    *,
    fresh: bool,
    force_scrape: bool = False,
    pins_file: str | None = None,
    python: str | None = None,
) -> list[list[str]]:
    py = python or sys.executable or "python"
    command = [
        py,
        "-u",
        str(repo_root / "dashboard" / "e2e_one_course.py"),
        "--code-dir",
        code_dir,
    ]
    if fresh:
        command.append("--fresh")
    else:
        command.append("--resume")
    if force_scrape:
        command.append("--force-scrape")
    if pins_file:
        command.extend(["--pins-file", pins_file])
    for level in study_levels:
        command.extend(["--study-level", level])
    return [command]
