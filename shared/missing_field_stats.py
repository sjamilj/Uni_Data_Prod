#!/usr/bin/env python3
"""Missing-field statistics for dev_courses_{university}_reviewed.csv by study level."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED.parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from export_dev_courses import DEV_COURSE_CSV_COLUMNS  # noqa: E402
from study_level import LEVEL_MATCH_ORDER, levels_for_url, load_url_levels  # noqa: E402
from validate_dev_courses import REQUIRED_NONEMPTY  # noqa: E402

REPORT_TXT_NAME = "missing_field_report.txt"

LEVEL_LABEL = {
    "foundation": "Foundation",
    "undergraduate": "Undergraduate",
    "postgraduate": "Postgraduate",
    "postgraduate_research": "Postgraduate Research",
    "other": "Other",
    "unknown": "Unknown",
}

KEY_FIELDS = (
    "degreeName",
    "courseDuration",
    "tuitionFee",
    "currency",
    "applicationDeadline",
)


@dataclass(frozen=True)
class MissingFieldReport:
    university_name: str
    reviewed_csv: Path
    report_txt: Path
    total_courses: int
    section_count: int


@dataclass(frozen=True)
class LevelStats:
    level_key: str
    label: str
    total: int
    missing_required: int
    field_missing: dict[str, int]
    error_counts: dict[str, int]


class MissingFieldStats:
    """Compute missing-field statistics grouped by study level."""

    REPORT_TXT_NAME = REPORT_TXT_NAME

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or _REPO_ROOT).resolve()

    @staticmethod
    def reviewed_csv_path(uni_dir: Path, university_name: str) -> Path:
        return uni_dir / "output" / f"dev_courses_{university_name}_reviewed.csv"

    @staticmethod
    def report_txt_path(uni_dir: Path) -> Path:
        return uni_dir / "output" / REPORT_TXT_NAME

    def resolve_university_dir(self, university_name: str) -> Path:
        uni_dir = self.repo_root / university_name
        if not uni_dir.is_dir():
            raise FileNotFoundError(f"University folder not found: {uni_dir}")
        return uni_dir

    @staticmethod
    def is_empty(value: object) -> bool:
        if value is None:
            return True
        text = str(value).strip()
        if not text:
            return True
        if text in ("[]", "{}", "null", "None"):
            return True
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list) and len(parsed) == 0:
                    return True
            except json.JSONDecodeError:
                pass
        return False

    @staticmethod
    def primary_level(levels: list[str]) -> str:
        if not levels:
            return "unknown"
        for level in LEVEL_MATCH_ORDER:
            if level in levels:
                return level
        return levels[0]

    @staticmethod
    def error_key(error_reason: str) -> str:
        err = (error_reason or "").strip()
        if not err:
            return "OK"
        if err.startswith("MISSING_REQUIRED_FIELD"):
            match = re.search(r"missing required field\(s\): ([^|]+)", err)
            return "MISSING: " + (match.group(1).strip() if match else "required")
        return err.split("|")[0].strip()[:80]

    def analyze_levels(
        self,
        university_name: str,
        *,
        reviewed_csv: Path | None = None,
    ) -> tuple[list[LevelStats], int, Path]:
        uni_dir = self.resolve_university_dir(university_name)
        csv_path = reviewed_csv or self.reviewed_csv_path(uni_dir, university_name)
        if not csv_path.is_file():
            raise FileNotFoundError(f"Reviewed CSV not found: {csv_path}")

        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        url_levels = load_url_levels(uni_dir / "output")
        by_level: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            levels = levels_for_url(
                row.get("courseUrlExternal", ""),
                url_levels=url_levels,
                course_name=row.get("courseName", ""),
            )
            by_level[self.primary_level(levels)].append(row)

        active_levels = sorted(
            by_level.keys(),
            key=lambda level: (
                list(LEVEL_MATCH_ORDER).index(level)
                if level in LEVEL_MATCH_ORDER
                else len(LEVEL_MATCH_ORDER)
            ),
        )

        fields = [col for col in DEV_COURSE_CSV_COLUMNS if col != "errorReason"]
        level_stats: list[LevelStats] = []

        for level in active_levels:
            group = by_level[level]
            total = len(group)
            label = LEVEL_LABEL.get(level, level)
            missing_required = sum(
                1
                for row in group
                if any(self.is_empty(row.get(field)) for field in REQUIRED_NONEMPTY)
            )
            field_missing = {
                field: sum(1 for row in group if self.is_empty(row.get(field)))
                for field in fields
            }
            err_counts: dict[str, int] = defaultdict(int)
            for row in group:
                err_counts[self.error_key(row.get("errorReason", ""))] += 1
            level_stats.append(
                LevelStats(
                    level_key=level,
                    label=label,
                    total=total,
                    missing_required=missing_required,
                    field_missing=field_missing,
                    error_counts=dict(err_counts),
                )
            )

        return level_stats, len(rows), csv_path

    @staticmethod
    def format_report_text(
        university_name: str,
        reviewed_csv: Path,
        level_stats: list[LevelStats],
        total_courses: int,
    ) -> str:
        lines: list[str] = []
        sep = "=" * 78
        dash = "-" * 78

        lines.append(sep)
        lines.append(f"{university_name} — missing field statistics")
        lines.append(sep)
        lines.append(f"Source: {reviewed_csv}")
        lines.append(f"Total courses: {total_courses}")
        lines.append("")
        lines.append("Required fields: " + ", ".join(REQUIRED_NONEMPTY))
        lines.append("")
        lines.append("Courses per level:")
        for stats in level_stats:
            lines.append(f"  {stats.label:22} {stats.total:>4}")
        lines.append("")
        lines.append(dash)
        lines.append("REQUIRED fields — courses missing at least one required field")
        lines.append(dash)
        for stats in level_stats:
            pct = 100 * stats.missing_required / stats.total if stats.total else 0
            lines.append(
                f"  {stats.label:22} {stats.missing_required:>4}/{stats.total}"
                f"  ({pct:.1f}%)"
            )

        lines.append("")
        lines.append(dash)
        lines.append("Key fields summary")
        lines.append(dash)
        for stats in level_stats:
            lines.append("")
            lines.append(f"{stats.label} ({stats.total} courses):")
            for field in KEY_FIELDS:
                missing = stats.field_missing.get(field, 0)
                pct = 100 * missing / stats.total if stats.total else 0
                lines.append(
                    f"  {field:22} {missing:>3}/{stats.total}"
                    f"  ({pct:.1f}% missing)"
                )

        lines.append("")
        lines.append(dash)
        lines.append("Per-field missing counts (empty cells)")
        lines.append(dash)
        active_labels = [stats.label for stats in level_stats]
        header = f"{'Field':26}" + "".join(f"{label[:14]:>14}" for label in active_labels)
        lines.append(header)
        lines.append("-" * len(header))

        all_fields = [col for col in DEV_COURSE_CSV_COLUMNS if col != "errorReason"]
        for field in all_fields:
            parts = [f"{field:26}"]
            for stats in level_stats:
                missing = stats.field_missing.get(field, 0)
                parts.append(f"{missing:>14}")
            lines.append("".join(parts))

        lines.append("")
        lines.append(dash)
        lines.append("errorReason breakdown")
        lines.append(dash)
        for stats in level_stats:
            lines.append("")
            lines.append(f"{stats.label}:")
            for key, count in sorted(
                stats.error_counts.items(),
                key=lambda item: (-item[1], item[0]),
            ):
                pct = 100 * count / stats.total if stats.total else 0
                lines.append(f"  {count:>3}  {key}  ({pct:.1f}%)")

        lines.append("")
        return "\n".join(lines) + "\n"

    def write_report_txt(
        self,
        text: str,
        report_path: Path,
        *,
        force: bool = False,
    ) -> Path:
        if report_path.exists() and not force:
            raise FileExistsError(f"Already exists: {report_path} (use --force to overwrite)")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
        return report_path

    def generate(
        self,
        university_name: str,
        *,
        force: bool = False,
        dry_run: bool = False,
        reviewed_csv: Path | None = None,
        report_txt: Path | None = None,
    ) -> MissingFieldReport:
        uni_dir = self.resolve_university_dir(university_name)
        level_stats, total_courses, reviewed_path = self.analyze_levels(
            university_name,
            reviewed_csv=reviewed_csv,
        )
        report_path = report_txt or self.report_txt_path(uni_dir)
        text = self.format_report_text(
            university_name,
            reviewed_path,
            level_stats,
            total_courses,
        )

        if not dry_run:
            self.write_report_txt(text, report_path, force=force)

        return MissingFieldReport(
            university_name=university_name,
            reviewed_csv=reviewed_path,
            report_txt=report_path,
            total_courses=total_courses,
            section_count=len(level_stats),
        )

    def print_summary(
        self,
        university_name: str,
        reviewed_csv: Path | None = None,
    ) -> None:
        level_stats, total, reviewed_path = self.analyze_levels(
            university_name,
            reviewed_csv=reviewed_csv,
        )
        print(
            self.format_report_text(
                university_name,
                reviewed_path,
                level_stats,
                total,
            ),
            end="",
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate missing-field statistics for a reviewed dev_courses CSV."
    )
    parser.add_argument(
        "university_name",
        help='University folder name, e.g. "Aston University"',
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repo root (default: parent of shared/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing report text file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary without writing report file",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print report path (no summary table)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stats = MissingFieldStats(args.repo_root)
    try:
        result = stats.generate(
            args.university_name,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, FileExistsError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        if args.dry_run:
            stats.print_summary(args.university_name)
        else:
            stats.print_summary(args.university_name)
            print(f"Wrote {result.report_txt}")
            print(f"Study levels: {result.section_count}")
    elif not args.dry_run:
        print(result.report_txt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
