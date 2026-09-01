#!/usr/bin/env python3
"""Copy a university's root variant CSV and reviewed dev_courses CSV into REVIEW/."""

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

REVIEW_DIR_NAME = "REVIEW"


@dataclass(frozen=True)
class ReviewPackageResult:
    university_name: str
    review_dir: Path
    variant_csv: Path
    reviewed_csv: Path


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

        if not dry_run:
            review_dir.mkdir(parents=True, exist_ok=True)
            for dest in (dest_variant, dest_reviewed):
                if dest.exists() and not force:
                    raise FileExistsError(
                        f"Already exists: {dest} (use --force to overwrite)"
                    )
            shutil.copy2(variant_csv, dest_variant)
            shutil.copy2(reviewed_csv, dest_reviewed)
        else:
            dest_variant = review_dir / variant_csv.name
            dest_reviewed = review_dir / reviewed_csv.name

        return ReviewPackageResult(
            university_name=university_name,
            review_dir=review_dir,
            variant_csv=dest_variant,
            reviewed_csv=dest_reviewed,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a university's root variant CSV and reviewed dev_courses CSV "
            f"into {REVIEW_DIR_NAME}/{{University Name}}/"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
