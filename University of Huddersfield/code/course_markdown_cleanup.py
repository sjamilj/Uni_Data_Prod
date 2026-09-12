"""University-specific course markdown cleanup (optional).

Configure simple heading removal in code/.env:

  COURSE_MARKDOWN_REMOVE_SECTIONS="
  4 :: With placement
  3 :: UK students
  "

Add conditional rules here via cleanup_course_markdown_uni() when .env is not enough.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import main


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Strip Huddersfield marketing noise that survives generic block extraction."""
    markdown = re.sub(r"^## Overview\s*\n+", "", markdown, flags=re.M)
    markdown = re.sub(
        r"^About this course\s*\n+.*?(?=^## )",
        "",
        markdown,
        flags=re.M | re.S,
    )
    markdown = re.sub(
        r"^### Accreditation and Professional Links\s*\n+Recognised connections to give you an extra edge when you graduate\.\s*\n+",
        "",
        markdown,
        flags=re.M | re.I,
    )
    markdown = re.sub(
        r"(?m)^Recent Awards For Excellence\s*\n+Find out more about these awards\s*\n+",
        "",
        markdown,
    )
    markdown = re.sub(r"(?m)^fees-and-finance-placement\s*\n?", "", markdown)
    return markdown


if __name__ == "__main__":
    raise SystemExit(main())
