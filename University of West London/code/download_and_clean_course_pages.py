"""Download + clean course pages → output/clean/courses (forwards to shared/)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHARED_SCRIPT = _REPO_ROOT / "shared" / "download_and_clean_course_pages.py"


if __name__ == "__main__":
    sys.argv = [str(_SHARED_SCRIPT), str(_CODE_DIR), *sys.argv[1:]]
    runpy.run_path(str(_SHARED_SCRIPT), run_name="__main__")
