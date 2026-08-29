"""Load university pipeline status from disk."""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[3] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from pipeline_status import scan_all_universities, summarize


def load_status(repo_root: Path) -> tuple[list[dict], dict]:
    rows = scan_all_universities(repo_root)
    return rows, summarize(rows)
