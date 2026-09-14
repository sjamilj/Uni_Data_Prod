"""Build output/courses.csv from output/clean/courses/*.md (forwards to shared llm_extract)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHARED_SCRIPT = _REPO_ROOT / "shared" / "llm_extract.py"


if __name__ == "__main__":
    sys.argv = [str(_SHARED_SCRIPT), str(_CODE_DIR), "--build-index", *sys.argv[1:]]
    runpy.run_path(str(_SHARED_SCRIPT), run_name="__main__")
