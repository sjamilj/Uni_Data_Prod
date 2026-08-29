"""Course page clean configuration from code/.env."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scrape_course_urls import ENV_FILE, load_env_file


@dataclass
class CleanConfig:
    blocks: list[tuple[str | None, str]]
    strip_within: list[str]
    expand_tabs: bool
    title_selector: str | None
    engine: str
    env_path: str


class CleanConfigLoader:
    """Reads COURSE_CLEAN_* settings from .env."""

    @staticmethod
    def parse_selector_list(value: str | None) -> list[str]:
        if not value or not str(value).strip():
            return []
        items: list[str] = []
        for part in re.split(r"[\n;]+", str(value)):
            item = part.strip().strip('"').strip("'")
            if not item:
                continue
            if item.startswith("#") and not re.match(r"#\w", item):
                continue
            items.append(item)
        return items

    @staticmethod
    def parse_clean_block_line(line: str) -> tuple[str | None, str]:
        for sep in ("::", "|"):
            if sep in line:
                heading, selector = line.split(sep, 1)
                heading = heading.strip()
                selector = selector.strip()
                return (heading if heading else None, selector)
        return None, line.strip()

    @classmethod
    def load(cls, work_dir: Path) -> CleanConfig:
        env_path = work_dir / ENV_FILE
        env = load_env_file(env_path)
        blocks_raw = cls.parse_selector_list(env.get("COURSE_CLEAN_BLOCKS"))
        blocks = [cls.parse_clean_block_line(line) for line in blocks_raw]
        expand_raw = (env.get("COURSE_CLEAN_EXPAND_TABS") or "true").strip().lower()
        engine = (env.get("COURSE_CLEAN_ENGINE") or "generic").strip().lower() or "generic"
        return CleanConfig(
            blocks=blocks,
            strip_within=cls.parse_selector_list(env.get("COURSE_CLEAN_STRIP_WITHIN")),
            expand_tabs=expand_raw in ("true", "1", "yes"),
            title_selector=(env.get("COURSE_PAGE_TITLE_SELECTOR") or "").strip() or None,
            engine=engine,
            env_path=str(env_path),
        )
