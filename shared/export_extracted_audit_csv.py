#!/usr/bin/env python3
"""Export extracted audit JSON files to a flat CSV for missing-field debugging."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED.parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from degree_name_inference import (  # noqa: E402
    DegreeInferenceInput,
    DegreeNameInferrer,
    apply_degree_to_course_dir,
    find_course_markdown,
    infer_degree_heuristic,
    markdown_excerpt_for_degree,
)
from export_dev_courses import serialize_csv_value  # noqa: E402
from llm_extract import course_slug_from_url, normalize_requirements_list  # noqa: E402
from missing_field_stats import MissingFieldStats  # noqa: E402
from study_level import extraction_dir  # noqa: E402
from study_level import (  # noqa: E402
    LEVEL_MATCH_ORDER,
    levels_for_url,
    load_url_levels,
)

DEFAULT_JSON_FILES = ("entry_requirement_parsed.json",)

JSON_PATH_PRESETS: dict[str, list[str]] = {
    "entry_requirement_parsed.json": [
        "requirements",
        "AcademicRequirementsMetaData",
    ],
    "stage1_parsed.json": [
        "courseName",
        "degreeName",
        "tuitionFee",
        "currency",
        "intakeInfo",
        "courseDuration",
        "AcademicRequirementsMetaData",
    ],
    "english_requirements_parsed.json": [
        "ieltsMinOverall",
        "ieltsMinSection",
        "toeflMinOverall",
        "toeflMinSection",
        "pteMinOverall",
        "pteMinSection",
        "AcademicRequirementsMetaData",
    ],
}

BASE_COLUMNS = (
    "courseName",
    "courseUrlExternal",
    "errorReason",
    "study_level",
    "slug",
    "json_files_found",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Filter reviewed dev_courses rows by missing field(s) and export "
            "selected extracted JSON audit files to a flat CSV."
        )
    )
    parser.add_argument(
        "--university",
        required=True,
        help='University folder name, e.g. "Keele University"',
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repo root (default: parent of shared/)",
    )
    parser.add_argument(
        "--missing-field",
        action="append",
        default=[],
        dest="missing_fields",
        help="Include rows where this reviewed CSV field is empty (repeatable)",
    )
    parser.add_argument(
        "--missing-any",
        action="append",
        default=[],
        dest="missing_any",
        help="Include rows where any listed field is empty (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="append",
        default=[],
        dest="json_files",
        help="Audit JSON filename under each course folder (repeatable)",
    )
    parser.add_argument(
        "--paths",
        default="",
        help="Comma-separated JSON paths to export for every --json file",
    )
    parser.add_argument(
        "--all-courses",
        action="store_true",
        help="Export every reviewed course (skip missing-field filter)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: {uni}/output/extracted_audit.csv)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output CSV",
    )
    parser.add_argument(
        "--include-markdown",
        action="store_true",
        help="Include clean_md_path and clean_md_excerpt columns from output/clean/courses",
    )
    parser.add_argument(
        "--infer-degree",
        action="store_true",
        help="Infer degreeName from markdown heuristics and LLM (adds inference columns)",
    )
    parser.add_argument(
        "--apply-degree",
        action="store_true",
        help="Patch stage1_parsed.json, output.json, and normalized.json with chosen degreeName",
    )
    return parser.parse_args(argv)


def json_stem(filename: str) -> str:
    return Path(filename).stem


def column_prefix(filename: str) -> str:
    return f"{json_stem(filename)}__"


def paths_for_json(filename: str, explicit_paths: list[str]) -> list[str]:
    if explicit_paths:
        return explicit_paths
    return JSON_PATH_PRESETS.get(filename, ["requirements", "AcademicRequirementsMetaData"])


def get_value_by_path(data: object, path: str) -> object:
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return ""
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return ""
            index = int(part)
            if index < 0 or index >= len(current):
                return ""
            current = current[index]
            continue
        return ""
    return current


def requirements_schema_signature(requirements: object) -> str:
    if not isinstance(requirements, list) or not requirements:
        return "empty"
    first = requirements[0]
    if isinstance(first, dict):
        return ",".join(sorted(first.keys()))
    return type(first).__name__


def metadata_text(metadata: object, subtitle: str) -> str:
    if not isinstance(metadata, list):
        return ""
    target = subtitle.strip().lower()
    chunks: list[str] = []
    for block in metadata:
        if not isinstance(block, dict):
            continue
        block_subtitle = str(block.get("subtitle", "") or "").strip().lower()
        if block_subtitle != target:
            continue
        description = block.get("description", [])
        if isinstance(description, str):
            chunks.append(description.strip())
            continue
        if isinstance(description, list):
            for item in description:
                text = str(item).strip()
                if text:
                    chunks.append(text)
    return " | ".join(chunks)


def entry_requirement_diagnostics(data: dict, study_level: str) -> dict[str, str]:
    requirements = data.get("requirements", [])
    metadata = data.get("AcademicRequirementsMetaData", [])
    normalized = normalize_requirements_list(
        requirements,
        course_level=study_level if study_level in LEVEL_MATCH_ORDER else "",
    )
    return {
        "req_count": str(len(requirements) if isinstance(requirements, list) else 0),
        "req_first_keys": requirements_schema_signature(requirements),
        "req_normalized_count": str(len(normalized)),
        "entry_text": metadata_text(metadata, "Entry Requirements"),
    }


def stage1_diagnostics(data: dict) -> dict[str, str]:
    metadata = data.get("AcademicRequirementsMetaData", [])
    degree_name = str(data.get("degreeName", "") or "").strip()
    return {
        "stage1_has_degreeName": "true" if degree_name else "false",
        "entry_text": metadata_text(metadata, "Entry Requirements"),
    }


def english_diagnostics(data: dict) -> dict[str, str]:
    metadata = data.get("AcademicRequirementsMetaData", [])
    return {
        "english_text": metadata_text(metadata, "English Requirement"),
    }


def diagnostics_for_json(filename: str, data: dict, study_level: str) -> dict[str, str]:
    if filename == "entry_requirement_parsed.json":
        return entry_requirement_diagnostics(data, study_level)
    if filename == "stage1_parsed.json":
        return stage1_diagnostics(data)
    if filename == "english_requirements_parsed.json":
        return english_diagnostics(data)
    return {}


def load_reviewed_rows(reviewed_csv: Path) -> list[dict[str, str]]:
    with reviewed_csv.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def row_matches_filter(
    row: dict[str, str],
    *,
    missing_fields: list[str],
    missing_any: list[str],
    all_courses: bool,
    stats: MissingFieldStats,
) -> bool:
    if all_courses:
        return True
    if missing_fields and not all(stats.is_empty(row.get(field)) for field in missing_fields):
        return False
    if missing_any and not any(stats.is_empty(row.get(field)) for field in missing_any):
        return False
    if not missing_fields and not missing_any:
        return True
    return True


def primary_level(levels: list[str]) -> str:
    if not levels:
        return "unknown"
    for level in LEVEL_MATCH_ORDER:
        if level in levels:
            return level
    return levels[0]


def read_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def build_audit_row(
    reviewed_row: dict[str, str],
    *,
    output_dir: Path,
    json_files: list[str],
    explicit_paths: list[str],
    url_levels: dict[str, list[str]],
    include_markdown: bool = False,
) -> dict[str, str]:
    course_url = reviewed_row.get("courseUrlExternal", "")
    slug = course_slug_from_url(course_url)
    levels = levels_for_url(
        course_url,
        url_levels=url_levels,
        course_name=reviewed_row.get("courseName", ""),
    )
    declared = (reviewed_row.get("studyLevel") or reviewed_row.get("study_level") or "").strip()
    study_level = declared or primary_level(levels)
    course_dir = extraction_dir(output_dir, slug, study_level)

    out: dict[str, str] = {
        "courseName": reviewed_row.get("courseName", ""),
        "courseUrlExternal": course_url,
        "errorReason": reviewed_row.get("errorReason", ""),
        "study_level": study_level,
        "slug": slug,
    }

    found_files: list[str] = []
    for filename in json_files:
        json_path = course_dir / filename
        prefix = column_prefix(filename)
        if json_path.is_file():
            found_files.append(filename)
        data = read_json_file(json_path)

        for path in paths_for_json(filename, explicit_paths):
            value = get_value_by_path(data, path) if data else ""
            out[f"{prefix}{path.replace('.', '_')}"] = serialize_csv_value(value)

        for key, value in diagnostics_for_json(filename, data, study_level).items():
            out[f"{prefix}{key}"] = value

    out["json_files_found"] = ",".join(found_files)
    out["course_dir"] = str(course_dir)

    if include_markdown:
        md_path = find_course_markdown(output_dir, slug)
        md_text = md_path.read_text(encoding="utf-8") if md_path and md_path.is_file() else ""
        out["clean_md_path"] = md_path.as_posix() if md_path else ""
        out["clean_md_excerpt"] = markdown_excerpt_for_degree(md_text) if md_text else ""

    return out


class ExtractedAuditCsvExporter:
    """Filter reviewed courses and export extracted audit JSON to CSV."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or _REPO_ROOT).resolve()
        self.stats = MissingFieldStats(self.repo_root)

    def resolve_paths(
        self,
        university_name: str,
        output: Path | None,
    ) -> tuple[Path, Path, Path]:
        uni_dir = self.stats.resolve_university_dir(university_name)
        reviewed_csv = self.stats.reviewed_csv_path(uni_dir, university_name)
        if not reviewed_csv.is_file():
            raise FileNotFoundError(f"Reviewed CSV not found: {reviewed_csv}")
        output_csv = output or (uni_dir / "output" / "extracted_audit.csv")
        return uni_dir, reviewed_csv, output_csv

    def export(
        self,
        university_name: str,
        *,
        missing_fields: list[str],
        missing_any: list[str],
        json_files: list[str],
        explicit_paths: list[str],
        all_courses: bool,
        output: Path | None = None,
        force: bool = False,
        include_markdown: bool = False,
        infer_degree: bool = False,
        apply_degree: bool = False,
    ) -> Path:
        uni_dir, reviewed_csv, output_csv = self.resolve_paths(university_name, output)
        if output_csv.exists() and not force:
            raise FileExistsError(f"Already exists: {output_csv} (use --force to overwrite)")

        rows = load_reviewed_rows(reviewed_csv)
        url_levels = load_url_levels(uni_dir / "output")
        output_dir = uni_dir / "output"

        selected = [
            row
            for row in rows
            if row_matches_filter(
                row,
                missing_fields=missing_fields,
                missing_any=missing_any,
                all_courses=all_courses,
                stats=self.stats,
            )
        ]

        if infer_degree or apply_degree:
            include_markdown = True

        audit_rows: list[dict[str, str]] = []
        for reviewed_row in selected:
            audit_row = build_audit_row(
                reviewed_row,
                output_dir=output_dir,
                json_files=json_files,
                explicit_paths=explicit_paths,
                url_levels=url_levels,
                include_markdown=include_markdown,
            )
            for field in missing_fields + missing_any:
                audit_row[f"reviewed_{field}"] = reviewed_row.get(field, "")
            audit_rows.append(audit_row)

        if infer_degree:
            self._attach_degree_inference(audit_rows, output_dir)

        patched = 0
        if apply_degree:
            for row in audit_rows:
                degree_name = row.get("chosen_degreeName", "").strip()
                course_dir = Path(row.get("course_dir", ""))
                if degree_name and course_dir.is_dir():
                    if apply_degree_to_course_dir(course_dir, degree_name):
                        patched += 1
            if patched:
                print(f"Patched degreeName on {patched} course(s).")
                print(
                    "Re-export with: python shared/export_dev_courses.py "
                    f'--code-dir "{uni_dir / "code"}"'
                )
                print(
                    'Then refresh report: python shared/missing_field_stats.py '
                    f'"{university_name}" --force'
                )

        columns = list(BASE_COLUMNS)
        if include_markdown:
            columns.extend(["clean_md_path", "clean_md_excerpt"])
        if infer_degree:
            columns.extend(
                ["heuristic_degreeName", "llm_degreeName", "chosen_degreeName"]
            )
        for field in missing_fields + missing_any:
            columns.append(f"reviewed_{field}")
        for filename in json_files:
            prefix = column_prefix(filename)
            for path in paths_for_json(filename, explicit_paths):
                col = f"{prefix}{path.replace('.', '_')}"
                if col not in columns:
                    columns.append(col)
            for key in diagnostics_for_json(filename, {}, "postgraduate"):
                col = f"{prefix}{key}"
                if col not in columns:
                    columns.append(col)

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(audit_rows)

        return output_csv

    @staticmethod
    def _attach_degree_inference(
        audit_rows: list[dict[str, str]],
        output_dir: Path,
    ) -> None:
        llm_inputs: list[DegreeInferenceInput] = []
        for row in audit_rows:
            course_name = row.get("courseName", "")
            study_level = row.get("study_level", "")
            md_excerpt = row.get("clean_md_excerpt", "")
            md_path = row.get("clean_md_path", "")
            md_text = ""
            if md_path:
                path = Path(md_path)
                if path.is_file():
                    md_text = path.read_text(encoding="utf-8")

            heuristic = infer_degree_heuristic(
                course_name,
                md_text,
                study_level=study_level,
            )
            row["heuristic_degreeName"] = heuristic
            row["llm_degreeName"] = ""
            row["chosen_degreeName"] = heuristic

            if not heuristic:
                llm_inputs.append(
                    DegreeInferenceInput(
                        course_name=course_name,
                        study_level=study_level,
                        md_excerpt=md_excerpt,
                        slug=row.get("slug", ""),
                        course_dir=Path(row.get("course_dir", "")),
                    )
                )

        if llm_inputs:
            print(f"LLM degreeName lookup for {len(llm_inputs)} course(s)")
            picks = DegreeNameInferrer().infer_with_llm(llm_inputs)
            for row in audit_rows:
                if row.get("chosen_degreeName"):
                    continue
                degree_name = picks.get(row.get("courseName", ""), "")
                row["llm_degreeName"] = degree_name
                row["chosen_degreeName"] = degree_name


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    json_files = args.json_files or list(DEFAULT_JSON_FILES)
    explicit_paths = [part.strip() for part in args.paths.split(",") if part.strip()]

    if not args.all_courses and not args.missing_fields and not args.missing_any:
        print(
            "Error: specify --missing-field, --missing-any, or --all-courses",
            file=sys.stderr,
        )
        return 1

    exporter = ExtractedAuditCsvExporter(args.repo_root)
    try:
        output_csv = exporter.export(
            args.university,
            missing_fields=args.missing_fields,
            missing_any=args.missing_any,
            json_files=json_files,
            explicit_paths=explicit_paths,
            all_courses=args.all_courses,
            output=args.output,
            force=args.force,
            include_markdown=args.include_markdown,
            infer_degree=args.infer_degree,
            apply_degree=args.apply_degree,
        )
    except (FileNotFoundError, FileExistsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
