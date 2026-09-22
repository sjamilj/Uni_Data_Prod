"""University of Suffolk — A-Level → HSC CGPA (from INTO entry requirements PDF).

Source: UOS INTO International Foundation entry table (A Level requirements column
paired with INTO Academic requirements %), converted to Bangladesh HSC CGPA out of 5
via the official 5.0-scale percentage bands in ``normalize_admission_data.BD_OFFICIAL_5_SCALE``.

PDF: https://www.uos.ac.uk/media/uniofsuffolk/website/content-assets/documents/international/017-INTO-Entry-Requirements_02-2026_A3-digital-[Final-ac].pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from normalize_admission_data import (  # noqa: E402
    ALEVEL_TO_HSC_EQUIVALENT,
    BD_OFFICIAL_5_SCALE,
    _closest_threshold,
    register_uni_alevel_to_hsc_map,
)

UNIVERSITY_NAME = "University of Suffolk"

INTO_ENTRY_REQUIREMENTS_PDF = (
    "https://www.uos.ac.uk/media/uniofsuffolk/website/content-assets/documents/international/"
    "017-INTO-Entry-Requirements_02-2026_A3-digital-[Final-ac].pdf"
)

# A-Level (3 subjects) → INTO Academic requirements % (unique rows in Feb 2026 PDF).
ALEVEL_TO_INTO_ACADEMIC_PERCENT: dict[str, int] = {
    "CDD": 45,
    "CCC": 55,
    "BBC": 60,
    "BBB": 65,
}


def _into_percent_to_hsc_cgpa(percent: int) -> float:
    return float(_closest_threshold(int(percent), BD_OFFICIAL_5_SCALE))


def build_suffolk_alevel_to_hsc_equivalent() -> dict[str, float]:
    """PDF-backed combos plus shared defaults for grades not listed in the INTO table."""
    mapping: dict[str, float] = dict(ALEVEL_TO_HSC_EQUIVALENT)
    for combo, into_pct in ALEVEL_TO_INTO_ACADEMIC_PERCENT.items():
        mapping[combo.upper()] = _into_percent_to_hsc_cgpa(into_pct)
    return mapping


SUFFOLK_ALEVEL_TO_HSC_EQUIVALENT = build_suffolk_alevel_to_hsc_equivalent()


def register_suffolk_alevel_mapping() -> None:
    register_uni_alevel_to_hsc_map(UNIVERSITY_NAME, SUFFOLK_ALEVEL_TO_HSC_EQUIVALENT)


register_suffolk_alevel_mapping()
