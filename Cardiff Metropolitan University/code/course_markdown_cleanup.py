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

from cardiff_intl_tuition_fees import resolve_international_fee_line, strip_pipeline_comment


_ENTRY_BODY_MARKERS = (
    r"\nApplicants should meet",
    r"\nApplicants should normally possess:",
    r"\nApplicants should normally have",
    r"\nStudents should normally possess:",
    r"\n#### Typical Offers",
)


def _strip_entry_preamble(markdown: str) -> str:
    """Remove accordion / foundation-hub catalogue before real entry requirements."""
    if "## Entry requirements" not in markdown:
        return markdown
    for marker in _ENTRY_BODY_MARKERS:
        pattern = rf"(?ms)^## Entry requirements\n+.*?(?={marker})"
        updated = re.sub(pattern, "## Entry requirements\n\n", markdown, count=1)
        if updated != markdown:
            return updated
    if "Compulsory Modules:" in markdown:
        updated = re.sub(
            r"(?ms)^## Entry requirements\n+Compulsory Modules:.*?(?=\nApplicants should meet)",
            "## Entry requirements\n\n",
            markdown,
            count=1,
        )
        if updated != markdown:
            return updated
    return markdown


def _strip_admissions_contact_footer(markdown: str) -> str:
    """Remove generic admissions / programme-leader contact blocks at end of entry."""
    return re.sub(
        r"\n+For general enquiries, please contact the Admissions Team.*?(?=\n## |\Z)",
        "\n",
        markdown,
        count=1,
        flags=re.I | re.DOTALL,
    )


def cleanup_course_markdown_uni(markdown: str) -> str:
    """Cardiff Met: normalize sidebar facts for Stage 1 parser (Terminal Four course pages)."""
    markdown = _strip_entry_preamble(markdown)
    markdown = _strip_admissions_contact_footer(markdown)
    extra: list[str] = []

    if "**Duration:**" not in markdown:
        duration = re.search(
            r"-\s*####\s*Duration\s*\n+([^\n]+)",
            markdown,
            re.I,
        )
        if duration:
            extra.append(f"**Duration:** {duration.group(1).strip()}")

    if not re.search(r"\*\*Start date:\*\*", markdown, re.I):
        year = re.search(r"Entry Year\s+(\d{4})", markdown)
        intake_year = year.group(1) if year else "2026"
        extra.append(f"- **Start date:** September {intake_year}")

    fee_line = resolve_international_fee_line(markdown)
    if fee_line:
        extra.append(fee_line)

    markdown = strip_pipeline_comment(markdown)

    if not extra:
        return markdown

    section = "## Key facts (normalized)\n\n" + "\n".join(extra) + "\n"
    if "## Key facts (normalized)" in markdown:
        return re.sub(
            r"## Key facts \(normalized\)\n\n[\s\S]*?(?=\n## |\Z)",
            section.rstrip() + "\n",
            markdown,
            count=1,
        )
    return markdown.rstrip() + "\n\n" + section


if __name__ == "__main__":
    raise SystemExit(main())
