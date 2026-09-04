#!/usr/bin/env python3
"""Copy a university's root variant CSV, reviewed dev_courses CSV, and clean/uni into REVIEW/."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED.parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from build_university_from_template import VARIANT_FILES  # noqa: E402
from missing_field_stats import MissingFieldStats, REPORT_TXT_NAME  # noqa: E402

REVIEW_DIR_NAME = "REVIEW"
UNI_CLEAN_REL = Path("output") / "clean" / "uni"
REVIEW_UNI_CLEAN_REL = Path("clean") / "uni"


@dataclass(frozen=True)
class ReviewPackageResult:
    university_name: str
    review_dir: Path
    variant_csv: Path
    reviewed_csv: Path
    missing_field_report_txt: Path
    uni_clean_files: tuple[Path, ...] = ()


class ReviewPackageBuilder:
    """Package variant CSV + reviewed dev_courses CSV for handoff."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or _REPO_ROOT).resolve()

    @staticmethod
    def find_variant_csv(uni_dir: Path) -> Path:
        matches = sorted(
            path
            for name in VARIANT_FILES
            if (path := uni_dir / name).is_file()
        )
        if not matches:
            names = ", ".join(sorted(VARIANT_FILES))
            raise FileNotFoundError(
                f"No variant CSV in {uni_dir}. Expected one of: {names}"
            )
        if len(matches) > 1:
            found = ", ".join(path.name for path in matches)
            raise ValueError(f"Multiple variant CSV files in {uni_dir}: {found}")
        return matches[0]

    @staticmethod
    def reviewed_csv_path(uni_dir: Path, university_name: str) -> Path:
        return uni_dir / "output" / f"dev_courses_{university_name}_reviewed.csv"

    @staticmethod
    def uni_clean_source_dir(uni_dir: Path) -> Path:
        return uni_dir / UNI_CLEAN_REL

    @staticmethod
    def copy_uni_clean_dir(
        source_dir: Path,
        dest_dir: Path,
        *,
        force: bool = False,
    ) -> list[Path]:
        if not source_dir.is_dir():
            return []
        files = sorted(path for path in source_dir.iterdir() if path.is_file())
        if not files:
            return []
        if dest_dir.exists():
            if not force:
                raise FileExistsError(
                    f"Already exists: {dest_dir} (use --force to overwrite)"
                )
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        copied: list[Path] = []
        for path in files:
            dest = dest_dir / path.name
            shutil.copy2(path, dest)
            copied.append(dest)
        return copied

    def resolve_university_dir(self, university_name: str) -> Path:
        uni_dir = self.repo_root / university_name
        if not uni_dir.is_dir():
            raise FileNotFoundError(f"University folder not found: {uni_dir}")
        return uni_dir

    def package(
        self,
        university_name: str,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> ReviewPackageResult:
        uni_dir = self.resolve_university_dir(university_name)
        variant_csv = self.find_variant_csv(uni_dir)
        reviewed_csv = self.reviewed_csv_path(uni_dir, university_name)

        if not reviewed_csv.is_file():
            raise FileNotFoundError(f"Reviewed CSV not found: {reviewed_csv}")

        review_dir = self.repo_root / REVIEW_DIR_NAME / university_name
        dest_variant = review_dir / variant_csv.name
        dest_reviewed = review_dir / reviewed_csv.name
        dest_report = review_dir / REPORT_TXT_NAME
        source_uni_clean = self.uni_clean_source_dir(uni_dir)
        dest_uni_clean = review_dir / REVIEW_UNI_CLEAN_REL

        stats = MissingFieldStats(self.repo_root)
        report_result = stats.generate(
            university_name,
            force=force,
            dry_run=dry_run,
            reviewed_csv=reviewed_csv,
            report_txt=uni_dir / "output" / REPORT_TXT_NAME,
        )

        copied_uni_files: list[Path] = []
        if not dry_run:
            review_dir.mkdir(parents=True, exist_ok=True)
            for dest in (dest_variant, dest_reviewed, dest_report):
                if dest.exists() and not force:
                    raise FileExistsError(
                        f"Already exists: {dest} (use --force to overwrite)"
                    )
            shutil.copy2(variant_csv, dest_variant)
            shutil.copy2(reviewed_csv, dest_reviewed)
            shutil.copy2(report_result.report_txt, dest_report)
            copied_uni_files = self.copy_uni_clean_dir(
                source_uni_clean,
                dest_uni_clean,
                force=force,
            )
        else:
            dest_variant = review_dir / variant_csv.name
            dest_reviewed = review_dir / reviewed_csv.name
            dest_report = review_dir / REPORT_TXT_NAME
            if source_uni_clean.is_dir():
                copied_uni_files = [
                    dest_uni_clean / path.name
                    for path in sorted(source_uni_clean.iterdir())
                    if path.is_file()
                ]

        return ReviewPackageResult(
            university_name=university_name,
            review_dir=review_dir,
            variant_csv=dest_variant,
            reviewed_csv=dest_reviewed,
            missing_field_report_txt=dest_report,
            uni_clean_files=tuple(copied_uni_files),
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a university's root variant CSV, reviewed dev_courses CSV, "
            f"clean/uni markdown, and missing-field report into {REVIEW_DIR_NAME}/{{University Name}}/"
        )
    )
    parser.add_argument(
        "university_name",
        help='University folder name, e.g. "Anglia Ruskin University - ARU"',
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
        help=f"Overwrite existing files in {REVIEW_DIR_NAME}/{{university}}/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print destination paths without copying",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    builder = ReviewPackageBuilder(args.repo_root)
    try:
        result = builder.package(
            args.university_name,
            force=args.force,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    prefix = "Would write" if args.dry_run else "Wrote"
    print(f"{prefix} {result.variant_csv}")
    print(f"{prefix} {result.reviewed_csv}")
    print(f"{prefix} {result.missing_field_report_txt}")
    for path in result.uni_clean_files:
        print(f"{prefix} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
