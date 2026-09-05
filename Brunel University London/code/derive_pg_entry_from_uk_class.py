#!/usr/bin/env python3
"""Derive Brunel Bangladesh BSc entry requirements from UK degree class in course markdown.

Applies to **undergraduate**, **postgraduate**, and **postgraduate_research** courses
when the international entry block shows the standard Bangladesh bachelor line, e.g.:

  ``Bangladesh - Bachelor degree (4 years) or Master's Degree (...)``
  ``Institution Dependent - please check with admissions``

Combined with UK key-info class (e.g. ``2:2``), maps to BSc GPA on the 4.0 scale:

  - 2:2 → GPA 3.25
  - 2:1 → GPA 3.5
  - etc.

Clinical PG pages with a failed country tab default to 2:1 → GPA 3.5.

Usage (from repo root or this code/ directory):
  python derive_pg_entry_from_uk_class.py --dry-run
  python derive_pg_entry_from_uk_class.py --apply
  python derive_pg_entry_from_uk_class.py --apply --re-normalize
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_SHARED = Path(__file__).resolve().parents[2] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from normalize_admission_data import AdmissionRecordNormalizer
from uni_paths import resolve_code_dir, resolve_output_dir

UK_CLASS_ALIASES = {
    "first": "first",
    "1st": "first",
    "first class": "first",
    "first class honours": "first",
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
    "third": "third",
    "3rd": "third",
    "third class": "third",
    "third class honours": "third",
}

DERIVE_STUDY_LEVELS = frozenset(
    {"undergraduate", "postgraduate", "postgraduate_research"}
)

# UK class -> (metadata line, BSc grade for requirements[])
BRUNEL_BANGLADESH_BY_UK_CLASS: dict[str, tuple[str, str]] = {
    "first": (
        "A minimum score of 70% or 3.5/4.",
        "GPA 3.5",
    ),
    "2:1": (
        "A minimum score of 60% - 70% or 3.0/4 - 3.5/4.",
        "GPA 3.5",
    ),
    "2:2": (
        "A minimum score of 55% - 65% or 2.75/4 - 3.25/4.",
        "GPA 3.25",
    ),
    "third": (
        "A minimum score of 45% - 55% or 2.25/4 - 2.75/4.",
        "GPA 2.75",
    ),
}

INSTITUTION_DEPENDENT_RE = re.compile(
    r"institution\s+dependent|please\s+check\s+with\s+admissions",
    re.I,
)
COUNTRY_SELECTOR_FAILURE_RE = re.compile(
    r"select\s+your\s+country(?:/region)?|please\s+contact\s+admissions",
    re.I,
)
BANGLADESH_PG_QUAL_RE = re.compile(
    r"bangladesh\s*-\s*bachelor\s+degree\s*\(\s*4\s+years\s*\)",
    re.I,
)
CLINICAL_PG_SLUG_RE = re.compile(
    r"(?:advanced-clinical-practice|advanced-professional-practice)-",
    re.I,
)
STANDARD_BANGLADESH_QUAL = (
    "Bangladesh - Bachelor degree (4 years) or Master's Degree "
    "(when following a 3-year Bachelor Pass or 4-year Bachelor degree)"
)
UK_CLASS_LINE_RE = re.compile(r"^\s*(2:1|2:2|3:2|first class|upper second|lower second|third class)\s*\.?\s*$", re.I)
HTML_UK_CLASS_RE = re.compile(
    r"\b(?:first\s+class|upper\s+second|lower\s+second|third\s+class|2:1|2:2|3:2)\b",
    re.I,
)
UK_CLASS_TOKEN_RE = re.compile(
    r"\b(?:first\s+class(?:\s+honou?rs)?|upper\s+second(?:\s+class(?:\s+honou?rs)?)?|"
    r"lower\s+second(?:\s+class(?:\s+honou?rs)?)?|third\s+class(?:\s+honou?rs)?|"
    r"[123](?:st|nd|rd)|2:1|2:2|3:2)\b",
    re.I,
)
ENTRY_BLOCK_RE = re.compile(
    r"(?:^|\n)Entry requirements\s*\n+([^\n#][^\n]*(?:\n[^\n#][^\n]*){0,4})",
    re.I,
)


@dataclass(frozen=True)
class DerivedEntry:
    uk_class: str
    degree: str
    grade: str
    metadata_line: str
    md_path: Path
    course_url: str
    study_level: str


def split_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    if not markdown.startswith("---"):
        return {}, markdown
    end = markdown.find("\n---", 3)
    if end == -1:
        return {}, markdown
    header = markdown[3:end].strip()
    body = markdown[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def canonicalize_uk_class(raw: str) -> str | None:
    text = re.sub(r"\s+", " ", (raw or "").strip().lower())
    if not text:
        return None
    if text in UK_CLASS_ALIASES:
        return UK_CLASS_ALIASES[text]
    match = UK_CLASS_TOKEN_RE.search(text)
    if not match:
        return None
    token = match.group(0).lower()
    token = re.sub(r"\s+", " ", token)
    if token in UK_CLASS_ALIASES:
        return UK_CLASS_ALIASES[token]
    if token in {"2:1", "2:2", "3:2"}:
        return token
    return UK_CLASS_ALIASES.get(token)


def extract_international_entry_section(body: str) -> str:
    section_match = re.search(
        r"## International entry requirements\s*\n+(.*?)(?=\n## |\Z)",
        body,
        re.S | re.I,
    )
    return section_match.group(1) if section_match else ""


def resolve_course_html_path(md_path: Path, meta: dict[str, str], output_dir: Path) -> Path | None:
    source_html = meta.get("source_html", "").strip()
    if source_html:
        candidate = output_dir / source_html.replace("/", "\\")
        if candidate.is_file():
            return candidate
        candidate = output_dir.parent / source_html
        if candidate.is_file():
            return candidate
    slug = md_path.stem
    pages_dir = output_dir / "course_pages"
    if pages_dir.is_dir():
        matches = sorted(pages_dir.glob(f"*{slug}*.html"), key=lambda p: len(p.name))
        if matches:
            return matches[0]
    return None


def extract_uk_entry_class_from_html(html_path: Path) -> str | None:
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    entry_match = re.search(
        r'id="entryRequirements"[^>]*>(.*?)(?=id="fees"|id="teaching"|</main>)',
        text,
        re.S | re.I,
    )
    haystack = entry_match.group(1) if entry_match else text
    for match in HTML_UK_CLASS_RE.finditer(haystack):
        uk_class = canonicalize_uk_class(match.group(0))
        if uk_class:
            return uk_class
    return None


def extract_uk_entry_class(
    markdown: str,
    *,
    md_path: Path | None = None,
    output_dir: Path | None = None,
    course_url: str = "",
) -> str | None:
    """Read UK entry class (e.g. 2:2, 2:1) from Brunel course markdown or saved HTML."""
    meta, body = split_frontmatter(markdown)
    match = ENTRY_BLOCK_RE.search(body)
    if match:
        block = match.group(1)
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if any(
                skip in lowered
                for skip in (
                    "a-level",
                    "btec",
                    "ib)",
                    "see specific",
                    "ucas",
                    "tariff",
                    "health profession",
                    "clinical work experience",
                    "pre-registration",
                )
            ):
                continue
            uk_class = canonicalize_uk_class(stripped)
            if uk_class:
                return uk_class

    uk_section = re.search(
        r"## UK entry requirements\s*\n+(.*?)(?=\n## |\Z)",
        body,
        re.S | re.I,
    )
    if uk_section:
        for line in uk_section.group(1).splitlines():
            uk_class = canonicalize_uk_class(line.strip())
            if uk_class:
                return uk_class
        for match in HTML_UK_CLASS_RE.finditer(uk_section.group(1)):
            uk_class = canonicalize_uk_class(match.group(0))
            if uk_class:
                return uk_class

    for line in body.splitlines():
        if UK_CLASS_LINE_RE.match(line):
            uk_class = canonicalize_uk_class(line.strip())
            if uk_class:
                return uk_class

    if md_path and output_dir:
        html_path = resolve_course_html_path(md_path, meta, output_dir)
        if html_path:
            uk_class = extract_uk_entry_class_from_html(html_path)
            if uk_class:
                return uk_class

    intl_section = extract_international_entry_section(body)
    if COUNTRY_SELECTOR_FAILURE_RE.search(intl_section):
        slug = course_url or meta.get("course_url", "") or md_path.stem if md_path else ""
        study_level = meta.get("study_level", "").strip().lower()
        if study_level == "postgraduate" and CLINICAL_PG_SLUG_RE.search(slug):
            return "2:1"
    return None


def is_brunel_derive_candidate(markdown: str) -> bool:
    meta, body = split_frontmatter(markdown)
    study_level = meta.get("study_level", "").strip().lower()
    if study_level not in DERIVE_STUDY_LEVELS:
        return False
    if "## International entry requirements" not in body:
        return False
    section = extract_international_entry_section(body)
    if INSTITUTION_DEPENDENT_RE.search(section):
        return True
    if BANGLADESH_PG_QUAL_RE.search(section):
        return True
    return bool(COUNTRY_SELECTOR_FAILURE_RE.search(section))


def is_brunel_pg_derive_candidate(markdown: str) -> bool:
    return is_brunel_derive_candidate(markdown)


def brunel_bangladesh_requirement(uk_class: str) -> tuple[dict[str, str], str] | None:
    canonical = canonicalize_uk_class(uk_class)
    if not canonical:
        return None
    mapping = BRUNEL_BANGLADESH_BY_UK_CLASS.get(canonical)
    if not mapping:
        return None
    metadata_line, grade = mapping
    return {"degree": "BSc", "grade": grade}, metadata_line


def brunel_pg_bangladesh_requirement(uk_class: str) -> tuple[dict[str, str], str] | None:
    return brunel_bangladesh_requirement(uk_class)


def derive_from_markdown(md_path: Path, *, output_dir: Path | None = None) -> DerivedEntry | None:
    markdown = md_path.read_text(encoding="utf-8")
    meta, _ = split_frontmatter(markdown)
    study_level = meta.get("study_level", "").strip().lower()
    if study_level not in DERIVE_STUDY_LEVELS:
        return None
    if not is_brunel_derive_candidate(markdown):
        return None
    uk_class = extract_uk_entry_class(
        markdown,
        md_path=md_path,
        output_dir=output_dir,
        course_url=meta.get("course_url", ""),
    )
    if not uk_class:
        return None
    mapped = brunel_bangladesh_requirement(uk_class)
    if not mapped:
        return None
    requirement, metadata_line = mapped
    return DerivedEntry(
        uk_class=uk_class,
        degree=requirement["degree"],
        grade=requirement["grade"],
        metadata_line=metadata_line,
        md_path=md_path,
        course_url=meta.get("course_url", ""),
        study_level=study_level,
    )


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _entry_metadata(derived: DerivedEntry, existing: object) -> list[dict[str, object]]:
    lines = [derived.metadata_line]
    qual_match = re.search(
        r"#####\s*(Bangladesh[^\n]+)",
        derived.md_path.read_text(encoding="utf-8"),
        re.I,
    )
    if qual_match:
        lines.insert(0, qual_match.group(1).strip())
    else:
        lines.insert(0, STANDARD_BANGLADESH_QUAL)
    return [{"subtitle": "Entry Requirements", "description": lines}]


def apply_to_course_json(
    audit_dir: Path,
    derived: DerivedEntry,
) -> bool:
    requirement = {"degree": derived.degree, "grade": derived.grade}
    metadata = _entry_metadata(derived, None)
    changed = False

    for name in (
        "entry_requirement_parsed.json",
        "stage2_llm_parsed.json",
        "stage2_parsed.json",
        "output.json",
    ):
        path = audit_dir / name
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        data["requirements"] = [requirement]
        changed = True
        if name in {"entry_requirement_parsed.json", "stage2_llm_parsed.json"}:
            data["AcademicRequirementsMetaData"] = metadata
        if name in {"stage2_parsed.json", "output.json"}:
            academic = data.get("AcademicRequirementsMetaData")
            english = [
                item
                for item in (academic or [])
                if isinstance(item, dict)
                and str(item.get("subtitle", "")).strip().lower() == "english requirement"
            ]
            data["AcademicRequirementsMetaData"] = metadata + english
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def find_audit_dir(output_dir: Path, derived: DerivedEntry) -> Path | None:
    slug = _slug_from_url(derived.course_url)
    if not slug:
        slug = derived.md_path.stem
    level = derived.study_level or "postgraduate"
    candidate = output_dir / "extracted" / level / slug
    if candidate.is_dir():
        return candidate
    for path in (output_dir / "extracted").rglob(slug):
        if path.is_dir() and (path / "output.json").is_file():
            return path
    return None


def scan_courses(courses_dir: Path, *, output_dir: Path) -> list[DerivedEntry]:
    derived_rows: list[DerivedEntry] = []
    for md_path in sorted(courses_dir.rglob("*.md")):
        if md_path.parent.name not in DERIVE_STUDY_LEVELS:
            continue
        derived = derive_from_markdown(md_path, output_dir=output_dir)
        if derived:
            derived_rows.append(derived)
    return derived_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive Brunel UG/PG/PGR Bangladesh BSc requirements from UK class in course markdown.",
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        default=".",
        help="Brunel code/ directory (default: cwd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print derived rows only (default when --apply is omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Patch extracted/*/entry_requirement_parsed.json, stage2_*.json, output.json",
    )
    parser.add_argument(
        "--re-normalize",
        action="store_true",
        help="After --apply, rewrite extracted/*/normalized.json from output.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N matching courses",
    )
    return parser


def apply_enrichments(
    code_dir: Path,
    *,
    re_normalize: bool = False,
    dry_run: bool = False,
    limit: int | None = None,
) -> int:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    courses_dir = output_dir / "clean" / "courses"
    if not courses_dir.is_dir():
        print(f"Missing courses markdown dir: {courses_dir}", file=sys.stderr)
        return 0

    derived_rows = scan_courses(courses_dir, output_dir=output_dir)
    if limit is not None:
        derived_rows = derived_rows[:limit]
    if not derived_rows:
        return 0

    patched = 0
    normalizer = AdmissionRecordNormalizer()
    print(f"Found {len(derived_rows)} course(s) to derive (UG/PG/PGR).")
    for derived in derived_rows:
        print(
            f"- [{derived.study_level}] {derived.md_path.name}: UK {derived.uk_class} -> "
            f"{derived.degree} / {derived.grade}"
        )
        if dry_run:
            continue
        audit_dir = find_audit_dir(output_dir, derived)
        if not audit_dir:
            print(f"  ! no extracted audit dir for {derived.course_url or derived.md_path.stem}")
            continue
        if apply_to_course_json(audit_dir, derived):
            patched += 1
            if re_normalize:
                output_json = audit_dir / "output.json"
                if output_json.is_file():
                    raw = json.loads(output_json.read_text(encoding="utf-8"))
                    normalized = normalizer.process_record(raw)
                    (audit_dir / "normalized.json").write_text(
                        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
    if dry_run:
        print("Dry run only. Pass --apply to patch extracted JSON.")
        return len(derived_rows)
    elif re_normalize:
        print(f"Patched {patched} course(s); rewrote normalized.json.")
    else:
        print(f"Patched {patched} course(s).")
    return patched


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = args.dry_run or not args.apply
    count = apply_enrichments(
        Path(args.code_dir),
        re_normalize=args.re_normalize,
        dry_run=dry_run,
        limit=args.limit,
    )
    if count == 0 and dry_run:
        print("No matching Brunel UG/PG/PGR derive-candidate courses found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
