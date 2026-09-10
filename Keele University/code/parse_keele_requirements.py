"""Normalize messy Keele entry_requirement_parsed.json requirements to {degree, grade}."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_SHARED = _CODE_DIR.parents[1] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import canonicalize_requirement_degree, extract_grade_from_requirement_text  # noqa: E402

from keele_bangladesh_rules import (  # noqa: E402
    ALIM_HSC_RE,
    detect_uk_class,
    foundation_default_requirement,
    pg_requirement_for_uk_class,
    undergraduate_default_requirement,
)

FOUNDATION_LEVELS = frozenset({"foundation"})
UG_LEVELS = frozenset({"undergraduate"})
PG_LEVELS = frozenset({"postgraduate", "postgraduate_research"})


def _norm_keys(entry: dict) -> dict[str, object]:
    return {str(key).strip().lower(): value for key, value in entry.items()}


def _as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_as_text(item) for item in value]
        return " ".join(part for part in parts if part)
    if isinstance(value, dict):
        return " ".join(_as_text(item) for item in value.values())
    return str(value).strip()


def _clean_grade(grade: str) -> str:
    value = (grade or "").strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"([%\d])\.+$", r"\1", value)
    return value.strip()


def _append_unique(items: list[dict[str, str]], degree: str, grade: str) -> None:
    degree = (degree or "").strip()
    grade = _clean_grade(grade)
    if not degree or not grade:
        return
    pair = {"degree": degree, "grade": grade}
    if pair not in items:
        items.append(pair)


def _degree_from_text(text: str, *, study_level: str) -> str:
    blob = text or ""
    mapped = canonicalize_requirement_degree(blob)
    if mapped and mapped in {
        "HSC",
        "Diploma",
        "BA",
        "BSc",
        "BBA",
        "BEng",
        "BCom",
        "MA",
        "MSc",
        "MBA",
        "PhD",
    }:
        return mapped
    if ALIM_HSC_RE.search(blob):
        return "HSC"
    if re.search(r"\bdiploma\b", blob, re.I):
        return "Diploma"
    if study_level in PG_LEVELS or re.search(r"\b(?:bachelor|master)\b", blob, re.I):
        return "BSc"
    if study_level in UG_LEVELS or re.search(r"\b2\s+year\s+undergraduate\b", blob, re.I):
        return "BA"
    if study_level in FOUNDATION_LEVELS:
        return "HSC"
    return mapped or ""


def _looks_like_grade(value: str) -> bool:
    if not value:
        return False
    if re.search(r"(?:CGPA|GPA)\s*[\d.]+", value, re.I):
        return True
    if re.search(r"\d+\s*%", value):
        return True
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", value.strip()))


def _grade_from_text(text: str, degree: str, *, study_level: str) -> str:
    uk_class = detect_uk_class(text)
    if uk_class and (study_level in PG_LEVELS or degree in {"BSc", "BA", "MSc", "MA", "MBA", "PhD"}):
        mapped = pg_requirement_for_uk_class(uk_class)
        if mapped:
            return mapped[1]
    grade = extract_grade_from_requirement_text(text)
    if _looks_like_grade(grade):
        return grade
    if study_level in FOUNDATION_LEVELS and ALIM_HSC_RE.search(text):
        return foundation_default_requirement()[1]
    if study_level in UG_LEVELS and ALIM_HSC_RE.search(text):
        return undergraduate_default_requirement(text)[1]
    return ""


def _parse_text_blob(text: str, *, study_level: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if not text.strip():
        return items

    uk_class = detect_uk_class(text)
    if uk_class and study_level in PG_LEVELS:
        mapped = pg_requirement_for_uk_class(uk_class)
        if mapped:
            _append_unique(items, *mapped)
            return items

    if study_level in FOUNDATION_LEVELS and (ALIM_HSC_RE.search(text) or "foundation" in text.lower()):
        _append_unique(items, *foundation_default_requirement())
        return items

    if ALIM_HSC_RE.search(text):
        degree, grade = (
            undergraduate_default_requirement(text)
            if study_level in UG_LEVELS
            else foundation_default_requirement()
        )
        _append_unique(items, degree, grade)

    if re.search(r"2\s+year\s+undergraduate", text, re.I):
        degree, grade = undergraduate_default_requirement(text)
        _append_unique(items, degree, grade)

    cgpa = re.search(r"CGPA\s*(?:of\s+)?([\d.]+)", text, re.I)
    pct = re.search(r"(\d+)\s*%", text)
    if cgpa or pct:
        degree = _degree_from_text(text, study_level=study_level)
        grade = _grade_from_text(text, degree, study_level=study_level)
        _append_unique(items, degree, grade)

    return items


def _parse_dict_entry(entry: dict, *, study_level: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    data = _norm_keys(entry)

    if "degrees" in data and isinstance(data["degrees"], list):
        for child in data["degrees"]:
            if isinstance(child, dict):
                items.extend(_parse_dict_entry(child, study_level=study_level))
            elif isinstance(child, str):
                items.extend(_parse_text_blob(child, study_level=study_level))
        if items:
            return items

    degree_raw = _as_text(data.get("degree", ""))
    grade_raw = _as_text(data.get("grade", ""))
    qualification = _as_text(data.get("qualification", ""))
    description = _as_text(data.get("description", ""))
    requirement = _as_text(data.get("requirement", ""))
    requirements = data.get("requirements", "")
    entry_requirements = data.get("entryrequirements", data.get("entry_requirements", ""))

    combined = " ".join(
        part
        for part in (degree_raw, qualification, grade_raw, description, requirement, _as_text(requirements), _as_text(entry_requirements))
        if part
    )

    if isinstance(requirements, list):
        for child in requirements:
            if isinstance(child, dict):
                items.extend(_parse_dict_entry(child, study_level=study_level))
            else:
                items.extend(_parse_text_blob(_as_text(child), study_level=study_level))
        if items:
            return items

    if isinstance(entry_requirements, list):
        for child in entry_requirements:
            items.extend(_parse_text_blob(_as_text(child), study_level=study_level))
        if items:
            return items

    if isinstance(data.get("grades"), list):
        grade_raw = _as_text(data["grades"])
    elif data.get("grades") not in (None, ""):
        grade_raw = _as_text(data["grades"])

    degree = canonicalize_requirement_degree(degree_raw) if degree_raw else ""
    if not degree or degree.lower() == "foundation":
        degree = _degree_from_text(combined or qualification or description, study_level=study_level)
    grade = _grade_from_text(
        combined or grade_raw or qualification or description,
        degree,
        study_level=study_level,
    )
    if not grade and grade_raw:
        extracted = extract_grade_from_requirement_text(grade_raw)
        if _looks_like_grade(extracted):
            grade = extracted
    _append_unique(items, degree, grade)

    if not items and combined:
        items.extend(_parse_text_blob(combined, study_level=study_level))

    return items


def parse_keele_requirements(raw: object, *, study_level: str = "") -> list[dict[str, str]]:
    """Convert a Keele requirements payload into canonical {degree, grade} rows."""
    level = (study_level or "").strip().lower()
    items: list[dict[str, str]] = []

    if raw in (None, "", []):
        return items

    if isinstance(raw, str):
        return _parse_text_blob(raw, study_level=level)

    if not isinstance(raw, list):
        if isinstance(raw, dict):
            return _parse_dict_entry(raw, study_level=level)
        return items

    for entry in raw:
        if isinstance(entry, str):
            items.extend(_parse_text_blob(entry, study_level=level))
        elif isinstance(entry, dict):
            items.extend(_parse_dict_entry(entry, study_level=level))
        elif isinstance(entry, list):
            for child in entry:
                items.extend(parse_keele_requirements(child, study_level=level))

    deduped: list[dict[str, str]] = []
    for item in items:
        _append_unique(deduped, item.get("degree", ""), item.get("grade", ""))
    return deduped


def requirements_to_metadata_line(requirements: list[dict[str, str]]) -> str:
    if not requirements:
        return ""
    parts = [f"{item['degree']} {item['grade']}".strip() for item in requirements]
    return " | ".join(part for part in parts if part)
