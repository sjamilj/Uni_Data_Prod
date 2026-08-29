"""Resolve university code/ (config) vs output/ (generated artifacts) paths."""

from __future__ import annotations

from pathlib import Path

OUTPUT_DIR_NAME = "output"


def resolve_code_dir(work_dir: Path | None = None) -> Path:
    """University code/ folder (.env, scripts)."""
    return (work_dir or Path.cwd()).resolve()


def resolve_output_dir(code_dir: Path | None = None) -> Path:
    """University output/ folder (CSVs, HTML, clean/, extracted/, logs)."""
    code = resolve_code_dir(code_dir)
    out = code.parent / OUTPUT_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)
    return out
