"""Read unit / commit pins from UNIVERSITIES_REGISTRY.md (same rows as checkout-uni.ps1)."""

from __future__ import annotations

import re
from pathlib import Path

_REGISTRY_ROW = re.compile(
    r"^\|\s*(unit-\d{2})\s*\|\s*([a-z0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*(\w+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
)

_SKIP_CHECKOUT_SLUGS = frozenset({"aru", "aston"})


def _normalize_commit(raw: str) -> str:
    text = raw.strip().strip("`").strip()
    if text in ("", "—", "-", "–"):
        return ""
    return text


def load_registry_by_folder(repo_root: Path) -> dict[str, dict[str, str]]:
    path = repo_root / "UNIVERSITIES_REGISTRY.md"
    if not path.is_file():
        return {}
    by_folder: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = _REGISTRY_ROW.match(line)
        if not match:
            continue
        unit, slug, folder, status, _tag, commit = (part.strip() for part in match.groups())
        by_folder[folder] = {
            "unit": unit,
            "slug": slug,
            "status": status,
            "commit": _normalize_commit(commit),
        }
    return by_folder


def should_run_registry_checkout(meta: dict[str, str] | None) -> bool:
    if not meta:
        return False
    if meta.get("slug") in _SKIP_CHECKOUT_SLUGS:
        return False
    return bool(meta.get("commit"))


def checkout_command(repo_root: Path, unit: str, commit: str) -> list[str]:
    script = repo_root / "scripts" / "checkout-uni.cmd"
    return [
        "cmd",
        "/c",
        str(script),
        "-Pick",
        unit,
        "-Commit",
        commit,
        "-IncludeShared",
    ]
