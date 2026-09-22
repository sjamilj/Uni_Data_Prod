#!/usr/bin/env python3
"""Derive Suffolk postgraduate BSc requirements from UK honours class on course markdown.

Mapping (suffolk_uk_class_mapping.py):
  2:1 → GPA 3.0
  2:2 → GPA 2.75

Usage:
  python derive_pg_entry_from_uk_class.py --dry-run
  python derive_pg_entry_from_uk_class.py --apply
  python derive_pg_entry_from_uk_class.py --apply --re-normalize
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_SHARED = _CODE_DIR.parents[1] / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from normalize_admission_data import AdmissionRecordNormalizer  # noqa: E402
from uni_paths import resolve_code_dir, resolve_output_dir  # noqa: E402

from suffolk_uk_class_mapping import (  # noqa: E402
    extract_uk_entry_class_from_text,
    suffolk_bangladesh_requirement,
)

DERIVE_STUDY_LEVELS = frozenset({"postgraduate", "postgraduate_research"})


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


def derive_from_markdown(md_path: Path) -> DerivedEntry | None:
    markdown = md_path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(markdown)
    study_level = meta.get("study_level", "").strip().lower()
    if study_level not in DERIVE_STUDY_LEVELS:
        return None
    uk_class = extract_uk_entry_class_from_text(body)
    if not uk_class:
        return None
    mapped = suffolk_bangladesh_requirement(uk_class)
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


def apply_to_course_json(audit_dir: Path, derived: DerivedEntry) -> bool:
    requirement = {"degree": derived.degree, "grade": derived.grade}
    metadata = [
        {
            "subtitle": "Entry Requirements",
            "description": [derived.metadata_line],
        }
    ]
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


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def find_audit_dir(output_dir: Path, derived: DerivedEntry) -> Path | None:
    slug = _slug_from_url(derived.course_url) or derived.md_path.stem
    level = derived.study_level or "postgraduate"
    candidate = output_dir / "extracted" / level / slug
    if candidate.is_dir():
        return candidate
    for path in (output_dir / "extracted").rglob(slug):
        if path.is_dir() and (path / "output.json").is_file():
            return path
    return None


def scan_courses(courses_dir: Path) -> list[DerivedEntry]:
    rows: list[DerivedEntry] = []
    for md_path in sorted(courses_dir.rglob("*.md")):
        if md_path.parent.name not in DERIVE_STUDY_LEVELS:
            continue
        derived = derive_from_markdown(md_path)
        if derived:
            rows.append(derived)
    return rows


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

    derived_rows = scan_courses(courses_dir)
    if limit is not None:
        derived_rows = derived_rows[:limit]
    if not derived_rows:
        return 0

    patched = 0
    normalizer = AdmissionRecordNormalizer()
    print(f"Found {len(derived_rows)} postgraduate course(s) with UK class → BSc GPA.")
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
                    record = json.loads(output_json.read_text(encoding="utf-8"))
                    normalized = normalizer.process_record(record)
                    (audit_dir / "normalized.json").write_text(
                        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
    return patched


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Derive Suffolk PG Bangladesh BSc GPA from UK 2:1 / 2:2 on course markdown.",
    )
    parser.add_argument("code_dir", nargs="?", default=".", help="Suffolk code/ directory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--re-normalize", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
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
