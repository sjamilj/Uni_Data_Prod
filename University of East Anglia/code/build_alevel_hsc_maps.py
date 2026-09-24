#!/usr/bin/env python3
"""Rebuild uea_*_alevel_to_hsc.json courseCount from clean course markdown Typical Offer lines."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = CODE_DIR.parent / "output"
TYPICAL_RE = re.compile(r"\*\*Typical Offer:\*\*\s*([A-E\*]{2,4})", re.I)
CONTEXTUAL_RE = re.compile(r"\*\*Contextual Offer:\*\*\s*([A-E\*]{2,4})", re.I)

# UEA-published HSC grades (South Asia / bangladesh-entry.md)
UEA_OFFICIAL = {
    "foundation": {"CCC": "GPA 3.5"},
    "undergraduate": {"ABB": "GPA 5.0", "BBB": "GPA 4.0"},
}

SHARED_FALLBACK = {
    "AAA": "GPA 5.0",
    "AAB": "GPA 5.0",
    "ABB": "GPA 5.0",
    "BBB": "GPA 4.0",
    "BBC": "GPA 4.0",
    "BCC": "GPA 3.5",
    "CCC": "GPA 3.5",
    "CCD": "GPA 3.5",
    "CDD": "GPA 3.5",
}


def scan_level(level: str) -> tuple[Counter[str], Counter[str]]:
    typical: Counter[str] = Counter()
    contextual: Counter[str] = Counter()
    folder = OUTPUT_DIR / "clean" / "courses" / level
    if not folder.is_dir():
        return typical, contextual
    for path in folder.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if m := TYPICAL_RE.search(text):
            typical[m.group(1).upper()] += 1
        if m := CONTEXTUAL_RE.search(text):
            contextual[m.group(1).upper()] += 1
    return typical, contextual


def hsc_grade(level: str, alevel: str) -> str:
    official = UEA_OFFICIAL.get(level, {})
    if alevel in official:
        return official[alevel]
    return SHARED_FALLBACK.get(alevel, "")


def main() -> int:
    foundation_typical, foundation_contextual = scan_level("foundation")
    ug_typical, ug_contextual = scan_level("undergraduate")

    foundation_doc = {
        "university": "University of East Anglia",
        "studyLevel": "foundation",
        "description": "Typical Offer on foundation-year course pages → HSC (see bangladesh-entry.md).",
        "typicalOffer": {
            combo: {
                "degree": "HSC",
                "grade": hsc_grade("foundation", combo),
                "courseCount": count,
                "source": (
                    "clean/uni/bangladesh-entry.md"
                    if combo in UEA_OFFICIAL.get("foundation", {})
                    else "shared ALEVEL_TO_HSC_EQUIVALENT"
                ),
            }
            for combo, count in sorted(foundation_typical.items())
        },
        "contextualOffer": {
            combo: {"courseCount": count, "note": "UK contextual; not used for international HSC mapping"}
            for combo, count in sorted(foundation_contextual.items())
        },
    }

    ug_doc = {
        "university": "University of East Anglia",
        "studyLevel": "undergraduate",
        "description": "Typical Offer on UG course pages → HSC.",
        "typicalOffer": {
            combo: {
                "degree": "HSC",
                "grade": hsc_grade("undergraduate", combo),
                "courseCount": count,
                "source": (
                    "clean/uni/bangladesh-entry.md"
                    if combo in UEA_OFFICIAL.get("undergraduate", {})
                    else "shared ALEVEL_TO_HSC_EQUIVALENT (confirm with UEA if needed)"
                ),
            }
            for combo, count in sorted(ug_typical.items())
        },
        "contextualOffer": {
            combo: {"courseCount": count, "note": "UK contextual only"}
            for combo, count in sorted(ug_contextual.items())
        },
    }

    (CODE_DIR / "uea_foundation_alevel_to_hsc.json").write_text(
        json.dumps(foundation_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (CODE_DIR / "uea_undergraduate_alevel_to_hsc.json").write_text(
        json.dumps(ug_doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Wrote uea_foundation_alevel_to_hsc.json and uea_undergraduate_alevel_to_hsc.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
