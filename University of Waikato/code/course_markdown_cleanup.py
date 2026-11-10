"""University of Waikato course markdown cleanup.

Waikato qualification pages are extracted through CSS selectors configured in
code/.env (overview, desktop key facts, entry requirements and fees tabs).
This hook stays available for future Waikato-specific markdown corrections.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Return the selected qualification content without further rewriting."""
    return markdown


if __name__ == "__main__":
    raise SystemExit(main())
