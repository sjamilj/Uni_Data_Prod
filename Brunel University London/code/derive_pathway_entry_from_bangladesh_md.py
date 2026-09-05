#!/usr/bin/env python3
"""Derive Brunel Pathway College entry requirements from bangladesh-entry.md.

Maps the 7 ``undergraduate-pathway-in-*-brunel-pathway-college`` courses to
Foundation pathway rows in ``output/clean/uni/bangladesh-entry.md``:

- Business / Computer Science / Economics / Humanities / Law → HSC GPA 3.0
- Engineering / Health and Life Sciences → HSC GPA 3.5

Usage:
  python derive_pathway_entry_from_bangladesh_md.py --dry-run
  python derive_pathway_entry_from_bangladesh_md.py --apply
  python derive_pathway_entry_from_bangladesh_md.py --apply --re-normalize
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

PATHWAY_URL_RE = re.compile(
    r"/undergraduate-pathway-in-.+-brunel-pathway-college/?$",
    re.I,
)

PATHWAY_SLUG_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(r"business-and-management", re.I),
        "3.0",
        "Business - Completion of HSC: GPA 3.0",
    ),
    (
        re.compile(r"computer-science", re.I),
        "3.0",
        "Computer Science pathway - Completion of HSC: GPA 3.0",
    ),
    (
        re.compile(r"economics-and-finance", re.I),
        "3.0",
        "Economics - Completion of HSC: GPA 3.0, incl. Maths grade C/GPA 2.0",
    ),
    (
        re.compile(r"humanities-social-sciences-education-psychology", re.I),
        "3.0",
        "Humanities/Social Sciences/Education - Completion of HSC: GPA 3.0",
    ),
    (
        re.compile(r"pathway-in-law", re.I),
        "3.0",
        "Law/Social Science - Completion of HSC: GPA 3.0",
    ),
    (
        re.compile(r"life-sciences", re.I),
        "3.5",
        "Engineering/Health and Life Sciences - Completion of HSC: GPA 3.5, incl. Maths grade C/GPA 3.0",
    ),
    (
        re.compile(r"pathway-in-engineering", re.I),
        "3.5",
        "Engineering/Health and Life Sciences - Completion of HSC: GPA 3.5, incl. Maths grade C/GPA 3.0",
    ),
)

FOUNDATION_HEADER = (
    "Foundation pathway (5 GCSE Passes A-E including Maths where stated in "
    "bangladesh-entry.md)"
)


@dataclass(frozen=True)
class DerivedPathwayEntry:
    slug: str
    course_url: str
    course_name: str
    degree: str
    grade: str
    metadata_line: str
    audit_dir: Path


def bangladesh_entry_path(output_dir: Path) -> Path:
    return output_dir / "clean" / "uni" / "bangladesh-entry.md"


def is_pathway_course_url(url: str) -> bool:
    return bool(PATHWAY_URL_RE.search((url or "").strip()))


def pathway_rule_for_slug(slug: str) -> tuple[str, str] | None:
    for pattern, gpa, metadata_line in PATHWAY_SLUG_RULES:
        if pattern.search(slug):
            return gpa, metadata_line
    return None


def entry_metadata(metadata_line: str) -> list[dict[str, object]]:
    return [
        {
            "subtitle": "Entry Requirements",
            "description": [FOUNDATION_HEADER, metadata_line],
        }
    ]


def apply_to_course_json(audit_dir: Path, derived: DerivedPathwayEntry) -> bool:
    requirement = {"degree": derived.degree, "grade": derived.grade}
    metadata = entry_metadata(derived.metadata_line)
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


def discover_pathway_audit_dirs(output_dir: Path) -> list[Path]:
    extracted = output_dir / "extracted"
    if not extracted.is_dir():
        return []
    audit_dirs: list[Path] = []
    for output_json in extracted.rglob("output.json"):
        try:
            data = json.loads(output_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        url = str(data.get("courseUrl") or data.get("courseUrlExternal") or "").strip()
        if is_pathway_course_url(url):
            audit_dirs.append(output_json.parent)
    return sorted(set(audit_dirs))


def derive_from_audit_dir(audit_dir: Path) -> DerivedPathwayEntry | None:
    output_json = audit_dir / "output.json"
    if not output_json.is_file():
        return None
    data = json.loads(output_json.read_text(encoding="utf-8"))
    url = str(data.get("courseUrl") or data.get("courseUrlExternal") or "").strip()
    if not is_pathway_course_url(url):
        return None
    slug = url.rstrip("/").split("/")[-1]
    rule = pathway_rule_for_slug(slug)
    if not rule:
        return None
    gpa, metadata_line = rule
    return DerivedPathwayEntry(
        slug=slug,
        course_url=url,
        course_name=str(data.get("courseName") or "").strip(),
        degree="HSC",
        grade=f"GPA {gpa}",
        metadata_line=metadata_line,
        audit_dir=audit_dir,
    )


def apply_enrichments(
    code_dir: Path,
    *,
    re_normalize: bool = False,
    dry_run: bool = False,
) -> int:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    bangladesh_md = bangladesh_entry_path(output_dir)
    if not bangladesh_md.is_file():
        print(f"Missing {bangladesh_md}", file=sys.stderr)
        return 0

    derived_rows = [
        row
        for audit_dir in discover_pathway_audit_dirs(output_dir)
        if (row := derive_from_audit_dir(audit_dir)) is not None
    ]
    if not derived_rows:
        return 0

    print(f"Found {len(derived_rows)} Brunel Pathway course(s) to derive.")
    patched = 0
    normalizer = AdmissionRecordNormalizer()
    for derived in derived_rows:
        print(
            f"- {derived.slug}: {derived.degree} / {derived.grade} "
            f"({derived.course_name or derived.course_url})"
        )
        if dry_run:
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
    elif re_normalize:
        print(f"Patched {patched} pathway course(s); rewrote normalized.json.")
    else:
        print(f"Patched {patched} pathway course(s).")
    return patched


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive Brunel Pathway College HSC requirements from bangladesh-entry.md.",
    )
    parser.add_argument("code_dir", nargs="?", default=".", help="Brunel code/ directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--re-normalize", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = args.dry_run or not args.apply
    apply_enrichments(
        Path(args.code_dir),
        re_normalize=args.re_normalize,
        dry_run=dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
