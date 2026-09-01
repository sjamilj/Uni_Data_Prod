#!/usr/bin/env python3
"""Copy _university_template/ to a new university folder."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

TEMPLATE_DIR_NAME = "_university_template"


class UniversityBootstrapper:
    """Create a new university folder from the shared template."""

    TEMPLATE_DIR_NAME = TEMPLATE_DIR_NAME

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def bootstrap(self, university_name: str, *, force: bool) -> Path:
        template_dir = self.repo_root / self.TEMPLATE_DIR_NAME
        if not template_dir.is_dir():
            raise FileNotFoundError(f"Template not found: {template_dir}")

        target_dir = self.repo_root / university_name
        if target_dir.exists():
            if not force:
                raise FileExistsError(f"Already exists: {target_dir} (use --force to replace)")
            shutil.rmtree(target_dir)

        shutil.copytree(template_dir, target_dir)

        replacements = {
            "{University Name - SHORT}": university_name,
            "{UNIVERSITY_NAME}": university_name,
        }
        for path in target_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".csv", ".html"}:
                continue
            text = path.read_text(encoding="utf-8")
            updated = text
            for old, new in replacements.items():
                updated = updated.replace(old, new)
            if updated != text:
                path.write_text(updated, encoding="utf-8")

        env_md = target_dir / "code" / "ENV.MD"
        env_file = target_dir / "code" / ".env"
        if env_md.is_file() and not env_file.exists():
            env_file.write_text(env_md.read_text(encoding="utf-8"), encoding="utf-8")

        return target_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=f"Create a new university folder from {TEMPLATE_DIR_NAME}/"
    )
    parser.add_argument(
        "university_name",
        help='Folder name, e.g. "Example University - EX" (must match UNIVERSITY_NAME)',
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="F1 repo root (default: parent of shared/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing folder",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = UniversityBootstrapper(args.repo_root).bootstrap(
            args.university_name, force=args.force
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Created {target}")
    print("Next: edit code/.env, save uni_req/ + course_listing/ + course_detail/ HTML")
    return 0


# Backward-compatible module-level aliases
def bootstrap_university(repo_root: Path, university_name: str, *, force: bool) -> Path:
    return UniversityBootstrapper(repo_root).bootstrap(university_name, force=force)

if __name__ == "__main__":
    raise SystemExit(main())
