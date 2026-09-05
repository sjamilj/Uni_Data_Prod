#!/usr/bin/env python3
"""Re-run Stage 2a (Bangladesh entry requirements) for extracted courses.

Uses existing stage1_parsed.json and keeps english / scholarship / deposit audits.
Updates extracted/{study_level}/{slug}/output.json, stage2_parsed.json, stage2_llm_parsed.json,
extracted_courses.csv, and optionally normalized.json + dev_courses CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from llm_extract import (
    COURSE_CSV_COLUMNS,
    ENGLISH_TEST_KEYS,
    EXTRACTED_CSV_REL,
    build_deterministic_row,
    build_output_json,
    combine_stage2_llm_parts,
    configure_code_dir,
    course_slug_from_url,
    fill_template,
    finalize_academic_requirements_metadata,
    enrich_entry_parsed,
    enrich_stage1_from_markdown,
    extract_stage1_fields_from_md,
    parser_hints_payload,
    index_row_to_entry,
    infer_course_level,
    infer_degree_name,
    load_template,
    merge_stage2_row,
    normalize_row,
    parse_bangladesh_requirements,
    read_course_index_csv,
    run_stage2_llm_part,
    save_audit,
    serialize_csv_value,
    split_frontmatter,
    update_course_index_outputs,
    utc_now,
    load_uni_content,
    load_uni_sections,
    infer_course_name,
)
from uni_paths import resolve_code_dir, resolve_output_dir
from study_level import extraction_dir

_SHARED_DIR = Path(__file__).resolve().parent
PROMPT_2_ENTRY = _SHARED_DIR / "prompt_2_entry.md"
ENTRY_RERUN_PROGRESS = Path("extracted") / "entry_rerun_progress.json"


def load_entry_rerun_progress(output_dir: Path) -> dict:
    path = output_dir / ENTRY_RERUN_PROGRESS
    if not path.exists():
        return {"completed": [], "failed": [], "updated_at": utc_now()}
    return json.loads(path.read_text(encoding="utf-8"))


def save_entry_rerun_progress(output_dir: Path, progress: dict) -> None:
    path = output_dir / ENTRY_RERUN_PROGRESS
    path.parent.mkdir(parents=True, exist_ok=True)
    progress["updated_at"] = utc_now()
    path.write_text(json.dumps(progress, indent=2), encoding="utf-8")


def load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_existing_stage2_parts(audit_dir: Path) -> tuple[dict, dict, dict]:
    """Load english, scholarship, and deposit Stage 2 parts from saved audits."""
    english = load_json_dict(audit_dir / "english_requirements_parsed.json")
    scholarship = load_json_dict(audit_dir / "scholarship_parsed.json")
    deposit = load_json_dict(audit_dir / "initial_deposit_parsed.json")

    combined = load_json_dict(audit_dir / "stage2_llm_parsed.json")
    if combined:
        if not english:
            english = {
                key: combined[key]
                for key in (
                    "ieltsMinOverall",
                    "ieltsMinSection",
                    "toeflMinOverall",
                    "toeflMinSection",
                    "pteMinOverall",
                    "pteMinSection",
                    "AcademicRequirementsMetaData",
                )
                if key in combined
            }
        if not scholarship:
            scholarship = {
                key: combined[key]
                for key in (
                    "scholarshipName",
                    "scholarshipAmount",
                    "scholarshipType",
                    "scholarshipMetaData",
                )
                if key in combined
            }
        if not deposit:
            deposit = {
                key: combined[key]
                for key in ("initialDeposit", "feesMetaData")
                if key in combined
            }
    return english, scholarship, deposit


def upsert_extracted_csv_row(output_path: Path, row: dict[str, object]) -> None:
    rows: list[dict[str, str]] = []
    if output_path.exists():
        with output_path.open(newline="", encoding="utf-8-sig") as handle:
            lines = handle.readlines()
        start = 1 if lines and lines[0].startswith("sep=") else 0
        reader = csv.DictReader(lines[start:], delimiter="\t")
        rows = list(reader)

    course_url = str(row.get("courseUrlExternal", "") or "").strip()
    serialized = {col: serialize_csv_value(row.get(col, "")) for col in COURSE_CSV_COLUMNS}
    replaced = False
    for index, existing in enumerate(rows):
        if str(existing.get("courseUrlExternal", "") or "").strip() == course_url:
            rows[index] = serialized
            replaced = True
            break
    if not replaced:
        rows.append(serialized)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        handle.write("sep=\t\n")
        writer = csv.DictWriter(handle, fieldnames=COURSE_CSV_COLUMNS, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


def finalize_extracted_course(
    *,
    code_dir: Path,
    course_entry: dict,
    stage1_json: dict,
    entry_json: dict,
    english_json: dict,
    scholarship_json: dict,
    deposit_json: dict,
    uni_content: str,
    english_content: str,
    entry_content: str,
    course_level: str,
    course_name: str,
    course_url: str,
    course_body: str,
    degree_name: str,
    university_name: str,
    audit_dir: Path,
) -> tuple[dict[str, object], str, str]:
    llm_json = combine_stage2_llm_parts(
        entry_json,
        english_json,
        scholarship_json,
        deposit_json,
    )
    save_audit(audit_dir, "stage2_llm_parsed.json", json.dumps(llm_json, indent=2, ensure_ascii=False))
    stage2_content = json.dumps(llm_json, ensure_ascii=False)

    deterministic = build_deterministic_row(
        stage1_json,
        university_name=university_name,
        course_url=course_url,
        course_name=course_name,
        degree_name=degree_name,
    )
    stage2_json = merge_stage2_row(
        deterministic,
        llm_json,
        uni_content=uni_content,
        entry_content=entry_content,
        course_level=course_level,
        course_body=course_body,
    )
    stage2_json["AcademicRequirementsMetaData"] = finalize_academic_requirements_metadata(
        stage2_json.get("AcademicRequirementsMetaData"),
        stage1_json=stage1_json,
        uni_content=uni_content,
        english_content=english_content,
        entry_content=entry_content,
        course_level=course_level,
        english_scalars={key: llm_json.get(key, "") for key in ENGLISH_TEST_KEYS},
        course_name=course_name,
        course_body=course_body,
    )
    stage2_json["uniName"] = university_name
    stage2_json["courseUrlExternal"] = course_url
    stage2_json["courseScraped"] = course_url
    save_audit(audit_dir, "stage2_parsed.json", json.dumps(stage2_json, indent=2, default=str))

    output_json = build_output_json(
        stage1_json,
        llm_json,
        university_name=university_name,
        course_name=course_name,
        course_url=course_url,
        requirements=stage2_json.get("requirements"),
        academic_metadata=stage2_json.get("AcademicRequirementsMetaData"),
    )
    output_json_text = json.dumps(output_json, ensure_ascii=False, default=str)
    save_audit(audit_dir, "output.json", json.dumps(output_json, indent=2, ensure_ascii=False, default=str))

    row = normalize_row(stage2_json, university_name, course_url)
    if course_entry.get("courseName"):
        row["courseName"] = course_entry["courseName"]
        row["programmeName"] = course_entry["courseName"]
    if course_entry.get("degreeName"):
        row["degreeName"] = course_entry["degreeName"]
    row["uniName"] = university_name
    if not row.get("Result"):
        row["Result"] = "ok"
    row["Paste_AI_output"] = (
        f"{audit_dir.relative_to(resolve_output_dir(code_dir)).as_posix()}/stage2_llm_parsed.json"
    )
    return row, stage2_content, output_json_text


def rerun_entry_requirements_course(
    code_dir: Path,
    course_entry: dict,
    *,
    model: str | None = None,
    host: str | None = None,
    use_llm: bool = True,
) -> tuple[dict[str, object], str, str]:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    university_name = code_dir.parent.name
    course_url = course_entry.get("course_url") or course_entry.get("courseUrlExternal", "")
    study_level = course_entry.get("study_level", "").strip()
    slug = course_slug_from_url(course_url)
    audit_dir = extraction_dir(output_dir, slug, study_level)

    stage1_path = audit_dir / "stage1_parsed.json"
    if not stage1_path.exists():
        raise FileNotFoundError(f"Missing {stage1_path.relative_to(output_dir)} — run full llm_extract first")

    stage1_json = json.loads(stage1_path.read_text(encoding="utf-8"))
    course_path = output_dir / course_entry["clean_md"]
    _, course_body = split_frontmatter(course_path.read_text(encoding="utf-8"))
    course_name = course_entry.get("courseName") or infer_course_name(course_body, course_url)
    course_level = infer_course_level(course_name, course_url, study_level)
    degree_name = course_entry.get("degreeName") or infer_degree_name(course_name)
    uni_sections = load_uni_sections(output_dir)
    uni_content = load_uni_content(output_dir)
    grounding_warnings: list[str] = []
    parser_hints = extract_stage1_fields_from_md(course_body)
    save_audit(
        audit_dir,
        "parser_hints.json",
        json.dumps(parser_hints_payload(parser_hints, course_body), indent=2, ensure_ascii=False),
    )
    stage1_json = enrich_stage1_from_markdown(
        stage1_json,
        course_body=course_body,
        course_name=course_name,
        course_url=course_url,
        warnings=grounding_warnings,
    )
    save_audit(
        audit_dir,
        "extraction_warnings.json",
        json.dumps({"grounding": grounding_warnings}, indent=2, ensure_ascii=False),
    )
    save_audit(audit_dir, "stage1_parsed.json", json.dumps(stage1_json, indent=2, ensure_ascii=False))
    stage1_json_text = json.dumps(stage1_json, indent=2, ensure_ascii=False)

    if use_llm:
        prompt_2_entry = load_template(PROMPT_2_ENTRY)
        entry_json = run_stage2_llm_part(
            audit_dir=audit_dir,
            name="entry_requirement",
            prompt=fill_template(
                prompt_2_entry,
                COURSE_NAME=course_name,
                COURSE_URL=course_url,
                COURSE_LEVEL=course_level,
                STAGE1_JSON=stage1_json_text,
                ENTRY_CONTENT=uni_sections.get("entry", ""),
            ),
            model=model,
            host=host,
        )
        entry_json = enrich_entry_parsed(
            entry_json,
            uni_sections.get("entry", ""),
            course_level=course_level,
            stage1_json=stage1_json,
            course_name=course_name,
            course_body=course_body,
        )
        save_audit(
            audit_dir,
            "entry_requirement_parsed.json",
            json.dumps(entry_json, indent=2, ensure_ascii=False),
        )
    else:
        entry_json = enrich_entry_parsed(
            {
                "requirements": parse_bangladesh_requirements(
                    uni_content,
                    course_level,
                    entry_content=uni_sections.get("entry", ""),
                ),
                "AcademicRequirementsMetaData": [],
            },
            uni_sections.get("entry", ""),
            course_level=course_level,
            stage1_json=stage1_json,
            course_name=course_name,
            course_body=course_body,
        )
        save_audit(
            audit_dir,
            "entry_requirement_parsed.json",
            json.dumps(entry_json, indent=2, ensure_ascii=False),
        )

    english_json, scholarship_json, deposit_json = load_existing_stage2_parts(audit_dir)
    return finalize_extracted_course(
        code_dir=code_dir,
        course_entry=course_entry,
        stage1_json=stage1_json,
        entry_json=entry_json,
        english_json=english_json,
        scholarship_json=scholarship_json,
        deposit_json=deposit_json,
        uni_content=uni_content,
        english_content=uni_sections.get("english", ""),
        entry_content=uni_sections.get("entry", ""),
        course_level=course_level,
        course_name=course_name,
        course_url=course_url,
        course_body=course_body,
        degree_name=degree_name,
        university_name=university_name,
        audit_dir=audit_dir,
    )


def run_entry_rerun(
    code_dir: Path,
    *,
    limit: int | None = None,
    resume: bool = False,
    model: str | None = None,
    host: str | None = None,
    use_llm: bool = True,
    normalize: bool = False,
    export_dev_csv: bool = False,
    skip_uni_validation: bool = False,
) -> None:
    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    configure_code_dir(code_dir)
    if not skip_uni_validation:
        from validate_uni_clean import ensure_uni_clean_valid

        ensure_uni_clean_valid(output_dir, university_name=code_dir.parent.name, code_dir=code_dir)

    courses = [index_row_to_entry(row) for row in read_course_index_csv(output_dir)]
    if limit is not None:
        courses = courses[:limit]

    progress = load_entry_rerun_progress(output_dir)
    completed = set(progress.get("completed", []))
    output_csv = output_dir / EXTRACTED_CSV_REL

    mode = "LLM entry re-extract" if use_llm else "JSON merge-only entry fix"
    print(f"University: {code_dir.parent.name}", flush=True)
    print(f"Mode: {mode}", flush=True)
    print(f"Courses to process: {len(courses)}", flush=True)
    print(f"Output CSV: {output_csv.relative_to(output_dir)}", flush=True)

    skip_batch = 0
    for index, entry in enumerate(courses, start=1):
        slug = course_slug_from_url(entry["course_url"])
        if resume and slug in completed:
            skip_batch += 1
            continue
        if skip_batch:
            print(f"Resume: skipped {skip_batch} already-completed course(s)", flush=True)
            skip_batch = 0

        print(f"[{index}/{len(courses)}] {entry['md_file']} — {entry['course_url']}", flush=True)
        try:
            row, stage2_output, output_json = rerun_entry_requirements_course(
                code_dir,
                entry,
                model=model,
                host=host,
                use_llm=use_llm,
            )
            upsert_extracted_csv_row(output_csv, row)
            update_course_index_outputs(
                output_dir,
                md_file=entry["md_file"],
                stage1_output="",
                stage2_output=stage2_output,
                output_json=output_json,
            )
            completed.add(slug)
            progress["completed"] = sorted(completed)
            save_entry_rerun_progress(output_dir, progress)
            reqs = row.get("requirements", [])
            print(f"  -> requirements: {reqs}", flush=True)
            print(f"  -> updated {output_csv.name}", flush=True)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr, flush=True)
            failed = progress.setdefault("failed", [])
            if slug not in failed:
                failed.append(slug)
            save_entry_rerun_progress(output_dir, progress)
            raise

    if normalize or export_dev_csv:
        from normalize_admission_data import normalize_extracted_courses
        from export_dev_courses import export_dev_courses

        if normalize:
            print("\n==> Re-normalize extracted courses", flush=True)
            written = normalize_extracted_courses(code_dir)
            print(f"Wrote {len(written)} normalized.json file(s)", flush=True)
        if export_dev_csv:
            print("\n==> Export dev_courses CSV", flush=True)
            export_dev_courses(code_dir)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-run Bangladesh entry requirements for extracted courses."
    )
    parser.add_argument(
        "university_dir",
        nargs="?",
        default=".",
        help="University code/ folder",
    )
    parser.add_argument("--limit", type=int, help="Process first N courses only")
    parser.add_argument(
        "--resume",
        action="store_true",
        help=f"Skip slugs already listed in {ENTRY_RERUN_PROGRESS.as_posix()}",
    )
    parser.add_argument("--model", default=None, help="Ollama model (default from ollama_client)")
    parser.add_argument("--host", default=None, help="Ollama host")
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip LLM; fix requirements from bangladesh-entry JSON only (fast)",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="After rerun, rewrite extracted/*/normalized.json",
    )
    parser.add_argument(
        "--export-dev-csv",
        action="store_true",
        help="After rerun (and --normalize if set), export dev_courses CSV",
    )
    parser.add_argument(
        "--skip-uni-validation",
        action="store_true",
        help="Skip output/clean/uni validation gate before entry rerun",
    )
    args = parser.parse_args()

    try:
        code_dir = configure_code_dir(Path(args.university_dir))
        run_entry_rerun(
            code_dir,
            limit=args.limit,
            resume=args.resume,
            model=args.model,
            host=args.host,
            use_llm=not args.merge_only,
            normalize=args.normalize or args.export_dev_csv,
            export_dev_csv=args.export_dev_csv,
            skip_uni_validation=args.skip_uni_validation,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


class EntryRequirementRerunner:
    """Re-run Stage 2a (Bangladesh entry requirements) for extracted courses."""

    ENTRY_RERUN_PROGRESS = ENTRY_RERUN_PROGRESS
    PROMPT_2_ENTRY = PROMPT_2_ENTRY

    load_entry_rerun_progress = staticmethod(load_entry_rerun_progress)
    save_entry_rerun_progress = staticmethod(save_entry_rerun_progress)
    load_json_dict = staticmethod(load_json_dict)
    load_existing_stage2_parts = staticmethod(load_existing_stage2_parts)
    upsert_extracted_csv_row = staticmethod(upsert_extracted_csv_row)
    finalize_extracted_course = staticmethod(finalize_extracted_course)
    rerun_entry_requirements_course = staticmethod(rerun_entry_requirements_course)
    run_entry_rerun = staticmethod(run_entry_rerun)


# Backward-compatible module-level aliases


if __name__ == "__main__":
    raise SystemExit(main())
