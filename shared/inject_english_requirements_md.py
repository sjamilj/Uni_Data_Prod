#!/usr/bin/env python3
"""Inject mapped english_requirements_parsed.json tests into course markdown."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from course_markdown_cleanup import parse_uni_json_payload
from llm_extract import ENGLISH_TEST_KEYS, ExtractionPathConfig, Stage1Enricher, Stage2Enricher, load_uni_section, select_english_json_program
from study_level import CLEAN_COURSES_SUBDIR, PRESETUP_CLEAN_SUBDIR, PRESETUP_EXTRACT_SUBDIR
from uni_pages import split_frontmatter
from uni_paths import resolve_code_dir, resolve_output_dir

ENGLISH_TESTS_MARKER = "<!-- english-tests-mapped -->"
ENGLISH_SUBSECTION_RE = re.compile(
    r"^(###\s+(?:International and )?English language requirements[^\n]*\n)(.*?)(?=^###\s|^##\s|\Z)",
    re.M | re.I | re.S,
)
MAPPED_BLOCK_RE = re.compile(
    rf"\n?{re.escape(ENGLISH_TESTS_MARKER)}.*?(?=\n###\s|\n##\s|\Z)",
    re.S,
)
IELTS_IN_TEXT_RE = re.compile(r"\bIELTS\b", re.I)
IELTS_DESC_LINE_RE = re.compile(r"\bIELTS\b", re.I)
ENGLISH_JSON_FENCE_RE = re.compile(r"```json\s*\n(.*?)\n```", re.S)


def body_before_mapped_block(body: str) -> str:
    before, _, _ = body.partition(ENGLISH_TESTS_MARKER)
    return before


def build_ielts_description_from_profile(
    profile: dict[str, str],
    *,
    program_label: str = "",
) -> str:
    overall = str(profile.get("overall", "") or "").strip()
    writing = str(profile.get("writing_min", "") or "").strip()
    section = str(
        profile.get("min_section", "") or profile.get("all_components_min", "") or ""
    ).strip()
    if not overall:
        return ""
    prefix = f"{program_label}: " if program_label else ""
    if writing and section and writing != section:
        return (
            f"{prefix}IELTS {overall} overall with {writing} in writing "
            f"and {section} in all other components"
        )
    if section:
        return f"{prefix}IELTS {overall} overall with no element below {section}"
    return f"{prefix}IELTS {overall} overall"


def align_descriptions_to_course_ielts(
    descriptions: list[str],
    profile: dict[str, str],
    *,
    program_label: str = "",
) -> list[str]:
    """Keep group TOEFL/PTE lines but rewrite IELTS to match the course page."""
    course_line = build_ielts_description_from_profile(profile, program_label=program_label)
    if not course_line:
        return descriptions

    aligned: list[str] = []
    ielts_added = False
    for line in descriptions:
        if IELTS_DESC_LINE_RE.search(line):
            if not ielts_added:
                aligned.append(course_line)
                ielts_added = True
            continue
        aligned.append(line)

    if not ielts_added:
        aligned.insert(0, course_line)
    return aligned


def english_requirement_descriptions(english_json: dict) -> list[str]:
    """Return English Requirement description lines from parsed JSON."""
    descriptions: list[str] = []
    metadata = english_json.get("AcademicRequirementsMetaData") or []
    if not isinstance(metadata, list):
        return descriptions
    for block in metadata:
        if not isinstance(block, dict):
            continue
        subtitle = str(block.get("subtitle", "") or "").strip().casefold()
        if subtitle != "english requirement":
            continue
        raw = block.get("description", [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            continue
        for item in raw:
            text = str(item or "").strip()
            if text and text not in descriptions:
                descriptions.append(text)
    return descriptions


def normalize_english_requirements_payload(english_json: dict) -> dict[str, object]:
    """Normalize to english_requirements_parsed.json shape."""
    descriptions = english_requirement_descriptions(english_json)
    if not descriptions:
        overall = str(english_json.get("ieltsMinOverall", "") or "").strip()
        section = str(english_json.get("ieltsMinSection", "") or "").strip()
        if overall:
            descriptions = [
                Stage2Enricher.build_course_ielts_requirement_text(overall, section)
            ]

    metadata = english_json.get("AcademicRequirementsMetaData")
    if not isinstance(metadata, list) or not metadata:
        metadata = (
            [{"subtitle": "English Requirement", "description": descriptions}]
            if descriptions
            else []
        )

    payload: dict[str, object] = {"AcademicRequirementsMetaData": metadata}
    for key in ENGLISH_TEST_KEYS:
        payload[key] = str(english_json.get(key, "") or "").strip()
    return payload


def parse_english_json_from_mapped_block(mapped_text: str) -> dict[str, object] | None:
    match = ENGLISH_JSON_FENCE_RE.search(mapped_text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    payload = normalize_english_requirements_payload(data)
    if not payload.get("AcademicRequirementsMetaData") and not any(
        payload.get(key) for key in ENGLISH_TEST_KEYS
    ):
        return None
    return payload


def format_english_requirements_parsed_markdown(english_json: dict) -> str:
    """Format english_requirements_parsed.json as a fenced JSON block in course markdown."""
    payload = normalize_english_requirements_payload(english_json)
    if not payload.get("AcademicRequirementsMetaData") and not any(
        payload.get(key) for key in ENGLISH_TEST_KEYS
    ):
        return ""
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    return f"{ENGLISH_TESTS_MARKER}\n```json\n{json_text}\n```\n"


def strip_mapped_english_block(section_body: str) -> str:
    return MAPPED_BLOCK_RE.sub("", section_body).rstrip()


def inject_english_requirements_into_markdown(body: str, english_json: dict) -> tuple[str, bool]:
    """Append mapped English tests below the course English subsection."""
    block = format_english_requirements_parsed_markdown(english_json)
    if not block:
        return body, False

    match = ENGLISH_SUBSECTION_RE.search(body)
    if not match:
        return body, False

    heading = match.group(1)
    section_body = strip_mapped_english_block(match.group(2))
    new_section = f"{heading}{section_body}\n\n{block}\n\n"
    new_body = body[: match.start()] + new_section + body[match.end() :]
    return new_body, True


def load_foundation_year_english_program(output_dir: Path) -> dict[str, object]:
    """Return Foundation Year entry program from clean/uni/english-requirements.md."""
    content = load_uni_section(output_dir, "english-requirements.md")
    programs = parse_uni_json_payload(content, "english-requirements") or []
    if not isinstance(programs, list):
        return {}
    for program in programs:
        if not isinstance(program, dict):
            continue
        level = str(program.get("TestStudyLevel", "") or "").strip().casefold()
        name = str(program.get("ProgramName", "") or "").strip().casefold()
        if level == "foundation" and "foundation year" in name:
            return program
    return {}


def merge_foundation_pte_toefl_preserving_ielts(
    existing: dict[str, object],
    program: dict[str, object],
) -> dict[str, object]:
    """Add Essex Foundation Year PTE/TOEFL; keep Kaplan IELTS scalars and IELTS description lines."""
    merged: dict[str, object] = dict(existing)
    ielts_overall = str(existing.get("ieltsMinOverall", "") or "").strip()
    ielts_section = str(existing.get("ieltsMinSection", "") or "").strip()

    for test in program.get("TestRequirements", []) or []:
        if not isinstance(test, dict):
            continue
        name = str(test.get("TestName", "") or "").casefold()
        if "pte" in name or "pearson" in name:
            merged["pteMinOverall"] = str(test.get("pteMinOverall", "") or "").strip()
            merged["pteMinSection"] = str(test.get("pteMinSection", "") or "").strip()
        elif "toefl" in name:
            merged["toeflMinOverall"] = str(test.get("toeflMinOverall", "") or "").strip()
            merged["toeflMinSection"] = str(test.get("toeflMinSection", "") or "").strip()

    existing_desc = english_requirement_descriptions(existing)
    kept: list[str] = []
    for line in existing_desc:
        lower = line.casefold()
        if (
            "ielts" in lower
            or "kaplan" in lower
            or "pathway:" in lower
            or "summary sheet" in lower
            or "international college" in lower
        ):
            kept.append(line)

    for line in Stage1Enricher.normalize_description_list(program.get("description")):
        lower = str(line).casefold()
        if "ielts" in lower:
            continue
        if line not in kept:
            kept.append(str(line))

    merged["AcademicRequirementsMetaData"] = [
        {"subtitle": "English Requirement", "description": kept}
    ]
    merged["ieltsMinOverall"] = ielts_overall
    merged["ieltsMinSection"] = ielts_section
    return normalize_english_requirements_payload(merged)


def course_h1(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, re.M)
    return match.group(1).strip() if match else ""


def build_english_json_from_uni_mapping(
    body: str,
    *,
    course_level: str,
    course_name: str,
    english_content: str,
    english_course_groups: list[dict] | None = None,
) -> dict[str, object]:
    """Build english_requirements_parsed.json shape from uni english-requirements.md mapping."""
    programs = parse_uni_json_payload(english_content, "english-requirements") or []
    program = select_english_json_program(
        programs if isinstance(programs, list) else [],
        course_level=course_level,
        course_name=course_name,
        course_body=body,
        english_course_groups=english_course_groups,
    )
    descriptions: list[str] = []
    program_label = ""
    if isinstance(program, dict):
        descriptions = Stage1Enricher.normalize_description_list(program.get("description"))
        program_label = str(program.get("ProgramName", "") or "").strip()
    if not descriptions:
        descriptions = Stage2Enricher.extract_english_json_descriptions(
            english_content,
            course_level,
            course_name=course_name,
            course_body=body,
        )

    source_body = body_before_mapped_block(body)
    profile = Stage2Enricher.extract_course_ielts_profile(source_body)
    overall = str(profile.get("overall", "") or "").strip()
    section = str(
        profile.get("min_section", "") or profile.get("all_components_min", "") or ""
    ).strip()
    if isinstance(program, dict):
        prog_overall, prog_section = Stage2Enricher.get_ielts_from_english_program(program)
        if not overall:
            overall = prog_overall
        if not section:
            section = prog_section

    if overall:
        descriptions = align_descriptions_to_course_ielts(
            descriptions,
            profile if profile.get("overall") else {"overall": overall, "min_section": section},
            program_label=program_label,
        )

    payload: dict[str, object] = {
        "AcademicRequirementsMetaData": [
            {"subtitle": "English Requirement", "description": descriptions}
        ],
        "ieltsMinOverall": overall,
        "ieltsMinSection": section,
    }
    for key in ENGLISH_TEST_KEYS:
        payload[key] = str(payload.get(key, "") or "").strip()
    if isinstance(program, dict):
        for test in program.get("TestRequirements", []):
            if not isinstance(test, dict):
                continue
            name = str(test.get("TestName", "") or "").casefold()
            if "ielts" in name:
                if not payload["ieltsMinOverall"]:
                    payload["ieltsMinOverall"] = str(test.get("ieltsMinOverall", "") or "").strip()
                if not payload["ieltsMinSection"]:
                    payload["ieltsMinSection"] = str(test.get("ieltsMinSection", "") or "").strip()
            elif "toefl" in name:
                payload["toeflMinOverall"] = str(test.get("toeflMinOverall", "") or "").strip()
                payload["toeflMinSection"] = str(test.get("toeflMinSection", "") or "").strip()
            elif "pearson" in name or "pte" in name:
                payload["pteMinOverall"] = str(test.get("pteMinOverall", "") or "").strip()
                payload["pteMinSection"] = str(test.get("pteMinSection", "") or "").strip()
    if program:
        payload["mappedProgram"] = str(program.get("ProgramName", "") or "").strip()
    return payload


def write_markdown_body(md_path: Path, raw: str, new_body: str) -> None:
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        prefix = raw[: end + 4] + "\n\n" if end != -1 else ""
        md_path.write_text(prefix + new_body, encoding="utf-8")
    else:
        md_path.write_text(new_body, encoding="utf-8")


def iter_course_markdown_files(output_dir: Path, *, presetup: bool = False) -> list[Path]:
    subdir = PRESETUP_CLEAN_SUBDIR if presetup else CLEAN_COURSES_SUBDIR
    root = output_dir / "clean" / subdir
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.md"))


def inject_course_markdown_from_uni(
    output_dir: Path,
    md_path: Path,
    *,
    english_content: str,
    english_course_groups: list[dict] | None = None,
    dry_run: bool = True,
) -> dict[str, object]:
    raw = md_path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)
    course_level = (frontmatter.get("study_level") or md_path.parent.name).strip().lower()
    course_name = course_h1(body)
    payload = build_english_json_from_uni_mapping(
        body,
        course_level=course_level,
        course_name=course_name,
        english_content=english_content,
        english_course_groups=english_course_groups,
    )
    descriptions = english_requirement_descriptions(payload)
    if not descriptions:
        return {
            "status": "empty_mapping",
            "markdown": str(md_path.relative_to(output_dir)),
            "course_level": course_level,
            "mappedProgram": payload.get("mappedProgram", ""),
        }

    new_body, changed = inject_english_requirements_into_markdown(body, payload)
    if not changed:
        return {
            "status": "no_english_section",
            "markdown": str(md_path.relative_to(output_dir)),
            "descriptions": len(descriptions),
            "mappedProgram": payload.get("mappedProgram", ""),
        }

    if not dry_run:
        write_markdown_body(md_path, raw, new_body)

    return {
        "status": "injected" if not dry_run else "would_inject",
        "markdown": str(md_path.relative_to(output_dir)),
        "tests": len(descriptions),
        "mappedProgram": payload.get("mappedProgram", ""),
        "ieltsMinOverall": payload.get("ieltsMinOverall", ""),
        "ieltsMinSection": payload.get("ieltsMinSection", ""),
    }


def resolve_course_markdown(
    output_dir: Path,
    *,
    study_level: str,
    slug: str,
    extract_root: str,
) -> Path | None:
    subdir = PRESETUP_CLEAN_SUBDIR if extract_root == PRESETUP_EXTRACT_SUBDIR else CLEAN_COURSES_SUBDIR
    candidates = [study_level]
    if study_level == "postgraduate":
        candidates.append("postgraduate_research")
    elif study_level == "postgraduate_research":
        candidates.append("postgraduate")
    for level in candidates:
        path = output_dir / "clean" / subdir / level / f"{slug}.md"
        if path.is_file():
            return path
    return None


def iter_english_parsed_dirs(output_dir: Path, *, presetup: bool | None = None) -> list[Path]:
    extracted = output_dir / "extracted"
    if not extracted.is_dir():
        return []

    roots: list[str] = []
    if presetup in (None, True) and (extracted / PRESETUP_EXTRACT_SUBDIR).is_dir():
        roots.append(PRESETUP_EXTRACT_SUBDIR)
    if presetup in (None, False):
        for child in sorted(extracted.iterdir()):
            if child.is_dir() and child.name != PRESETUP_EXTRACT_SUBDIR:
                roots.append(child.name)
        if presetup is None and not roots:
            roots.append("")

    seen: set[Path] = set()
    dirs: list[Path] = []
    for root in roots:
        base = extracted / root if root else extracted
        if not base.is_dir():
            continue
        for json_path in sorted(base.rglob("english_requirements_parsed.json")):
            parent = json_path.parent
            if parent in seen:
                continue
            seen.add(parent)
            dirs.append(parent)
    return dirs


def inject_course_dir(
    output_dir: Path,
    course_dir: Path,
    *,
    dry_run: bool = True,
) -> dict[str, object]:
    json_path = course_dir / "english_requirements_parsed.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"status": "invalid_json", "course_dir": str(course_dir)}

    parts = course_dir.relative_to(output_dir / "extracted").parts
    if len(parts) < 2:
        return {"status": "bad_path", "course_dir": str(course_dir)}
    extract_root, study_level, slug = parts[0], parts[1], parts[2]

    md_path = resolve_course_markdown(
        output_dir,
        study_level=study_level,
        slug=slug,
        extract_root=extract_root,
    )
    if not md_path:
        return {
            "status": "no_markdown",
            "course_dir": str(course_dir.relative_to(output_dir)),
            "slug": slug,
        }

    raw = md_path.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(raw)
    new_body, changed = inject_english_requirements_into_markdown(body, payload)
    if not changed:
        descriptions = english_requirement_descriptions(payload)
        status = "no_english_section" if descriptions else "empty_json"
        return {
            "status": status,
            "markdown": str(md_path.relative_to(output_dir)),
            "descriptions": len(descriptions),
        }

    if not dry_run:
        write_markdown_body(md_path, raw, new_body)

    return {
        "status": "injected" if not dry_run else "would_inject",
        "markdown": str(md_path.relative_to(output_dir)),
        "tests": len(english_requirement_descriptions(payload)),
        "has_ielts_in_section": bool(IELTS_IN_TEXT_RE.search(body)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("code_dir", nargs="?", default=".", help="University code/ directory")
    parser.add_argument("--apply", action="store_true", help="Write updated markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only (default)")
    parser.add_argument("--presetup", action="store_true", help="Only pre_setup_course_extracted")
    parser.add_argument(
        "--from-uni",
        action="store_true",
        help="Map from clean/uni/english-requirements.md (no extracted JSON needed)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Process only first N courses")
    parser.add_argument("--json-out", type=Path, help="Write JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = args.dry_run or not args.apply
    code_dir = resolve_code_dir(Path(args.code_dir))
    output_dir = resolve_output_dir(code_dir)

    report: list[dict[str, object]] = []
    counts: dict[str, int] = {}

    if args.from_uni:
        english_content = load_uni_section(output_dir, "english-requirements.md")
        english_course_groups = ExtractionPathConfig.load_english_course_groups(output_dir)
        md_files = iter_course_markdown_files(output_dir, presetup=args.presetup)
        if args.limit is not None:
            md_files = md_files[: args.limit]
        for md_path in md_files:
            frontmatter, _ = split_frontmatter(md_path.read_text(encoding="utf-8"))
            study_level = (frontmatter.get("study_level") or md_path.parent.name).strip().lower()
            if study_level == "foundation":
                report.append(
                    {
                        "status": "skipped_foundation",
                        "markdown": str(md_path.relative_to(output_dir)),
                    }
                )
                counts["skipped_foundation"] = counts.get("skipped_foundation", 0) + 1
                continue
            row = inject_course_markdown_from_uni(
                output_dir,
                md_path,
                english_content=english_content,
                english_course_groups=english_course_groups,
                dry_run=dry_run,
            )
            report.append(row)
            status = str(row.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
        scanned = len(md_files)
    else:
        course_dirs = iter_english_parsed_dirs(output_dir, presetup=True if args.presetup else None)
        if args.limit is not None:
            course_dirs = course_dirs[: args.limit]
        for course_dir in course_dirs:
            row = inject_course_dir(output_dir, course_dir, dry_run=dry_run)
            report.append(row)
            status = str(row.get("status", "unknown"))
            counts[status] = counts.get(status, 0) + 1
        scanned = len(course_dirs)

    print(f"=== Inject English requirements into markdown ===")
    print(f"Courses scanned: {scanned}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    if dry_run:
        print("Dry run only. Pass --apply to write markdown files.")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Report: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
