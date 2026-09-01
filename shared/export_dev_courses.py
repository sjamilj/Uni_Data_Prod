#!/usr/bin/env python3
"""Export output/extracted/*/normalized.json to dev_courses_{UNIVERSITY_NAME}.csv."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from llm_extract import (
    course_slug_from_url,
    infer_degree_name,
    index_row_to_entry,
    read_course_index_csv,
)
from scrape_course_urls import ENV_FILE, load_env_file
from study_level import extraction_dir, intake_start_year_from_md_path, iter_extracted_json
from uni_paths import resolve_code_dir, resolve_output_dir

DEV_COURSE_CSV_COLUMNS = [
    "uniName",
    "programmeName",
    "courseName",
    "minDegreeName",
    "minGpa",
    "higherDegreeName",
    "higherGpa",
    "AcademicRequirementsMetaData",
    "intakeInfo",
    "courseDuration",
    "tuitionFee",
    "currency",
    "initialDeposit",
    "applicationFee",
    "feesMetaData",
    "commission",
    "applicationDeadline",
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
    "scholarshipName",
    "scholarshipAmount",
    "scholarshipType",
    "scholarshipMetaData",
    "degreeName",
    "courseUrlExternal",
]

JSON_COLUMNS = frozenset(
    {
        "AcademicRequirementsMetaData",
        "feesMetaData",
        "scholarshipMetaData",
    }
)


class PortalLookup:
    """Lookup programmeName/degreeName from a university portal CSV."""

    def __init__(self) -> None:
        self.by_url: dict[str, dict[str, str]] = {}
        self.by_name: dict[str, dict[str, str]] = {}
        self.by_both: dict[tuple[str, str], dict[str, str]] = {}
        self.row_count = 0

    def __bool__(self) -> bool:
        return self.row_count > 0

    @staticmethod
    def normalize_course_url_key(url: str) -> str:
        url = (url or "").strip()
        if not url:
            return ""
        return urlparse(url).path.rstrip("/").lower()

    @staticmethod
    def normalize_course_name_key(name: str) -> str:
        return " ".join((name or "").strip().split()).casefold()

    @staticmethod
    def portal_row_from_csv(row: dict[str, str]) -> dict[str, str]:
        return {
            "programmeName": (row.get("programmeName") or "").strip(),
            "degreeName": (row.get("degreeName") or "").strip(),
        }

    @classmethod
    def load(cls, portal_path: Path) -> PortalLookup:
        lookup = cls()
        if not portal_path.is_file():
            return lookup

        with portal_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                url_key = cls.normalize_course_url_key(row.get("courseUrlExternal", ""))
                name_key = cls.normalize_course_name_key(row.get("courseName", ""))
                if not url_key and not name_key:
                    continue
                entry = cls.portal_row_from_csv(row)
                lookup.row_count += 1
                if url_key:
                    lookup.by_url[url_key] = entry
                if name_key:
                    lookup.by_name[name_key] = entry
                if url_key and name_key:
                    lookup.by_both[(url_key, name_key)] = entry
        return lookup

    def resolve_row(self, url: str, course_name: str) -> dict[str, str] | None:
        url_key = self.normalize_course_url_key(url)
        name_key = self.normalize_course_name_key(course_name)

        if url_key and name_key:
            portal_row = self.by_both.get((url_key, name_key))
            if portal_row:
                return portal_row
        if url_key:
            portal_row = self.by_url.get(url_key)
            if portal_row:
                return portal_row
        if name_key:
            portal_row = self.by_name.get(name_key)
            if portal_row:
                return portal_row
        return None

    def apply_to_row(self, row: dict[str, object]) -> dict[str, object]:
        portal_row = self.resolve_row(
            str(row.get("courseUrlExternal") or ""),
            str(row.get("courseName") or ""),
        )
        if not portal_row:
            row["programmeName"] = ""
            return row
        if portal_row.get("programmeName"):
            row["programmeName"] = portal_row["programmeName"]
        else:
            row["programmeName"] = ""
        if portal_row.get("degreeName") and not str(row.get("degreeName") or "").strip():
            row["degreeName"] = portal_row["degreeName"]
        return row


class DevCoursesExporter:
    """Export normalized.json files to dev_courses_{UNIVERSITY_NAME}.csv."""

    DEV_COURSE_CSV_COLUMNS = DEV_COURSE_CSV_COLUMNS
    JSON_COLUMNS = JSON_COLUMNS

    @staticmethod
    def load_env_config(code_dir: Path) -> tuple[str, str]:
        env_path = code_dir / ENV_FILE
        if not env_path.is_file():
            raise FileNotFoundError(f"{env_path} not found")
        env = load_env_file(env_path)
        university_name = (env.get("UNIVERSITY_NAME") or "").strip()
        if not university_name:
            raise ValueError(f"{env_path}: UNIVERSITY_NAME is required")
        university_base_url = (env.get("UNIVERSITY_BASE_URL") or "").strip().rstrip("/")
        if not university_base_url:
            raise ValueError(f"{env_path}: UNIVERSITY_BASE_URL is required")
        return university_name, university_base_url

    @staticmethod
    def resolve_portal_csv_path(code_dir: Path, university_name: str) -> Path:
        return resolve_code_dir(code_dir).parent / f"{university_name}_portal.csv"

    @staticmethod
    def resolve_course_url_external(course_url: str, university_base_url: str) -> str:
        course_url = (course_url or "").strip()
        university_base_url = (university_base_url or "").strip().rstrip("/")
        if not course_url:
            return ""
        if not university_base_url:
            return course_url
        path = urlparse(course_url).path or ""
        if not path:
            return university_base_url
        return f"{university_base_url}{path}"

    @staticmethod
    def discover_normalized_files(output_dir: Path) -> list[Path]:
        extracted_dir = output_dir / "extracted"
        if not extracted_dir.is_dir():
            return []
        paths = iter_extracted_json(extracted_dir, "normalized.json")
        return [path for path in paths if path.is_file()]

    def dedupe_normalized_by_course_name(self, paths: list[Path]) -> list[Path]:
        """When the same courseName appears in multiple intakes, prefer the latest year."""
        grouped: dict[str, list[Path]] = {}
        for path in paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            key = PortalLookup.normalize_course_name_key(str(data.get("courseName") or ""))
            if not key:
                key = path.parent.name
            grouped.setdefault(key, []).append(path)

        selected: list[Path] = []
        for _key, group in grouped.items():
            if len(group) == 1:
                selected.append(group[0])
                continue
            selected.append(
                max(
                    group,
                    key=lambda path: (
                        intake_start_year_from_md_path(path.parent),
                        path.as_posix().lower(),
                    ),
                )
            )
        return sorted(selected, key=lambda path: path.as_posix().lower())

    def normalized_paths_from_course_index(self, output_dir: Path) -> list[Path]:
        """Resolve normalized.json paths for each row in courses.csv (canonical index)."""
        paths: list[Path] = []
        missing: list[str] = []
        for row in read_course_index_csv(output_dir):
            entry = index_row_to_entry(row)
            course_url = entry.get("course_url") or entry.get("courseUrlExternal", "")
            slug = course_slug_from_url(course_url)
            study_level = entry.get("study_level", "").strip()
            norm_path = extraction_dir(output_dir, slug, study_level) / "normalized.json"
            if norm_path.is_file():
                paths.append(norm_path)
            else:
                missing.append(entry.get("md_file") or course_url)
        if missing:
            print(
                f"Warning: {len(missing)} index course(s) missing normalized.json — skipped",
                flush=True,
            )
        return paths

    def select_normalized_paths(self, output_dir: Path) -> list[Path]:
        index_path = output_dir / "courses.csv"
        if index_path.is_file():
            return self.normalized_paths_from_course_index(output_dir)
        return self.dedupe_normalized_by_course_name(self.discover_normalized_files(output_dir))

    @staticmethod
    def serialize_csv_value(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def normalized_to_dev_row(
        self,
        data: dict,
        university_name: str,
        university_base_url: str,
        portal_lookup: PortalLookup | None = None,
    ) -> dict[str, object]:
        course_name = str(data.get("courseName") or "")
        programme_name = str(data.get("programmeName") or "")
        raw_course_url = str(data.get("courseUrlExternal") or data.get("courseUrl") or "")

        row: dict[str, object] = {col: "" for col in self.DEV_COURSE_CSV_COLUMNS}
        row["uniName"] = university_name
        row["programmeName"] = programme_name
        row["courseName"] = course_name
        row["degreeName"] = str(data.get("degreeName") or "") or infer_degree_name(course_name)
        row["courseUrlExternal"] = self.resolve_course_url_external(
            raw_course_url,
            university_base_url,
        )

        for col in self.DEV_COURSE_CSV_COLUMNS:
            if col in {
                "uniName",
                "programmeName",
                "courseName",
                "degreeName",
                "courseUrlExternal",
                "commission",
            }:
                continue
            value = data.get(col, "")
            if value is None:
                value = [] if col in self.JSON_COLUMNS else ""
            row[col] = value

        if portal_lookup:
            portal_lookup.apply_to_row(row)

        return row

    def write_dev_courses_csv(self, output_path: Path, rows: list[dict[str, object]]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle, delimiter=",", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(self.DEV_COURSE_CSV_COLUMNS)
            for row in rows:
                writer.writerow(
                    [self.serialize_csv_value(row.get(col, "")) for col in self.DEV_COURSE_CSV_COLUMNS]
                )

    def export(
        self,
        code_dir: Path,
        *,
        limit: int | None = None,
    ) -> Path:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        university_name, university_base_url = self.load_env_config(code_dir)
        output_path = output_dir / f"dev_courses_{university_name}.csv"
        portal_path = self.resolve_portal_csv_path(code_dir, university_name)
        portal_lookup = PortalLookup.load(portal_path)
        if portal_lookup:
            print(f"Loaded {portal_lookup.row_count} portal row(s) from {portal_path}")
        else:
            print(
                f"No portal CSV at {portal_path} — programmeName left empty; "
                "degreeName from normalized.json or inferred"
            )

        normalized_paths = self.select_normalized_paths(output_dir)
        if limit is not None:
            normalized_paths = normalized_paths[:limit]
        if not normalized_paths:
            raise FileNotFoundError(
                f"No normalized.json files found under {output_dir / 'extracted'}"
            )

        rows: list[dict[str, object]] = []
        for path in normalized_paths:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                self.normalized_to_dev_row(
                    data,
                    university_name,
                    university_base_url,
                    portal_lookup,
                )
            )

        self.write_dev_courses_csv(output_path, rows)
        from validate_dev_courses import print_validation_report, validate_dev_courses_csv

        report = validate_dev_courses_csv(output_path, code_dir)
        print_validation_report(report)
        return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert output/extracted/{study_level}/{slug}/normalized.json into "
            "dev_courses_{UNIVERSITY_NAME}.csv. When courses.csv exists, export "
            "matches that index (latest intake per course name)."
        )
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        default=".",
        help="University code/ directory containing .env (default: cwd)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Export only the first N normalized.json files",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output_path = DevCoursesExporter().export(Path(args.code_dir), limit=args.limit)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Wrote {output_path}")
    return 0


# Backward-compatible module-level aliases
load_env_config = DevCoursesExporter.load_env_config
normalize_course_url_key = PortalLookup.normalize_course_url_key
normalize_course_name_key = PortalLookup.normalize_course_name_key
resolve_portal_csv_path = DevCoursesExporter.resolve_portal_csv_path
portal_row_from_csv = PortalLookup.portal_row_from_csv
load_portal_lookup = PortalLookup.load
resolve_portal_row = PortalLookup().resolve_row
apply_portal_lookup = PortalLookup().apply_to_row
resolve_course_url_external = DevCoursesExporter.resolve_course_url_external
discover_normalized_files = DevCoursesExporter().discover_normalized_files
dedupe_normalized_by_course_name = DevCoursesExporter().dedupe_normalized_by_course_name
normalized_paths_from_course_index = DevCoursesExporter().normalized_paths_from_course_index
select_normalized_paths = DevCoursesExporter().select_normalized_paths
serialize_csv_value = DevCoursesExporter.serialize_csv_value
normalized_to_dev_row = DevCoursesExporter().normalized_to_dev_row
write_dev_courses_csv = DevCoursesExporter().write_dev_courses_csv
export_dev_courses = DevCoursesExporter().export


if __name__ == "__main__":
    raise SystemExit(main())
