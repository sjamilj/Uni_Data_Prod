#!/usr/bin/env python3
"""Backfill Massey normalized course fields from saved clean markdown.

This script is deterministic and offline: it never invokes an LLM or downloads
course pages. It fills missing GPA, intake, duration, tuition and currency
values when they are explicitly supported by the associated clean markdown.
Whenever tuition is present, initialDeposit is set to the tuition amount.

Run from the repository root after academic normalization:
    python shared/normalize_admission_data.py "Massey University"
    python "Massey University/code/backfill_normalized.py"
    python shared/export_dev_courses.py --code-dir "Massey University/code"
"""

from __future__ import annotations

import json
import re
from pathlib import Path


UNIVERSITY_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = UNIVERSITY_DIR / "output"
EXTRACTED_DIR = OUTPUT_DIR / "extracted"
CLEAN_DIR = OUTPUT_DIR / "clean"

# Verified against Massey's saved course page and current selected-entry dates.
COURSE_OVERRIDES: dict[str, dict[str, str]] = {
    "study-all-qualifications-and-degrees-executive-master-of-business-administration-pmbsa": {
        "intakeInfo": "Semester One 2027",
        "courseDuration": "2 years part-time",
        "tuitionFee": "82800",
        "currency": "NZD",
        "minGpa": "3.00/4.00",
    },
}

MONEY_RE = re.compile(r"(?:NZ\s*\$|\$\s*NZD|NZD\s*\$|\$)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
GPA_RE = re.compile(r"\b(\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?)\b")


def _clean_markdown_path(normalized_path: Path) -> Path | None:
    relative = normalized_path.parent.relative_to(EXTRACTED_DIR)
    if relative.parts and relative.parts[0] == "pre_setup_course_extracted":
        level = relative.parts[1] if len(relative.parts) > 1 else ""
        slug = relative.parts[2] if len(relative.parts) > 2 else ""
        candidates = [CLEAN_DIR / "pre_setup_course" / level / f"{slug}.md"]
    else:
        level = relative.parts[0] if relative.parts else ""
        slug = relative.parts[1] if len(relative.parts) > 1 else ""
        candidates = [
            CLEAN_DIR / "courses" / level / f"{slug}.md",
            CLEAN_DIR / "pre_setup_course" / level / f"{slug}.md",
        ]
    return next((path for path in candidates if path.is_file()), None)


def _body(markdown: str) -> str:
    if markdown.startswith("---"):
        parts = markdown.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return markdown


def _section(text: str, heading: str) -> str:
    match = re.search(
        rf"(?ims)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
    )
    return match.group(1) if match else ""


def _extract_gpa(record: dict, text: str) -> str:
    blocks = record.get("AcademicRequirementsMetaData") or []
    if isinstance(blocks, dict):
        blocks = [blocks]
    candidates = []
    for block in blocks:
        if isinstance(block, dict):
            description = block.get("description", [])
            candidates.extend(description if isinstance(description, list) else [description])
    for candidate in [*candidates, text]:
        match = GPA_RE.search(str(candidate or ""))
        if match:
            return re.sub(r"\s+", "", match.group(1))
    return ""


def _extract_duration(text: str) -> str:
    # Prefer the explicitly labelled completion duration over narrative claims.
    match = re.search(
        r"(?ims)^#{2,4}\s+Time to complete\s*$\n((?:(?!^#{1,6}\s).+\n?){1,4})",
        text,
    )
    if match:
        value = " ".join(line.strip() for line in match.group(1).splitlines() if line.strip())
        value = re.sub(r"\s+Part-time available\b", "", value, flags=re.I).strip()
        if value:
            return value
    match = re.search(
        r"\b(\d+\s+(?:years?|months?)(?:\s+of)?\s+(?:part-time|full-time)(?:\s+study)?)\b",
        text,
        re.I,
    )
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _extract_tuition(text: str) -> tuple[str, str]:
    fees = _section(text, "Fees and scholarships")
    if not fees:
        fees = text
    for line in fees.splitlines():
        if not re.search(r"international\s+students?", line, re.I):
            continue
        match = MONEY_RE.search(line)
        if match:
            amount = match.group(1).replace(",", "")
            amount = amount.rstrip("0").rstrip(".") if "." in amount else amount
            return amount, "NZD"
    return "", ""


def _extract_intake(text: str) -> str:
    # Do not mistake application closing dates for course start dates.
    patterns = (
        r"(?im)^\s*(?:intake|start(?: date|s)?)\s*:\s*(?!application)([^\n]+)",
        r"(?im)^\s*(?:course )?start date\s*[-:]\s*([^\n]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = re.sub(r"\s+", " ", match.group(1)).strip(" -*")
            if value and not re.search(r"application|closing|due date", value, re.I):
                return value
    return ""


def _apply(path: Path) -> tuple[bool, list[str]]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"SKIP {path.relative_to(OUTPUT_DIR)}: {exc}")
        return False, []
    if not isinstance(record, dict):
        return False, []

    markdown_path = _clean_markdown_path(path)
    text = _body(markdown_path.read_text(encoding="utf-8")) if markdown_path else ""
    slug = path.parent.name
    fields = {
        "minGpa": _extract_gpa(record, text),
        "intakeInfo": _extract_intake(text),
        "courseDuration": _extract_duration(text),
    }
    fee, currency = _extract_tuition(text)
    fields.update(tuitionFee=fee, currency=currency)
    fields.update(COURSE_OVERRIDES.get(slug, {}))

    changed: list[str] = []
    for key, value in fields.items():
        if value and not str(record.get(key) or "").strip():
            record[key] = value
            changed.append(key)
    tuition = str(record.get("tuitionFee") or "").strip()
    if tuition and str(record.get("initialDeposit") or "").strip() != tuition:
        record["initialDeposit"] = tuition
        changed.append("initialDeposit")

    if changed:
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return bool(changed), changed


def main() -> int:
    if not EXTRACTED_DIR.is_dir():
        raise SystemExit(f"No extracted directory found: {EXTRACTED_DIR}")
    paths = sorted(EXTRACTED_DIR.rglob("normalized.json"))
    updated = 0
    field_counts: dict[str, int] = {}
    missing_counts: dict[str, int] = {}
    for path in paths:
        changed, fields = _apply(path)
        if changed:
            updated += 1
            print(f"Updated {path.relative_to(OUTPUT_DIR)}: {', '.join(fields)}")
            for field in fields:
                field_counts[field] = field_counts.get(field, 0) + 1
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(record, dict):
            for field in ("minGpa", "intakeInfo", "courseDuration", "tuitionFee", "currency"):
                if not str(record.get(field) or "").strip():
                    missing_counts[field] = missing_counts.get(field, 0) + 1
    print(f"Updated {updated} / {len(paths)} normalized.json files")
    if field_counts:
        print("Fields updated: " + ", ".join(f"{key}={value}" for key, value in sorted(field_counts.items())))
    if missing_counts:
        print("Still blank (not found in saved sources): " + ", ".join(f"{key}={value}" for key, value in sorted(missing_counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
