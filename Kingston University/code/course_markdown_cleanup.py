"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  4 :: With placement
  3 :: UK students
  "

# Kingston hub route variants (kingston_hub_foundation_clean.py) use HUB_ROUTE_CLEAN_BLOCKS
# in .env — not cleanup_course_markdown_uni(). Fees are filtered to the selected route.
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
