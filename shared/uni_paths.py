"""Resolve university code/ (config) vs output/ (generated artifacts) paths."""

from __future__ import annotations

from pathlib import Path


class UniPathResolver:
    """Resolve university code/ and output/ directory paths."""

    OUTPUT_DIR_NAME = "output"

    @classmethod
    def resolve_code_dir(cls, work_dir: Path | None = None) -> Path:
        """University code/ folder (.env, scripts)."""
        return (work_dir or Path.cwd()).resolve()

    @classmethod
    def resolve_output_dir(cls, code_dir: Path | None = None) -> Path:
        """University output/ folder (CSVs, HTML, clean/, extracted/, logs)."""
        code = cls.resolve_code_dir(code_dir)
        # University/code/.env layout -> sibling output/; uni root or repo cwd -> code/output/
        if code.name == "code":
            out = code.parent / cls.OUTPUT_DIR_NAME
        else:
            out = code / cls.OUTPUT_DIR_NAME
        out.mkdir(parents=True, exist_ok=True)
        return out


OUTPUT_DIR_NAME = UniPathResolver.OUTPUT_DIR_NAME
resolve_code_dir = UniPathResolver.resolve_code_dir
resolve_output_dir = UniPathResolver.resolve_output_dir
