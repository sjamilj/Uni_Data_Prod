#!/usr/bin/env python3
"""Split UK Course.csv into per-university portal CSV files.

Reads Uni_List.csv and writes one file per listed university:

  {University Folder}/{uniName}_portal.csv

Rows are filtered where UK Course.csv ``uniName`` matches exactly.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UK_COURSE_CSV = REPO_ROOT / "UK Course.csv"
DEFAULT_UNI_LIST_CSV = REPO_ROOT / "Uni_List.csv"
UNI_LIST_COLUMN = "Uni"
UNI_NAME_COLUMN = "uniName"


class PortalCoursesExporter:
    """Split master UK Course.csv into per-university portal CSV files."""

    UNI_LIST_COLUMN = UNI_LIST_COLUMN
    UNI_NAME_COLUMN = UNI_NAME_COLUMN

    def __init__(
        self,
        repo_root: Path,
        *,
        uk_course_csv: Path = DEFAULT_UK_COURSE_CSV,
        uni_list_csv: Path = DEFAULT_UNI_LIST_CSV,
    ) -> None:
        self.repo_root = repo_root
        self.uk_course_csv = uk_course_csv
        self.uni_list_csv = uni_list_csv

    @staticmethod
    def read_uni_list(path: Path) -> list[str]:
        if not path.is_file():
            raise FileNotFoundError(f"Uni list not found: {path}")
        names: list[str] = []
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or UNI_LIST_COLUMN not in reader.fieldnames:
                raise ValueError(f"{path}: expected column {UNI_LIST_COLUMN!r}")
            for row in reader:
                name = (row.get(UNI_LIST_COLUMN) or "").strip()
                if name:
                    names.append(name)
        if not names:
            raise ValueError(f"{path}: no universities listed")
        return names

    @staticmethod
    def load_courses_by_uni(path: Path) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
        if not path.is_file():
            raise FileNotFoundError(f"UK course file not found: {path}")
        by_uni: dict[str, list[dict[str, str]]] = defaultdict(list)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or UNI_NAME_COLUMN not in reader.fieldnames:
                raise ValueError(f"{path}: expected column {UNI_NAME_COLUMN!r}")
            fieldnames = list(reader.fieldnames)
            for row in reader:
                uni_name = (row.get(UNI_NAME_COLUMN) or "").strip()
                if not uni_name:
                    continue
                by_uni[uni_name].append({key: row.get(key, "") for key in fieldnames})
        return fieldnames, by_uni

    def portal_output_path(self, uni_name: str) -> Path:
        return self.repo_root / uni_name / f"{uni_name}_portal.csv"

    @staticmethod
    def write_portal_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    def export(self, *, only_uni: str | None = None) -> list[Path]:
        uni_names = self.read_uni_list(self.uni_list_csv)
        if only_uni:
            only_uni = only_uni.strip()
            if only_uni not in uni_names:
                raise ValueError(f"{only_uni!r} not found in {self.uni_list_csv}")
            uni_names = [only_uni]

        fieldnames, courses_by_uni = self.load_courses_by_uni(self.uk_course_csv)
        written: list[Path] = []
        missing_dirs: list[str] = []
        empty_unis: list[str] = []

        for uni_name in uni_names:
            uni_dir = self.repo_root / uni_name
            if not uni_dir.is_dir():
                missing_dirs.append(uni_name)
                continue

            rows = courses_by_uni.get(uni_name, [])
            if not rows:
                empty_unis.append(uni_name)

            output_path = self.portal_output_path(uni_name)
            self.write_portal_csv(output_path, fieldnames, rows)
            written.append(output_path)

        if missing_dirs:
            print(
                f"Warning: folder missing for {len(missing_dirs)} universit(ies): "
                + ", ".join(missing_dirs),
                file=sys.stderr,
            )
        if empty_unis:
            print(
                f"Warning: no rows in {self.uk_course_csv.name} for: "
                + ", ".join(empty_unis),
                file=sys.stderr,
            )

        return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Split UK Course.csv into per-university {uniName}_portal.csv files "
            "using Uni_List.csv"
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="F1 repository root (default: parent of shared/)",
    )
    parser.add_argument(
        "--uk-course-csv",
        type=Path,
        default=DEFAULT_UK_COURSE_CSV,
        help="Master UK course CSV (default: UK Course.csv)",
    )
    parser.add_argument(
        "--uni-list-csv",
        type=Path,
        default=DEFAULT_UNI_LIST_CSV,
        help="University list CSV (default: Uni_List.csv)",
    )
    parser.add_argument(
        "--uni",
        default=None,
        help="Export only this university (must appear in Uni_List.csv)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        exporter = PortalCoursesExporter(
            args.repo_root.resolve(),
            uk_course_csv=args.uk_course_csv.resolve(),
            uni_list_csv=args.uni_list_csv.resolve(),
        )
        written = exporter.export(only_uni=args.uni)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    for path in written:
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")
    print(f"Done: {len(written)} portal CSV file(s)")
    return 0


# Backward-compatible module-level aliases
read_uni_list = PortalCoursesExporter.read_uni_list
load_courses_by_uni = PortalCoursesExporter.load_courses_by_uni
write_portal_csv = PortalCoursesExporter.write_portal_csv


def portal_output_path(repo_root: Path, uni_name: str) -> Path:
    return PortalCoursesExporter(repo_root).portal_output_path(uni_name)


def export_portal_courses(
    repo_root: Path,
    *,
    uk_course_csv: Path,
    uni_list_csv: Path,
    only_uni: str | None = None,
) -> list[Path]:
    return PortalCoursesExporter(
        repo_root,
        uk_course_csv=uk_course_csv,
        uni_list_csv=uni_list_csv,
    ).export(only_uni=only_uni)


if __name__ == "__main__":
    raise SystemExit(main())
