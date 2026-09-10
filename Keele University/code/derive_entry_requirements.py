#!/usr/bin/env python3
"""Derive Keele canonical entry requirements from parsed JSON and course markdown.

Usage:
  python derive_entry_requirements.py --dry-run
  python derive_entry_requirements.py --apply
  python derive_entry_requirements.py --apply --re-normalize
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_SHARED = _CODE_DIR.parents[1] / "shared"
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from llm_extract import normalize_requirements_list  # noqa: E402
from normalize_admission_data import AdmissionRecordNormalizer  # noqa: E402
from uni_paths import resolve_code_dir, resolve_output_dir  # noqa: E402

from degree_name_inference import find_course_markdown  # noqa: E402
from keele_bangladesh_rules import (  # noqa: E402
    detect_uk_class,
    level_default_requirement,
    pg_fallback_from_markdown,
    pg_requirement_for_uk_class,
)
from parse_keele_requirements import (  # noqa: E402
    parse_keele_requirements,
    requirements_to_metadata_line,
)

ENTRY_BLOCK_RE = re.compile(
    r"(?:^|\n)##\s+Entry requirements\s*\n+(.*?)(?=\n## |\Z)",
    re.S | re.I,
)
DERIVE_LEVELS = frozenset(
    {"foundation", "undergraduate", "postgraduate", "postgraduate_research"}
)


@dataclass(frozen=True)
class DerivedEntry:
    slug: str
    study_level: str
    course_url: str
    course_name: str
    requirements: list[dict[str, str]]
    metadata_line: str
    audit_dir: Path
    source: str


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


def extract_entry_text(markdown: str) -> str:
    _, body = split_frontmatter(markdown)
    match = ENTRY_BLOCK_RE.search(body)
    return match.group(1).strip() if match else body[:4000]


def derive_from_markdown(md_path: Path, *, study_level: str) -> list[dict[str, str]]:
    markdown = md_path.read_text(encoding="utf-8")
    entry_text = extract_entry_text(markdown)
    level = study_level.strip().lower()

    if level in {"postgraduate", "postgraduate_research"}:
        fallback = pg_fallback_from_markdown(entry_text)
        if fallback:
            return [{"degree": fallback[0], "grade": fallback[1]}]
        uk_class = detect_uk_class(entry_text)
        if uk_class:
            mapped = pg_requirement_for_uk_class(uk_class)
            if mapped:
                return [{"degree": mapped[0], "grade": mapped[1]}]

    default = level_default_requirement(level, entry_text)
    if default:
        return [{"degree": default[0], "grade": default[1]}]
    return []


def pick_requirements(
    raw_requirements: object,
    *,
    study_level: str,
    md_path: Path | None,
) -> tuple[list[dict[str, str]], str]:
    parsed = parse_keele_requirements(raw_requirements, study_level=study_level)
    normalized = normalize_requirements_list(parsed, course_level=study_level)
    if normalized:
        return normalized, "parsed"

    if md_path and md_path.is_file():
        from_md = derive_from_markdown(md_path, study_level=study_level)
        normalized_md = normalize_requirements_list(from_md, course_level=study_level)
        if normalized_md:
            return normalized_md, "markdown"

    default = level_default_requirement(study_level)
    if default and study_level in {"foundation", "undergraduate"}:
        return [{"degree": default[0], "grade": default[1]}], "default"

    if study_level in {"postgraduate", "postgraduate_research"} and md_path and md_path.is_file():
        fallback = pg_fallback_from_markdown(md_path.read_text(encoding="utf-8"))
        if fallback:
            return [{"degree": fallback[0], "grade": fallback[1]}], "markdown_pg"

    return [], "none"


def _entry_metadata(requirements: list[dict[str, str]], existing: object) -> list[dict[str, object]]:
    lines = [requirements_to_metadata_line(requirements)] if requirements else []
    if isinstance(existing, list):
        for block in existing:
            if not isinstance(block, dict):
                continue
            subtitle = str(block.get("subtitle", "")).strip().lower()
            if subtitle == "entry requirements":
                description = block.get("description", [])
                if isinstance(description, list):
                    for item in description:
                        text = str(item).strip()
                        if text and text not in lines:
                            lines.append(text)
    return [{"subtitle": "Entry Requirements", "description": [line for line in lines if line]}]


def apply_to_course_json(audit_dir: Path, derived: DerivedEntry) -> bool:
    if not derived.requirements:
        return False

    requirement = derived.requirements[0]
    if len(derived.requirements) > 1:
        requirements = derived.requirements
    else:
        requirements = [requirement]

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
        existing_meta = data.get("AcademicRequirementsMetaData")
        metadata = _entry_metadata(requirements, existing_meta)
        data["requirements"] = requirements
        changed = True
        if name in {"entry_requirement_parsed.json", "stage2_llm_parsed.json"}:
            data["AcademicRequirementsMetaData"] = metadata
        if name in {"stage2_parsed.json", "output.json"}:
            english = [
                item
                for item in (existing_meta or [])
                if isinstance(item, dict)
                and str(item.get("subtitle", "")).strip().lower() == "english requirement"
            ]
            data["AcademicRequirementsMetaData"] = metadata + english
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def scan_extracted_courses(output_dir: Path) -> list[DerivedEntry]:
    extracted = output_dir / "extracted"
    if not extracted.is_dir():
        return []

    derived_rows: list[DerivedEntry] = []
    for entry_path in sorted(extracted.rglob("entry_requirement_parsed.json")):
        audit_dir = entry_path.parent
        study_level = audit_dir.parent.name
        if study_level not in DERIVE_LEVELS:
            continue
        slug = audit_dir.name
        payload = json.loads(entry_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue

        output_json = audit_dir / "output.json"
        course_url = ""
        course_name = slug
        if output_json.is_file():
            output_data = json.loads(output_json.read_text(encoding="utf-8"))
            if isinstance(output_data, dict):
                course_url = str(output_data.get("courseUrl") or output_data.get("courseUrlExternal") or "")
                course_name = str(output_data.get("courseName") or course_name)

        md_path = find_course_markdown(output_dir, slug)
        requirements, source = pick_requirements(
            payload.get("requirements", []),
            study_level=study_level,
            md_path=md_path,
        )
        if not requirements:
            continue

        derived_rows.append(
            DerivedEntry(
                slug=slug,
                study_level=study_level,
                course_url=course_url,
                course_name=course_name,
                requirements=requirements,
                metadata_line=requirements_to_metadata_line(requirements),
                audit_dir=audit_dir,
                source=source,
            )
        )
    return derived_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Derive Keele canonical entry requirements for extracted courses.",
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        default=".",
        help="Keele code/ directory (default: cwd)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print derived rows only")
    parser.add_argument("--apply", action="store_true", help="Patch extracted JSON files")
    parser.add_argument("--re-normalize", action="store_true", help="Rewrite normalized.json after apply")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N courses")
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
    derived_rows = scan_extracted_courses(output_dir)
    if limit is not None:
        derived_rows = derived_rows[:limit]
    if not derived_rows:
        return 0

    print(f"Found {len(derived_rows)} course(s) with derivable Keele entry requirements.")
    patched = 0
    normalizer = AdmissionRecordNormalizer()
    for derived in derived_rows:
        req = derived.requirements[0]
        print(
            f"- [{derived.study_level}] {derived.course_name}: "
            f"{req['degree']} / {req['grade']} ({derived.source})"
        )
        if dry_run:
            continue
        if apply_to_course_json(derived.audit_dir, derived):
            patched += 1
            if re_normalize:
                output_json = derived.audit_dir / "output.json"
                if output_json.is_file():
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
        print("No matching Keele derive-candidate courses found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
