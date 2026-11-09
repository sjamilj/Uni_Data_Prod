"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  4 :: With placement
  3 :: UK students
  "

Add conditional rules here via cleanup_course_markdown_uni() when .env is not enough.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Per-university rules after shared .env section removal. Default: no-op."""
    return markdown


if __name__ == "__main__":
    raise SystemExit(main())
