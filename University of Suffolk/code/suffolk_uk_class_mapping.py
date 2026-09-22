"""University of Suffolk — UK honours class → Bangladesh BSc GPA (postgraduate entry).

Maps course-page UK requirements (2:1 / 2:2) to 4-year bachelor's GPA strings
aligned with output/clean/uni/bangladesh-entry.md (PG minimum 2.75 GPA baseline).
"""

from __future__ import annotations

import re

SUFFOLK_UK_CLASS_TO_BSC_GRADE: dict[str, str] = {
    "2:1": "GPA 3.0",
    "2:2": "GPA 2.75",
}

UK_CLASS_ALIASES: dict[str, str] = {
    "first": "2:1",
    "first class": "2:1",
    "upper second": "2:1",
    "upper second class": "2:1",
    "upper second class honours": "2:1",
    "2:1": "2:1",
    "21": "2:1",
    "lower second": "2:2",
    "lower second class": "2:2",
    "lower second class honours": "2:2",
    "2:2": "2:2",
    "22": "2:2",
}

UK_CLASS_TOKEN_RE = re.compile(
    r"\b(?:first\s+class(?:\s+honou?rs)?|upper\s+second(?:\s+class(?:\s+honou?rs)?)?|"
    r"lower\s+second(?:\s+class(?:\s+honou?rs)?)?|2:1|2:2)\b",
    re.I,
)
UK_CLASS_LINE_RE = re.compile(
    r"^\s*(2:1|2:2|first class|upper second|lower second)\s*\.?\s*$",
    re.I,
)
ENTRY_BLOCK_RE = re.compile(
    r"(?:^|\n)##\s*Entry requirements\s*\n+(.*?)(?=\n## |\Z)",
    re.S | re.I,
)


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
    mapped = UK_CLASS_ALIASES.get(token, token)
    return mapped if mapped in SUFFOLK_UK_CLASS_TO_BSC_GRADE else None


def extract_uk_entry_class_from_text(body: str) -> str | None:
    entry_match = ENTRY_BLOCK_RE.search(body)
    haystacks = [entry_match.group(1)] if entry_match else []
    haystacks.append(body)
    for haystack in haystacks:
        for line in haystack.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if UK_CLASS_LINE_RE.match(stripped):
                uk = canonicalize_uk_class(stripped)
                if uk:
                    return uk
            uk = canonicalize_uk_class(stripped)
            if uk:
                return uk
        for match in UK_CLASS_TOKEN_RE.finditer(haystack):
            uk = canonicalize_uk_class(match.group(0))
            if uk:
                return uk
    return None


def suffolk_bangladesh_requirement(uk_class: str) -> tuple[dict[str, str], str] | None:
    canonical = canonicalize_uk_class(uk_class)
    if not canonical:
        return None
    grade = SUFFOLK_UK_CLASS_TO_BSC_GRADE.get(canonical)
    if not grade:
        return None
    metadata = (
        f"UK {canonical} — 4-year Bangladesh bachelor's degree: {grade} "
        f"(University of Suffolk postgraduate entry mapping)."
    )
    return {"degree": "BSc", "grade": grade}, metadata
