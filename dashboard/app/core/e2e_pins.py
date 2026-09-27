"""Load per-university pinned E2E course URLs (dashboard/e2e_course_pins.json)."""

from __future__ import annotations

import json
from pathlib import Path


def pins_file_path(repo_root: Path, config: dict | None = None) -> Path:
    name = "e2e_course_pins.json"
    if config and config.get("e2e_course_pins_file"):
        name = str(config["e2e_course_pins_file"]).strip()
    return repo_root / "dashboard" / name


def load_e2e_pins(repo_root: Path, config: dict | None = None) -> dict[str, dict]:
    path = pins_file_path(repo_root, config)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    pins = data.get("pins")
    if not isinstance(pins, dict):
        return {}
    return {str(k): v for k, v in pins.items() if isinstance(v, dict)}


def get_pin_for_folder(repo_root: Path, folder_name: str, config: dict | None = None) -> dict | None:
    pins = load_e2e_pins(repo_root, config)
    return pins.get(folder_name)
