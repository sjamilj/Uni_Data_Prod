"""Git restore helpers for dashboard (shared baseline + back to main)."""

from __future__ import annotations

import re
from pathlib import Path

_SHARED_TAG = re.compile(r"`(shared/v[\d.]+)`")


def load_shared_baseline_tag(repo_root: Path, config_override: str | None = None) -> str:
    if config_override and str(config_override).strip():
        text = str(config_override).strip()
        if text.startswith("shared/"):
            return text
    path = repo_root / "UNIVERSITIES_REGISTRY.md"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "Current reset baseline" not in line:
                continue
            match = _SHARED_TAG.search(line)
            if match:
                return match.group(1)
    return "shared/v1.2.2"


def git_command(repo_root: Path, *args: str) -> list[str]:
    return ["git", "-C", str(repo_root), *args]


def restore_shared_command(repo_root: Path, tag: str) -> list[str]:
    return git_command(repo_root, "restore", "--worktree", f"--source={tag}", "--", "shared")


_SKIP_TOP_LEVEL = frozenset(
    {
        "shared",
        "dashboard",
        "scripts",
        "docs",
        "_university_template",
        ".git",
        ".cursor",
    }
)


def university_folders_for_restore(repo_root: Path) -> list[str]:
    """All uni folders that checkout-uni may have touched (registry + ENV.MD on disk)."""
    from app.core.uni_registry import load_registry_by_folder

    names: set[str] = set(load_registry_by_folder(repo_root))
    for entry in repo_root.iterdir():
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in _SKIP_TOP_LEVEL:
            continue
        if (entry / "code" / "ENV.MD").is_file():
            names.add(entry.name)
    return sorted(names, key=str.lower)


def collect_head_restore_paths(
    repo_root: Path,
    university_folder: str | None = None,
    *,
    all_universities: bool = False,
) -> list[str]:
    paths: list[str] = ["shared"]
    if all_universities:
        paths.extend(university_folders_for_restore(repo_root))
    elif university_folder:
        paths.append(university_folder)
    return paths


def restore_head_worktree_command(
    repo_root: Path,
    paths: list[str],
    *,
    source: str = "HEAD",
) -> list[str]:
    """Discard staged + unstaged changes and match working tree to source for paths."""
    return git_command(
        repo_root,
        "restore",
        f"--source={source}",
        "--staged",
        "--worktree",
        "--",
        *paths,
    )


def clean_untracked_in_paths_command(repo_root: Path, paths: list[str]) -> list[str]:
    """Remove untracked files and directories under paths (not ignored files)."""
    return git_command(repo_root, "clean", "-fd", "--", *paths)


def switch_main_command(repo_root: Path) -> list[str]:
    return git_command(repo_root, "switch", "main")


def back_to_main_command_chain(
    repo_root: Path,
    university_folder: str | None = None,
    *,
    fetch_origin: bool = False,
    source: str = "HEAD",
    all_universities: bool = True,
) -> list[list[str]]:
    """Commands run in order: optional fetch, switch main, restore worktree from source."""
    steps: list[list[str]] = []
    if fetch_origin:
        steps.append(git_command(repo_root, "fetch", "origin", "main"))
    steps.append(switch_main_command(repo_root))
    paths = collect_head_restore_paths(
        repo_root,
        university_folder,
        all_universities=all_universities,
    )
    steps.append(restore_head_worktree_command(repo_root, paths, source=source))
    steps.append(clean_untracked_in_paths_command(repo_root, paths))
    return steps


# Backward-compatible alias
def restore_main_command(repo_root: Path, university_folder: str | None = None) -> list[str]:
    paths = collect_head_restore_paths(repo_root, university_folder, all_universities=not university_folder)
    return restore_head_worktree_command(repo_root, paths, source="HEAD")
