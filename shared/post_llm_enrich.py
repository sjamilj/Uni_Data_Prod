#!/usr/bin/env python3
"""Run optional university-specific enrichers after LLM extract, before normalize."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from uni_paths import resolve_code_dir

_SHARED_DIR = Path(__file__).resolve().parent


def run_post_llm_enrich(code_dir: Path) -> int:
    """Execute ``code_dir/run_post_llm_enrich.py`` when present."""
    code_dir = resolve_code_dir(code_dir)
    script = code_dir / "run_post_llm_enrich.py"
    if not script.is_file():
        return 0
    python = sys.executable or "python"
    print()
    print("==> Post-LLM enrich (university-specific)")
    print(" ".join([python, "-u", str(script), str(code_dir)]))
    result = subprocess.run([python, "-u", str(script), str(code_dir)], cwd=str(_SHARED_DIR.parent))
    if result.returncode != 0:
        raise SystemExit(f"Post-LLM enrich failed: exit {result.returncode}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("Usage: post_llm_enrich.py <university-code-dir>", file=sys.stderr)
        return 1
    run_post_llm_enrich(Path(args[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
