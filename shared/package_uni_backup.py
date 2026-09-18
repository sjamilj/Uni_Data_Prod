#!/usr/bin/env python3
"""Copy pipeline handoff artifacts for completed universities into a backup tree.

Default root is ``.../DATA SCOL/BACKUP`` (sibling of ``UK_Uni_Data``, not inside the repo).
Override with ``--backup-root`` or env ``UK_UNI_BACKUP_ROOT``.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED.parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from build_university_from_template import VARIANT_FILES  # noqa: E402

BACKUP_ENV_VAR = "UK_UNI_BACKUP_ROOT"

OUTPUT_URL_CSVS = (
    "course_urls.csv",
    "failed_urls.csv",
    "foundation_course_urls.csv",
    "undergraduate_course_urls.csv",
    "postgraduate_course_urls.csv",
    "postgraduate_research_course_urls.csv",
    "other_course_urls.csv",
)

OPTIONAL_ROOT_DIRS = ("course_listing", "course_detail")

_COPYTREE_IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".device-profile-edge",
    ".device-profile-*",
    ".playwright-profile",
)


def resolve_backup_root(repo_root: Path, override: str | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get(BACKUP_ENV_VAR, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    # Standard layout: .../DATA SCOL/UK_Uni_Data -> .../DATA SCOL/BACKUP
    return (repo_root.parent / "BACKUP").resolve()


def university_folders_from_registry(repo_root: Path) -> list[str]:
    """Folder names from UNIVERSITIES_REGISTRY.md (unit/slug table rows)."""
    registry = repo_root / "UNIVERSITIES_REGISTRY.md"
    if not registry.is_file():
        raise FileNotFoundError(f"Registry not found: {registry}")
    folders: list[str] = []
    row_re = re.compile(
        r"^\|\s*unit-\d{2}\s*\|\s*[a-z0-9-]+\s*\|\s*([^|]+?)\s*\|\s*\w+\s*\|",
        re.I,
    )
    for line in registry.read_text(encoding="utf-8").splitlines():
        match = row_re.match(line.strip())
        if match:
            folders.append(match.group(1).strip())
    if not folders:
        raise ValueError(f"No university rows parsed from {registry}")
    return folders


def copy_if_exists(src: Path, dest: Path) -> bool:
    if not src.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=_COPYTREE_IGNORE)
    else:
        shutil.copy2(src, dest)
    return True


def package_university(
    repo_root: Path,
    university_name: str,
    *,
    backup_root_parent: Path,
    force: bool = False,
) -> list[str]:
    uni_dir = repo_root / university_name
    if not uni_dir.is_dir():
        raise FileNotFoundError(f"University folder not found: {uni_dir}")

    backup_root = backup_root_parent / university_name
    if backup_root.exists() and not force:
        raise FileExistsError(f"Already exists: {backup_root} (use --force)")
    if backup_root.exists() and force:
        shutil.rmtree(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    def record(rel: str) -> None:
        copied.append(rel)

    # code/, uni_req/, course_listing/, course_detail/
    for name in ("code", "uni_req", *OPTIONAL_ROOT_DIRS):
        src = uni_dir / name
        if copy_if_exists(src, backup_root / name):
            record(name + ("/" if src.is_dir() else ""))

    # Root variant + portal CSV
    for variant in sorted(VARIANT_FILES):
        if copy_if_exists(uni_dir / variant, backup_root / variant):
            record(variant)
    for portal in sorted(uni_dir.glob("*_portal.csv")):
        rel = portal.name
        if copy_if_exists(portal, backup_root / rel):
            record(rel)

    out = uni_dir / "output"
    if out.is_dir():
        if copy_if_exists(out / "clean", backup_root / "output" / "clean"):
            record("output/clean/")
        for name in OUTPUT_URL_CSVS:
            if copy_if_exists(out / name, backup_root / "output" / name):
                record(f"output/{name}")
        for reviewed in sorted(out.glob("dev_courses_*_reviewed.csv")):
            rel = f"output/{reviewed.name}"
            if copy_if_exists(reviewed, backup_root / "output" / reviewed.name):
                record(rel)

    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Copy completed-university artifacts to UK_UNI_BACKUP_ROOT (see --backup-root)",
    )
    parser.add_argument(
        "universities",
        nargs="*",
        metavar="UNIVERSITY",
        help='University folder name(s), e.g. "University of Derby"',
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Backup every university listed in UNIVERSITIES_REGISTRY.md",
    )
    parser.add_argument(
        "--backup-root",
        metavar="DIR",
        help=f"Backup parent directory (default: env {BACKUP_ENV_VAR} or DATA SCOL/BACKUP)",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing {backup-root}/{university}/")
    args = parser.parse_args(argv)

    backup_parent = resolve_backup_root(_REPO_ROOT, args.backup_root)
    if args.all and args.universities:
        parser.error("Use either positional UNIVERSITY name(s) or --all, not both")
    if args.all:
        names = university_folders_from_registry(_REPO_ROOT)
    elif args.universities:
        names = list(args.universities)
    else:
        parser.error('Provide UNIVERSITY folder name(s) or --all (see UNIVERSITIES_REGISTRY.md)')
    print(f"Backup root: {backup_parent}")
    for name in names:
        try:
            copied = package_university(
                _REPO_ROOT,
                name,
                backup_root_parent=backup_parent,
                force=args.force,
            )
        except (FileNotFoundError, FileExistsError) as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"{name}: {len(copied)} item(s) -> {backup_parent / name}")
        for rel in copied:
            print(f"  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
