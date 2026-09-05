"""Per-university Stage 2 LLM content routing (code/.env)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scrape_course_urls import ENV_FILE, load_env_file
from uni_pages import UNI_MD_BY_ROLE

_DEFAULT_UNI_PARTS = ("entry", "english", "scholarship", "deposit")
_DEFAULT_ENTRY_SECTIONS = ("International entry requirements", "Entry requirements")
_DEFAULT_ENGLISH_SECTIONS = ("English language requirements",)


def _env_bool(value: str | None, *, default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _parse_list(value: str | None, *, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value or not str(value).strip():
        return default
    items: list[str] = []
    for part in re.split(r"[\n;,]+", str(value)):
        item = part.strip().strip('"').strip("'")
        if not item:
            continue
        if item.startswith("#") and not re.match(r"#\w", item):
            continue
        items.append(item)
    return tuple(items) if items else default


def extract_markdown_sections(
    body: str,
    headings: tuple[str, ...],
    *,
    heading_levels: tuple[int, ...] = (2, 3),
) -> str:
    """Return concatenated markdown sections for matching headings (h2 and/or h3)."""
    if not body.strip() or not headings:
        return ""
    sections: list[str] = []
    lines = body.splitlines()
    heading_res: list[tuple[re.Pattern[str], int]] = []
    for heading in headings:
        for level in heading_levels:
            hashes = "#" * level
            heading_res.append(
                (
                    re.compile(rf"^{hashes}\s+{re.escape(heading)}\s*$", re.I),
                    level,
                )
            )
    index = 0
    while index < len(lines):
        matched = False
        for heading_re, level in heading_res:
            if heading_re.match(lines[index].strip()):
                matched = True
                block = [lines[index]]
                index += 1
                stop_re = re.compile(r"^#{1," + str(level) + r"}\s+")
                while index < len(lines):
                    if stop_re.match(lines[index]):
                        break
                    block.append(lines[index])
                    index += 1
                sections.append("\n".join(block).strip())
                break
        if not matched:
            index += 1
    return "\n\n".join(section for section in sections if section).strip()


@dataclass(frozen=True)
class LlmStage2Config:
    entry_source: str
    english_source: str
    uni_parts: tuple[str, ...]
    entry_sections: tuple[str, ...]
    english_sections: tuple[str, ...]
    entry_prompt: str
    english_prompt: str
    env_path: str

    @classmethod
    def load(cls, code_dir: Path) -> "LlmStage2Config":
        env_path = code_dir / ENV_FILE
        env = load_env_file(env_path)
        entry_source = (env.get("LLM_STAGE2_ENTRY_SOURCE") or "uni").strip().lower()
        english_source = (env.get("LLM_STAGE2_ENGLISH_SOURCE") or "uni").strip().lower()
        uni_parts = _parse_list(env.get("LLM_STAGE2_UNI_PARTS"), default=_DEFAULT_UNI_PARTS)
        entry_sections = _parse_list(
            env.get("LLM_STAGE2_ENTRY_SECTIONS"),
            default=_DEFAULT_ENTRY_SECTIONS,
        )
        english_sections = _parse_list(
            env.get("LLM_STAGE2_ENGLISH_SECTIONS"),
            default=_DEFAULT_ENGLISH_SECTIONS,
        )
        entry_prompt = (env.get("LLM_STAGE2_ENTRY_PROMPT") or "").strip()
        english_prompt = (env.get("LLM_STAGE2_ENGLISH_PROMPT") or "").strip()
        if not entry_prompt:
            entry_prompt = (
                "prompt_2_entry_course.md"
                if entry_source == "course"
                else "prompt_2_entry.md"
            )
        if not english_prompt:
            english_prompt = (
                "prompt_2_english_course.md"
                if english_source == "course"
                else "prompt_2_english.md"
            )
        return cls(
            entry_source=entry_source,
            english_source=english_source,
            uni_parts=uni_parts,
            entry_sections=entry_sections,
            english_sections=english_sections,
            entry_prompt=entry_prompt,
            english_prompt=english_prompt,
            env_path=str(env_path),
        )

    def entry_content(self, course_body: str, uni_sections: dict[str, str]) -> str:
        if self.entry_source == "course":
            section = extract_markdown_sections(course_body, self.entry_sections)
            if section:
                return f"# Course entry requirements\n\n{section}"
        return uni_sections.get("entry", "")

    def english_content(self, course_body: str, uni_sections: dict[str, str]) -> str:
        if self.english_source == "course":
            section = extract_markdown_sections(course_body, self.english_sections)
            if section:
                return f"# Course English language requirements\n\n{section}"
        return uni_sections.get("english", "")

    def filtered_uni_sections(self, uni_sections: dict[str, str]) -> dict[str, str]:
        return {
            role: uni_sections.get(role, "")
            for role in self.uni_parts
            if role in UNI_MD_BY_ROLE or role in uni_sections
        }

    def uni_content(self, uni_sections: dict[str, str]) -> str:
        parts = [
            content.strip()
            for content in self.filtered_uni_sections(uni_sections).values()
            if content.strip()
        ]
        return "\n\n---\n\n".join(parts)
