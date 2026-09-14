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

_BRACKET_ONLY = re.compile(r"^\s*[\[\]]\s*$")
_BROKEN_FEE_TAIL = re.compile(
    r"^\s*\]\s*\]\s*-\s*UK Scholarships.*$",
    re.I | re.MULTILINE,
)


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Strip MMU accordion placeholders left by HTML→markdown conversion."""
    lines: list[str] = []
    for line in markdown.splitlines():
        if _BRACKET_ONLY.match(line):
            continue
        if _BROKEN_FEE_TAIL.match(line):
            continue
        lines.append(line.rstrip())
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
