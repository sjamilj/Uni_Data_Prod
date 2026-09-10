#!/usr/bin/env python3
"""Derive Brunel undergraduate HSC entry from A-level requirements + bangladesh-entry.md.

Reads ``output/clean/uni/bangladesh-entry.md`` for:

- Standard A-level combo → HSC CGPA (AAA=5.0, ABB=5.0, BBB=4.0, …)
- Brunel course-page A-level bands (e.g. ``ABB - BBB`` → GPA 5.0, ``BBB - BCC`` → GPA 4.75)

For each undergraduate course markdown, uses (in order):

1. Explicit ``GPA X/5`` in the Bangladesh international block on the course page
2. A-level band line from bangladesh-entry.md (e.g. ``ABB - BBB``)
3. Lower bound of an A-level range mapped via the standard combo table
4. Single A-level combo mapped via the standard combo table

Skips Brunel Pathway College courses (handled by ``derive_pathway_entry_from_bangladesh_md.py``).

Usage:
  python derive_ug_entry_from_bangladesh_md.py --dry-run
  python derive_ug_entry_from_bangladesh_md.py --apply
  python derive_ug_entry_from_bangladesh_md.py --apply --re-normalize
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

from normalize_admission_data import ALEVEL_TO_HSC_EQUIVALENT, AdmissionRecordNormalizer
from uni_paths import resolve_code_dir, resolve_output_dir

from derive_pathway_entry_from_bangladesh_md import is_pathway_course_url

ALEVEL_RANGE_RE = re.compile(
    r"\b([A-D]{3})\s*[-–]\s*([A-D]{3})\s*\(A-level\)",
    re.I,
)
ALEVEL_SINGLE_RE = re.compile(r"\b([A-D]{3})\s*\(A-level\)", re.I)
GPA_EXPLICIT_RE = re.compile(r"gpa\s*(\d+(?:\.\d+)?)\s*/\s*5", re.I)
BANGLADESH_BLOCK_RE = re.compile(
    r"#####\s*Bangladesh[^\n]*\n+([^\n#]+)",
    re.I,
)
ENTRY_BLOCK_RE = re.compile(
    r"(?:^|\n)Entry requirements\s*\n+(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
STANDARD_LINE_RE = re.compile(
    r"^([A-D]{3})\s*—\s*Bangladesh HSC[^\n]*:\s*(\d+(?:\.\d+)?)\s*$",
    re.I,
)
BAND_LINE_RE = re.compile(
    r"^([A-D]{3})\s*[-–]\s*([A-D]{3})\s*—\s*GPA\s*(\d+(?:\.\d+)?)\s*$",
    re.I,
)
SINGLE_BAND_LINE_RE = re.compile(
    r"^([A-D]{3})\s*—\s*GPA\s*(\d+(?:\.\d+)?)\s*$",
    re.I,
)
GRADE_ORDER = {grade: index for index, grade in enumerate(("A", "B", "C", "D", "E"))}


@dataclass(frozen=True)
class BangladeshUgTables:
    standard: dict[str, str]
    bands: dict[str, str]


@dataclass(frozen=True)
class DerivedUgEntry:
    slug: str
    course_url: str
    course_name: str
    alevel_label: str
    degree: str
    grade: str
    metadata_line: str
    md_path: Path
    audit_dir: Path | None = None


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


def bangladesh_entry_path(output_dir: Path) -> Path:
    return output_dir / "clean" / "uni" / "bangladesh-entry.md"


def load_bangladesh_ug_tables(path: Path) -> BangladeshUgTables:
    text = path.read_text(encoding="utf-8")
    _, body = split_frontmatter(text)
    standard: dict[str, str] = {}
    bands: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        band_match = BAND_LINE_RE.match(stripped)
        if band_match:
            key = f"{band_match.group(1).upper()}-{band_match.group(2).upper()}"
            bands[key] = band_match.group(3)
            continue
        single_band = SINGLE_BAND_LINE_RE.match(stripped)
        if single_band:
            bands[single_band.group(1).upper()] = single_band.group(2)
            continue
        standard_match = STANDARD_LINE_RE.match(stripped)
        if standard_match:
            standard[standard_match.group(1).upper()] = standard_match.group(2)
    if not standard:
        standard = {combo: str(gpa) for combo, gpa in ALEVEL_TO_HSC_EQUIVALENT.items()}
    return BangladeshUgTables(standard=standard, bands=bands)


def _canonical_combo(text: str) -> str:
    combo = (text or "").strip().upper()
    if len(combo) != 3 or not all(ch in "ABCDE" for ch in combo):
        return ""
    return "".join(sorted(combo, key=lambda ch: GRADE_ORDER.get(ch, 99)))


def _lower_combo(low: str, high: str) -> str:
    low_combo = _canonical_combo(low)
    high_combo = _canonical_combo(high)
    if not low_combo or not high_combo:
        return low_combo or high_combo
    low_score = sum(GRADE_ORDER.get(ch, 99) for ch in low_combo)
    high_score = sum(GRADE_ORDER.get(ch, 99) for ch in high_combo)
    return low_combo if low_score >= high_score else high_combo


def _format_gpa(value: str) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return f"GPA {int(numeric)}"
    return f"GPA {numeric:.2f}".rstrip("0").rstrip(".")


def extract_alevel_label(entry_block: str) -> str:
    range_match = ALEVEL_RANGE_RE.search(entry_block)
    if range_match:
        return f"{range_match.group(1).upper()}-{range_match.group(2).upper()}"
    single_match = ALEVEL_SINGLE_RE.search(entry_block)
    if single_match:
        return single_match.group(1).upper()
    return ""


def extract_explicit_bangladesh_gpa(markdown: str) -> str | None:
    block_match = BANGLADESH_BLOCK_RE.search(markdown)
    if not block_match:
        return None
    line = block_match.group(1).strip()
    if re.search(r"institution\s+dependent|please\s+check\s+with\s+admissions", line, re.I):
        return None
    gpa_match = GPA_EXPLICIT_RE.search(line)
    if gpa_match:
        return gpa_match.group(1)
    return None


def map_alevel_to_gpa(label: str, tables: BangladeshUgTables) -> tuple[str, str] | None:
    if not label:
        return None

    if label in tables.bands:
        gpa = tables.bands[label]
        return gpa, f"A-level {label.replace('-', ' - ')} - HSC CGPA {gpa} (Brunel course-page band)"

    if "-" in label:
        low, high = label.split("-", 1)
        band_key = f"{low.upper()}-{high.upper()}"
        if band_key in tables.bands:
            gpa = tables.bands[band_key]
            return gpa, f"A-level {low.upper()} - {high.upper()} - HSC CGPA {gpa} (Brunel course-page band)"
        combo = _lower_combo(low, high)
        gpa = tables.standard.get(combo) or str(ALEVEL_TO_HSC_EQUIVALENT.get(combo, ""))
        if gpa:
            return gpa, (
                f"A-level {low.upper()} - {high.upper()} - "
                f"HSC CGPA {gpa} (minimum {combo} equivalent)"
            )
        return None

    combo = _canonical_combo(label)
    gpa = tables.standard.get(combo) or str(ALEVEL_TO_HSC_EQUIVALENT.get(combo, ""))
    if not gpa:
        return None
    return gpa, f"A-level {combo} - HSC CGPA {gpa}"


def bangladesh_hsc_header(markdown: str) -> str:
    match = re.search(r"#####\s*(Bangladesh[^\n]+)", markdown, re.I)
    if match:
        return match.group(1).strip()
    return "Bangladesh - Higher School Certificate (from a Board of Intermediate and Secondary Education)"


def entry_metadata(metadata_line: str, header: str) -> list[dict[str, object]]:
    return [
        {
            "subtitle": "Entry Requirements",
            "description": [header, metadata_line],
        }
    ]


def apply_to_course_json(audit_dir: Path, derived: DerivedUgEntry) -> bool:
    requirement = {"degree": derived.degree, "grade": derived.grade}
    metadata = entry_metadata(derived.metadata_line, bangladesh_hsc_header(derived.md_path.read_text(encoding="utf-8")))
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
        if name in {"entry_requirement_parsed.json", "stage2_llm_parsed.json"}:
            data["AcademicRequirementsMetaData"] = metadata
        if name in {"stage2_parsed.json", "output.json"}:
            english = [
                item
                for item in (data.get("AcademicRequirementsMetaData") or [])
                if isinstance(item, dict)
                and str(item.get("subtitle", "")).strip().lower() == "english requirement"
            ]
            data["AcademicRequirementsMetaData"] = metadata + english
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed = True
    return changed


def find_audit_dir(output_dir: Path, course_url: str, slug: str) -> Path | None:
    candidate = output_dir / "extracted" / "undergraduate" / slug
    if candidate.is_dir():
        return candidate
    for path in (output_dir / "extracted").rglob(slug):
        if path.is_dir() and (path / "output.json").is_file():
            return path
    return None


def derive_from_markdown(
    md_path: Path,
    *,
    tables: BangladeshUgTables,
    output_dir: Path,
) -> DerivedUgEntry | None:
    markdown = md_path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(markdown)
    if meta.get("study_level", "").strip().lower() != "undergraduate":
        return None
    course_url = meta.get("course_url", "").strip()
    if is_pathway_course_url(course_url):
        return None

    entry_match = ENTRY_BLOCK_RE.search(body)
    entry_block = entry_match.group(1) if entry_match else ""
    alevel_label = extract_alevel_label(entry_block)
    explicit_gpa = extract_explicit_bangladesh_gpa(markdown)

    if explicit_gpa:
        gpa = explicit_gpa
        label = alevel_label or "A-level"
        metadata_line = f"GPA {gpa}/5 in a related subject"
    else:
        if not alevel_label:
            return None
        mapped = map_alevel_to_gpa(alevel_label, tables)
        if not mapped:
            return None
        gpa, metadata_line = mapped

    slug = course_url.rstrip("/").split("/")[-1] if course_url else md_path.stem
    audit_dir = find_audit_dir(output_dir, course_url, slug)
    return DerivedUgEntry(
        slug=slug,
        course_url=course_url,
        course_name=meta.get("course_name", "") or md_path.stem,
        alevel_label=alevel_label,
        degree="HSC",
        grade=_format_gpa(gpa),
        metadata_line=metadata_line,
        md_path=md_path,
        audit_dir=audit_dir,
    )


def scan_courses(courses_dir: Path, *, tables: BangladeshUgTables, output_dir: Path) -> list[DerivedUgEntry]:
    derived_rows: list[DerivedUgEntry] = []
    ug_dir = courses_dir / "undergraduate"
    if not ug_dir.is_dir():
        return derived_rows
    for md_path in sorted(ug_dir.glob("*.md")):
        derived = derive_from_markdown(md_path, tables=tables, output_dir=output_dir)
        if derived:
            derived_rows.append(derived)
    return derived_rows


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
    bangladesh_md = bangladesh_entry_path(output_dir)
    if not bangladesh_md.is_file():
        print(f"Missing {bangladesh_md}", file=sys.stderr)
        return 0
    if not courses_dir.is_dir():
        print(f"Missing courses markdown dir: {courses_dir}", file=sys.stderr)
        return 0

    tables = load_bangladesh_ug_tables(bangladesh_md)
    derived_rows = scan_courses(courses_dir, tables=tables, output_dir=output_dir)
    if limit is not None:
        derived_rows = derived_rows[:limit]
    if not derived_rows:
        return 0

    print(f"Found {len(derived_rows)} undergraduate course(s) to derive (A-level -> HSC).")
    patched = 0
    normalizer = AdmissionRecordNormalizer()
    for derived in derived_rows:
        print(
            f"- {derived.slug}: {derived.alevel_label or 'explicit'} -> "
            f"{derived.degree} / {derived.grade}"
        )
        if dry_run:
            continue
        if not derived.audit_dir:
            print(f"  ! no extracted audit dir for {derived.course_url or derived.slug}")
            continue
        if apply_to_course_json(derived.audit_dir, derived):
            patched += 1
            if re_normalize:
                output_json = derived.audit_dir / "output.json"
                raw = json.loads(output_json.read_text(encoding="utf-8"))
                normalized = normalizer.process_record(raw)
                (derived.audit_dir / "normalized.json").write_text(
                    json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
    if dry_run:
        print("Dry run only. Pass --apply to patch extracted JSON.")
        return len(derived_rows)
    if re_normalize:
        print(f"Patched {patched} undergraduate course(s); rewrote normalized.json.")
    else:
        print(f"Patched {patched} undergraduate course(s).")
    return patched


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive Brunel undergraduate HSC requirements from A-level + bangladesh-entry.md.",
    )
    parser.add_argument("code_dir", nargs="?", default=".", help="Brunel code/ directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--re-normalize", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = args.dry_run or not args.apply
    apply_enrichments(
        Path(args.code_dir),
        re_normalize=args.re_normalize,
        dry_run=dry_run,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
