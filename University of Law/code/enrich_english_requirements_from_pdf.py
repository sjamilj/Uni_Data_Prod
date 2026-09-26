#!/usr/bin/env python3
"""Merge ULaw accepted-qualifications PDF (Table 1 + Table 2) into english-requirements.md.

Run after convert_country_entry_html.py::

    python enrich_english_requirements_from_pdf.py

Adds PDF-only programme rows, fixes gaps (e.g. Certificate of Higher Education IELTS),
and attaches PTE / TOEFL / LanguageCert / Duolingo / ULET equivalents per IELTS band.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_ROOT = _CODE_DIR.parent
_DEFAULT_ENGLISH = _UNI_ROOT / "output" / "clean" / "uni" / "english-requirements.md"
_DEFAULT_PDF = _UNI_ROOT / "uni_req" / "pdf_students_accepted-english-language-qualifications.pdf"
_PDF_SOURCE_REL = "uni_req/pdf_students_accepted-english-language-qualifications.pdf"
_PDF_SOURCE_URL = (
    "https://www.law.ac.uk/globalassets/13.-media--doc-repo/"
    "04.-students/international/pdf_students_accepted-english-language-qualifications.pdf"
)

# Table 2 columns: (ielts_overall, ielts_min_section)
IELTS_BANDS: list[tuple[str, str]] = [
    ("5.0", "4.5"),
    ("5.5", "5.5"),
    ("6.0", "5.5"),
    ("6.5", "6.0"),
    ("7.0", "6.5"),
    ("7.5", "7.5"),
]

# Curated from PDF Table 2 (2026 edition); section detail in band_notes.
TABLE2_BY_BAND: list[dict] = [
    {
        "pteOverall": "43",
        "pteMinSection": "43",
        "toeflOverall": "40",
        "toeflMinSection": "5",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 40 overall; min. 5 Listening/Reading, 15 Writing/Speaking",
        "languageCertOverall": "50",
        "languageCertMinSection": "40",
        "duolingo": "",
        "uletOverall": "5.0",
        "uletMinSection": "4.5",
        "oxfordEllt": "",
    },
    {
        "pteOverall": "52",
        "pteMinSection": "52",
        "toeflOverall": "49",
        "toeflMinSection": "7",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 49 overall; min. 7 L, 8 R, 18 W, 16 S",
        "languageCertOverall": "60",
        "languageCertMinSection": "60",
        "duolingo": "100",
        "duolingoNote": "Duolingo: 100 overall (100 min. each subscore)",
        "uletOverall": "5.5",
        "uletMinSection": "5.5",
        "oxfordEllt": "5",
        "oxfordElltNote": "Oxford ELLT: 5 overall (5 min. each skill)",
    },
    {
        "pteOverall": "56",
        "pteMinSection": "52",
        "pteNote": "PTE Academic: 56 overall; min. 52 in each skill",
        "toeflOverall": "60",
        "toeflMinSection": "11",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 60 overall; min. 11 L, 12 R, 20 W, 17 S",
        "languageCertOverall": "65",
        "languageCertMinSection": "60",
        "duolingo": "110",
        "duolingoNote": "Duolingo: 110 overall (100 min. each subscore)",
        "uletOverall": "6.0",
        "uletMinSection": "5.5",
        "oxfordEllt": "6",
        "oxfordElltNote": "Oxford ELLT: 6 overall (5 min. each skill)",
    },
    {
        "pteOverall": "59",
        "pteMinSection": "56",
        "pteNote": "PTE Academic: 59 overall; min. 56 L/R/S and 62 Writing",
        "toeflOverall": "79",
        "toeflMinSection": "18",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 79 overall; min. 19 L/S, 18 R, 23 W",
        "languageCertOverall": "70",
        "languageCertMinSection": "65",
        "duolingo": "120",
        "duolingoNote": "Duolingo: 120 overall (110 min. each subscore)",
        "uletOverall": "6.5",
        "uletMinSection": "6.0",
        "oxfordEllt": "7",
        "oxfordElltNote": "Oxford ELLT: 7 overall (6 min. each skill)",
    },
    {
        "pteOverall": "66",
        "pteMinSection": "59",
        "pteNote": "PTE Academic: 66 overall; min. 59 L/R/S and 74 Writing",
        "toeflOverall": "94",
        "toeflMinSection": "22",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 94 overall; min. 23 L/R, 26 W, 22 S",
        "languageCertOverall": "75",
        "languageCertMinSection": "70",
        "duolingo": "130",
        "duolingoNote": "Duolingo: 130 overall (120 min.; 130 min. Writing)",
        "uletOverall": "7.0",
        "uletMinSection": "6.5",
        "oxfordEllt": "8",
        "oxfordElltNote": "Oxford ELLT: 8 overall (7 min. each skill)",
    },
    {
        "pteOverall": "78",
        "pteMinSection": "75",
        "pteNote": "PTE Academic: 78 overall; min. 75 L/R/S and 88 Writing",
        "toeflOverall": "102",
        "toeflMinSection": "23",
        "toeflNote": "TOEFL iBT (from 26 Jan 2026): 102 overall; min. 26 L, 25 R, 28 W, 23 S",
        "languageCertOverall": "80",
        "languageCertMinSection": "80",
        "duolingo": "143",
        "duolingoNote": "Duolingo: 143 overall (L135, R135, W155, S145)",
        "uletOverall": "7.5",
        "uletMinSection": "7.5",
        "oxfordEllt": "9",
        "oxfordElltNote": "Oxford ELLT: 9 overall (9 min. each skill)",
    },
]

# PDF Table 1 programmes not present on the Bangladesh country HTML export.
PDF_EXTRA_PROGRAMMES: list[dict] = [
    {
        "TestStudyLevel": "Undergraduate",
        "subjectArea": "Law",
        "ProgramName": "Law: Degrees with Foundation (Blended)",
        "duration": "Blended",
        "ieltsOverall": "5.5",
        "ieltsSection": "5.5",
        "description": [
            "Law degrees with Foundation (Blended).",
            "IELTS Academic 5.5 overall with minimum 5.5 in each component.",
        ],
    },
    {
        "TestStudyLevel": "Undergraduate",
        "subjectArea": "Criminology",
        "ProgramName": "Criminology: Degrees with Foundation (Blended)",
        "duration": "Blended",
        "ieltsOverall": "5.5",
        "ieltsSection": "5.5",
        "description": [
            "Criminology degree with Foundation (Blended).",
        ],
    },
    {
        "TestStudyLevel": "Undergraduate",
        "subjectArea": "Psychology",
        "ProgramName": "Psychology: Degrees with Foundation (Blended)",
        "duration": "Blended",
        "ieltsOverall": "5.5",
        "ieltsSection": "5.5",
        "description": [
            "Psychology degree with Foundation (Blended).",
        ],
    },
    {
        "TestStudyLevel": "Undergraduate",
        "subjectArea": "Computer Science",
        "ProgramName": "Computer Science: Degrees with Foundation (Blended)",
        "duration": "Blended",
        "ieltsOverall": "5.5",
        "ieltsSection": "5.5",
        "description": [
            "Computer Science degree with Foundation (Blended).",
        ],
    },
    {
        "TestStudyLevel": "Postgraduate",
        "subjectArea": "Business",
        "ProgramName": "Business: MSc Global Accounting Top-Up",
        "duration": "",
        "ieltsOverall": "6.5",
        "ieltsSection": "5.5",
        "description": ["MSc in Global Accounting Top-Up degree."],
    },
    {
        "TestStudyLevel": "Postgraduate",
        "subjectArea": "Criminology",
        "ProgramName": "Criminology: MSc Criminology and Criminal Justice",
        "duration": "One year",
        "ieltsOverall": "6.5",
        "ieltsSection": "6.0",
        "description": ["MSc Criminology and Criminal Justice."],
    },
    {
        "TestStudyLevel": "Postgraduate",
        "subjectArea": "Education",
        "ProgramName": "Education: MA/PGCert HE Administration, Management & Leadership",
        "duration": "",
        "ieltsOverall": "6.5",
        "ieltsSection": "6.0",
        "description": [
            "MA/PGCert in HE Administration, Management & Leadership.",
        ],
    },
    {
        "TestStudyLevel": "Postgraduate",
        "subjectArea": "Psychology",
        "ProgramName": "Psychology: MSc Psychology (Conversion)",
        "duration": "One year",
        "ieltsOverall": "6.5",
        "ieltsSection": "6.0",
        "description": ["MSc Psychology (Conversion)."],
    },
    {
        "TestStudyLevel": "Postgraduate",
        "subjectArea": "Computer Science",
        "ProgramName": "Computer Science: MSc Computer Science (Conversion)",
        "duration": "One year",
        "ieltsOverall": "6.0",
        "ieltsSection": "5.5",
        "description": ["MSc Computer Science (Conversion)."],
    },
]

CERT_HE_PROGRAM = "Law: Certificate of Higher Education"
CERT_HE_IELTS = ("6.5", "6.0")

VALIDITY_NOTE = (
    "English language tests are generally valid for up to 2 years before the "
    "course start date (see ULaw accepted English qualifications for exceptions)."
)


def _public_description_line(line: str) -> str:
    text = (line or "").strip()
    if not text:
        return ""
    if text.startswith("PDF Table 2:"):
        return VALIDITY_NOTE
    if text.startswith("PDF Table 1:"):
        rest = text[len("PDF Table 1:") :].strip()
        if "grouped with LLB" in rest:
            return "Same English requirement as LLB (Hons) / Top-Up programmes: IELTS 6.5 (6.0)."
        return rest
    return text


def _band_index(overall: str, section: str) -> int | None:
    overall = str(overall).strip()
    section = str(section).strip()
    # Table 1 only: Global Accounting Top-Up — use Table 2 "6.0 (5.5)" equivalents.
    if (overall, section) == ("6.5", "5.5"):
        return 2
    for i, band in enumerate(IELTS_BANDS):
        if band == (overall, section):
            return i
    return None


def _ielts_from_row(row: dict) -> tuple[str, str] | None:
    for test in row.get("TestRequirements") or []:
        if not isinstance(test, dict):
            continue
        overall = str(test.get("ieltsMinOverall") or "").strip()
        section = str(test.get("ieltsMinSection") or "").strip()
        if overall:
            return overall, section
    return None


def build_test_requirements(overall: str, section: str) -> tuple[list[dict], list[str]]:
    idx = _band_index(overall, section)
    if idx is None:
        return [], []

    table2 = TABLE2_BY_BAND[idx]
    notes: list[str] = []
    tests: list[dict] = [
        {
            "TestName": "IELTS Academic",
            "ieltsMinOverall": overall,
            "ieltsMinSection": section,
        },
        {
            "TestName": "PTE Academic (not Online)",
            "pteMinOverall": table2["pteOverall"],
            "pteMinSection": table2["pteMinSection"],
        },
        {
            "TestName": "TOEFL iBT",
            "toeflMinOverall": table2["toeflOverall"],
            "toeflMinSection": table2.get("toeflMinSection") or "",
        },
    ]

    notes.append(
        f"ULET: {table2['uletOverall']} overall (min. {table2['uletMinSection']} in each skill)."
    )
    notes.append(
        f"LanguageCert Academic: {table2['languageCertOverall']} overall "
        f"(min. {table2['languageCertMinSection']} in each skill)."
    )
    if table2.get("pteNote"):
        notes.append(table2["pteNote"])
    if table2.get("toeflNote"):
        notes.append(table2["toeflNote"])
    if table2.get("duolingo"):
        notes.append(table2.get("duolingoNote") or f"Duolingo: {table2['duolingo']}")
    if table2.get("oxfordEllt"):
        notes.append(table2.get("oxfordElltNote") or f"Oxford ELLT: {table2['oxfordEllt']}")

    notes.append(VALIDITY_NOTE)
    return tests, notes


def _scrub_descriptions(lines: list[str] | None) -> list[str]:
    desc: list[str] = []
    seen: set[str] = set()
    for line in lines or []:
        cleaned = _public_description_line(str(line))
        if cleaned and cleaned not in seen:
            desc.append(cleaned)
            seen.add(cleaned)
    return desc


def enrich_row(row: dict) -> dict:
    row = dict(row)
    ielts = _ielts_from_row(row)
    if not ielts and row.get("ieltsOverall"):
        ielts = (str(row["ieltsOverall"]), str(row.get("ieltsSection") or ""))

    if not ielts or not ielts[0]:
        row["description"] = _scrub_descriptions(row.get("description"))
        return row

    tests, table_notes = build_test_requirements(ielts[0], ielts[1])
    if tests:
        row["TestRequirements"] = tests

    desc = _scrub_descriptions(row.get("description"))
    seen = set(desc)
    for note in table_notes:
        cleaned = _public_description_line(note)
        if cleaned and cleaned not in seen:
            desc.append(cleaned)
            seen.add(cleaned)
    row["description"] = desc
    row.pop("ieltsOverall", None)
    row.pop("ieltsSection", None)
    return row


def parse_english_md(path: Path) -> tuple[dict[str, str], list[dict]]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"(---\n.*?\n---\n)(.*)", text, re.S)
    if not m:
        raise ValueError(f"No frontmatter in {path}")
    front = m.group(1)
    body = m.group(2)
    json_m = re.search(r"\[\s*\{", body)
    if not json_m:
        raise ValueError(f"No JSON array in {path}")
    data = json.loads(body[json_m.start() :])
    meta: dict[str, str] = {}
    for line in front.splitlines():
        if line.startswith("source_") or line.startswith("university:") or line.startswith("cleaned_at:"):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, data


def write_english_md(path: Path, meta: dict[str, str], rows: list[dict]) -> None:
    lines = ["---"]
    for key in (
        "source_html",
        "source_pdf",
        "source_url",
        "source_pdf_url",
        "page_type",
        "university",
        "cleaned_at",
    ):
        if key in meta and meta[key]:
            lines.append(f"{key}: {meta[key]}")
    lines.append("---")
    body = "\n".join(lines) + "\n# English Language Requirements\n\n"
    body += json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    path.write_text(body, encoding="utf-8")


def merge_programmes(existing: list[dict], extras: list[dict]) -> list[dict]:
    seen = {str(r.get("ProgramName") or "") for r in existing}
    merged = list(existing)
    for extra in extras:
        name = str(extra.get("ProgramName") or "")
        if name and name not in seen:
            merged.append(extra)
            seen.add(name)
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Enrich english-requirements.md from ULaw PDF.")
    parser.add_argument("--english-md", type=Path, default=_DEFAULT_ENGLISH)
    parser.add_argument("--pdf", type=Path, default=_DEFAULT_PDF, help="PDF path (metadata only)")
    args = parser.parse_args(argv)

    english_path = args.english_md.resolve()
    if not english_path.is_file():
        print(f"Missing {english_path}; run convert_country_entry_html.py first.", file=sys.stderr)
        return 1
    if not args.pdf.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    meta, rows = parse_english_md(english_path)
    rows = merge_programmes(rows, PDF_EXTRA_PROGRAMMES)
    extra_by_name = {str(p["ProgramName"]): p for p in PDF_EXTRA_PROGRAMMES}

    enriched = []
    for row in rows:
        row = dict(row)
        name = str(row.get("ProgramName") or "")
        if name == CERT_HE_PROGRAM and not _ielts_from_row(row):
            row["ieltsOverall"], row["ieltsSection"] = CERT_HE_IELTS
            if not any("LLB (Hons)" in str(d) for d in row.get("description") or []):
                row.setdefault("description", []).append(
                    "Same English requirement as LLB (Hons) / Top-Up programmes: IELTS 6.5 (6.0)."
                )
        extra = extra_by_name.get(name)
        if extra and not _ielts_from_row(row):
            row["ieltsOverall"] = extra.get("ieltsOverall")
            row["ieltsSection"] = extra.get("ieltsSection")
        enriched.append(enrich_row(row))

    meta["source_pdf"] = _PDF_SOURCE_REL
    meta["source_pdf_url"] = _PDF_SOURCE_URL
    meta["cleaned_at"] = date.today().isoformat()

    write_english_md(english_path, meta, enriched)
    print(f"Updated {english_path} ({len(enriched)} programmes, PTE/TOEFL from PDF Table 2)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
