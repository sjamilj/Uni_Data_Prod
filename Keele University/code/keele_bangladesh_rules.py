"""Keele Bangladesh entry mappings from output/clean/uni/bangladesh-entry.md."""

from __future__ import annotations

import re

KEELE_UK_CLASS_TO_PG: dict[str, tuple[str, str]] = {
    "2:1": ("BSc", "CGPA 3.0"),
    "2:2": ("BSc", "CGPA 2.8"),
}

UK_CLASS_ALIASES: dict[str, str] = {
    "first": "2:1",
    "first class": "2:1",
    "upper second": "2:1",
    "upper second class": "2:1",
    "upper second class honours": "2:1",
    "good honours": "2:1",
    "good honours degree": "2:1",
    "2:1": "2:1",
    "21": "2:1",
    "lower second": "2:2",
    "lower second class": "2:2",
    "lower second class honours": "2:2",
    "2:2": "2:2",
    "22": "2:2",
    "third": "2:2",
    "third class": "2:2",
}

KEELE_UK_PHRASES: tuple[tuple[str, str], ...] = (
    (r"good\s+honou?rs(?:\s+degree)?", "2:1"),
    (r"successful\s+completion", "2:2"),
    (r"\bupper\s+second\b", "2:1"),
    (r"\blower\s+second\b", "2:2"),
    (r"\b2:1\b", "2:1"),
    (r"\b2:2\b", "2:2"),
)

FOUNDATION_HSC: tuple[str, str] = ("HSC", "GPA 2.00")
UG_HSC: tuple[str, str] = ("HSC", "CGPA 5.0")
UG_TWO_YEAR: tuple[str, str] = ("BA", "60%")

UK_CLASS_TOKEN_RE = re.compile(
    r"\b(?:first\s+class(?:\s+honou?rs)?|upper\s+second(?:\s+class(?:\s+honou?rs)?)?|"
    r"lower\s+second(?:\s+class(?:\s+honou?rs)?)?|third\s+class(?:\s+honou?rs)?|"
    r"good\s+honou?rs(?:\s+degree)?|2:1|2:2)\b",
    re.I,
)

BACHELOR_ENTRY_RE = re.compile(
    r"\b(?:bachelor|master'?s?|postgraduate|mphil|phd|research)\b",
    re.I,
)
ALIM_HSC_RE = re.compile(r"\b(?:alim|hsc|higher\s+secondary\s+certificate|dakhil)\b", re.I)
DIPLOMA_ENGINEERING_RE = re.compile(r"\b4\s+year(?:s)?\s+diploma\b", re.I)


def canonicalize_uk_class(raw: str) -> str | None:
    text = re.sub(r"\s+", " ", (raw or "").strip().lower())
    if not text:
        return None
    if text in UK_CLASS_ALIASES:
        return UK_CLASS_ALIASES[text]
    match = UK_CLASS_TOKEN_RE.search(text)
    if not match:
        return None
    token = re.sub(r"\s+", " ", match.group(0).lower())
    return UK_CLASS_ALIASES.get(token, token if token in {"2:1", "2:2"} else None)


def detect_uk_class(text: str) -> str | None:
    if not text:
        return None
    for pattern, uk_class in KEELE_UK_PHRASES:
        if re.search(pattern, text, re.I):
            return uk_class
    return canonicalize_uk_class(text)


def pg_requirement_for_uk_class(uk_class: str) -> tuple[str, str] | None:
    return KEELE_UK_CLASS_TO_PG.get(uk_class)


def foundation_default_requirement() -> tuple[str, str]:
    return FOUNDATION_HSC


def undergraduate_default_requirement(text: str = "") -> tuple[str, str]:
    if re.search(r"2\s+year\s+undergraduate", text, re.I):
        return UG_TWO_YEAR
    if ALIM_HSC_RE.search(text):
        return UG_HSC
    return UG_HSC


def level_default_requirement(study_level: str, text: str = "") -> tuple[str, str] | None:
    level = (study_level or "").strip().lower()
    if level == "foundation":
        if ALIM_HSC_RE.search(text) or DIPLOMA_ENGINEERING_RE.search(text):
            return foundation_default_requirement()
        return foundation_default_requirement()
    if level == "undergraduate":
        return undergraduate_default_requirement(text)
    return None


def pg_fallback_from_markdown(body: str) -> tuple[str, str] | None:
    if not BACHELOR_ENTRY_RE.search(body):
        return None
    uk_class = detect_uk_class(body)
    if not uk_class:
        uk_class = "2:2"
    return pg_requirement_for_uk_class(uk_class)
