"""Map ULaw course markdown → english-requirements.md programme row."""

from __future__ import annotations

import json
import re
from pathlib import Path

SUBJECT_FROM_URL = {
    "business": "Business",
    "law": "Law",
    "criminology": "Criminology",
    "computer-science": "Computer Science",
    "psychology": "Psychology",
    "education": "Education",
}


def load_english_programs(english_md: Path) -> list[dict]:
    text = english_md.read_text(encoding="utf-8")
    start = text.index("[")
    data = json.loads(text[start:])
    return data if isinstance(data, list) else []


def subject_from_course_url(url: str) -> str:
    match = re.search(r"/study/(?:undergraduate|postgraduate)/([^/]+)/", url or "", re.I)
    if not match:
        return ""
    key = match.group(1).lower()
    return SUBJECT_FROM_URL.get(key, key.replace("-", " ").title())


def _pick(programs: list[dict], **filters: str) -> dict | None:
    for program in programs:
        if not isinstance(program, dict):
            continue
        ok = True
        for key, value in filters.items():
            if str(program.get(key, "") or "").strip() != value:
                ok = False
                break
        if ok:
            return program
    return None


def _pick_name_contains(
    programs: list[dict],
    *,
    study_level: str,
    subject: str,
    needle: str,
) -> dict | None:
    needle_l = needle.casefold()
    for program in programs:
        if program.get("TestStudyLevel") != study_level:
            continue
        if str(program.get("subjectArea", "")).casefold() != subject.casefold():
            continue
        if needle_l in str(program.get("ProgramName", "")).casefold():
            return program
    return None


def match_english_program(
    programs: list[dict],
    *,
    study_level: str,
    course_url: str,
    title: str,
) -> dict | None:
    subject = subject_from_course_url(course_url)
    if not subject:
        return None

    title_l = (title or "").casefold()
    slug = (course_url or "").casefold()

    if study_level == "postgraduate":
        if subject == "Law":
            if "pgdl" in slug or "pg-dip" in title_l or "postgraduate diploma" in title_l:
                return _pick_name_contains(programs, study_level="Postgraduate", subject="Law", needle="Postgraduate Diploma")
            if "/lpc" in slug or "legal practice course" in title_l:
                return _pick_name_contains(programs, study_level="Postgraduate", subject="Law", needle="Legal Practice Course")
            if "/bpc" in slug or "bar practice" in title_l:
                return _pick_name_contains(programs, study_level="Postgraduate", subject="Law", needle="Bar Practice Course")
            if "ma-law" in slug or re.match(r"^ma law\b", title_l):
                return _pick_name_contains(programs, study_level="Postgraduate", subject="Law", needle="MA Law")
            return _pick_name_contains(programs, study_level="Postgraduate", subject="Law", needle="LLM")
        for needle in ("Master", "MSc", "MA", "PGCert", subject):
            hit = _pick_name_contains(
                programs,
                study_level="Postgraduate",
                subject=subject,
                needle=needle,
            )
            if hit:
                return hit
        return None

    # foundation folder + foundation year titles → foundation-year programme row
    is_foundation = study_level == "foundation" or "foundation year" in title_l
    is_blended = "blended" in title_l or "blended" in slug

    if subject == "Law":
        if "senior-status" in slug or "senior status" in title_l:
            return _pick_name_contains(programs, study_level="Undergraduate", subject="Law", needle="Senior Status")
        if "accelerated" in slug or "accelerated" in title_l:
            return _pick_name_contains(programs, study_level="Undergraduate", subject="Law", needle="Accelerated")
        if "top-up" in slug or "top up" in title_l:
            return _pick_name_contains(programs, study_level="Undergraduate", subject="Law", needle="Top-Up")
        if "mlaw" in slug or "solicitors" in title_l:
            return _pick_name_contains(programs, study_level="Undergraduate", subject="Law", needle="MLaw")
        if is_foundation:
            if is_blended:
                return _pick_name_contains(
                    programs, study_level="Undergraduate", subject="Law", needle="Foundation (Blended)"
                )
            return _pick_name_contains(
                programs, study_level="Undergraduate", subject="Law", needle="Degrees with Foundation Year"
            )
        return _pick_name_contains(programs, study_level="Undergraduate", subject="Law", needle="LLB (Hons) Law")

    if is_foundation:
        if is_blended:
            return _pick_name_contains(
                programs,
                study_level="Undergraduate",
                subject=subject,
                needle="Foundation (Blended)",
            )
        return _pick_name_contains(
            programs,
            study_level="Undergraduate",
            subject=subject,
            needle="Degrees with Foundation Year",
        )

    if "top-up" in slug or "top up" in title_l:
        return _pick_name_contains(
            programs,
            study_level="Undergraduate",
            subject=subject,
            needle="Top-Up",
        )

    return _pick_name_contains(
        programs,
        study_level="Undergraduate",
        subject=subject,
        needle="Three Year",
    )


def duration_display_from_program(program: dict) -> str:
    """Stage-1-friendly duration when the matched programme row supports it."""
    raw = str(program.get("duration") or "").strip()
    for line in program.get("description") or []:
        text = str(line).strip()
        if text.lower().startswith("duration:"):
            raw = text.split(":", 1)[1].strip()
            break

    if raw.casefold() in {"", "on campus", "blended"}:
        name = str(program.get("ProgramName") or "")
        if "Three Year" in name:
            return "3 years"
        if "Degrees with Foundation Year" in name and "Blended" not in name:
            return "4 years"
        return ""

    if raw.casefold() == "one year":
        return "1 year"

    year_match = re.search(r"(\d+)\s*year", raw, re.I)
    if year_match:
        n = year_match.group(1)
        return f"{n} year" if n == "1" else f"{n} years"

    month_match = re.search(r"(\d+(?:\.\d+)?)\s*month", raw, re.I)
    if month_match:
        value = month_match.group(1).rstrip("0").rstrip(".")
        return f"{value} months"

    if re.search(r"solicitors", raw, re.I):
        return ""

    return ""
