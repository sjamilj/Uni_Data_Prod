"""LLM extract from output/clean/courses (no presetup, no download/clean).

Forwards to shared/run_course_pipeline.py with --code-dir set to this folder.
Adds --llm-only when you omit a pipeline mode flag.

Examples (from repo root):
  python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --all --resume
  python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --limit 3
  python -u "Manchester Metropolitan University/code/run_llm_from_clean.py" --study-level postgraduate --all --resume

Requires Ollama. Builds output/courses.csv from clean/courses when missing or stale.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHARED_SCRIPT = _REPO_ROOT / "shared" / "run_course_pipeline.py"

_MODE_FLAGS = frozenset({"--llm-only", "--presetup", "--presetup-llm", "--execute"})


if __name__ == "__main__":
    extra = list(sys.argv[1:])
    if not any(flag in _MODE_FLAGS for flag in extra):
        extra = ["--llm-only", *extra]
    sys.argv = [str(_SHARED_SCRIPT), "--code-dir", str(_CODE_DIR), *extra]
    runpy.run_path(str(_SHARED_SCRIPT), run_name="__main__")
