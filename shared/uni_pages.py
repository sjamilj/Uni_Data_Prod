#!/usr/bin/env python3
"""Generic filenames for university-level requirement pages (all universities)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


class UniPageNaming:
    """Constants and helpers for uni_req / clean/uni markdown naming."""

    # --- Output markdown (clean/uni/) — used by llm_extract.py ---
    UNI_MD_BY_ROLE = {
        "entry": "bangladesh-entry.md",
        "english": "english-requirements.md",
        "scholarship": "scholarships.md",
        "deposit": "deposit.md",
    }

    # --- Source HTML (uni_req/) — rename saved pages to these names ---
    UNI_HTML_BY_ROLE = {
        "entry": "bangladesh-entry.html",
        "english": "english-requirements.html",
        "scholarship": "scholarships.html",
        "deposit": "deposit.html",
    }

    UNI_SECTION_TITLES = {
        "english-requirements.md": "English Language Requirements",
        "bangladesh-entry.md": "Bangladesh Entry Requirements",
        "scholarships.md": "Scholarships",
        "deposit.md": "Tuition Fee Deposit",
    }

    # Browser default save titles → generic markdown output name
    HTML_STEM_TO_MD: dict[str, str] = {
        "english language requirements": UNI_MD_BY_ROLE["english"],
        "bangladesh": UNI_MD_BY_ROLE["entry"],
        "south asia scholarship": UNI_MD_BY_ROLE["scholarship"],
        "bangladesh-entry": UNI_MD_BY_ROLE["entry"],
        "english-requirements": UNI_MD_BY_ROLE["english"],
        "scholarships": UNI_MD_BY_ROLE["scholarship"],
        "deposit": UNI_MD_BY_ROLE["deposit"],
    }

    @staticmethod
    def slug_from_stem(stem: str) -> str:
        slug = re.sub(r"[^\w\-]+", "-", stem).strip("-").lower()
        return slug[:160] or "page"

    @classmethod
    def uni_md_output_name(cls, html_stem: str) -> str:
        """Map uni_req HTML stem to generic clean/uni/*.md filename."""
        key = html_stem.lower().strip()
        if key in cls.HTML_STEM_TO_MD:
            return cls.HTML_STEM_TO_MD[key]
        for html_name, md_name in zip(cls.UNI_HTML_BY_ROLE.values(), cls.UNI_MD_BY_ROLE.values()):
            if key == Path(html_name).stem.lower():
                return md_name
        return f"{cls.slug_from_stem(html_stem)}.md"

    @staticmethod
    def course_slug_from_url(url: str) -> str:
        parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
        if "courses" in parts:
            idx = parts.index("courses")
            tail = parts[idx + 1 :]
            if tail:
                slug = re.sub(r"[^\w\-]+", "-", "-".join(tail)).strip("-").lower()
                if slug:
                    return slug[:160]
        path = urlparse(url).path.strip("/")
        slug = re.sub(r"[^\w\-]+", "-", path.replace("/", "-")).strip("-").lower()
        return slug[:160] or "course"


class FrontmatterParser:
    """Parse YAML-style markdown frontmatter."""

    @staticmethod
    def split(text: str) -> tuple[dict[str, str], str]:
        if not text.startswith("---"):
            return {}, text
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text
        meta: dict[str, str] = {}
        for line in parts[1].strip().splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()
        return meta, parts[2].lstrip("\n")


# Backward-compatible module-level aliases
UNI_MD_BY_ROLE = UniPageNaming.UNI_MD_BY_ROLE
UNI_HTML_BY_ROLE = UniPageNaming.UNI_HTML_BY_ROLE
UNI_SECTION_TITLES = UniPageNaming.UNI_SECTION_TITLES
HTML_STEM_TO_MD = UniPageNaming.HTML_STEM_TO_MD
slug_from_stem = UniPageNaming.slug_from_stem
uni_md_output_name = UniPageNaming.uni_md_output_name
course_slug_from_url = UniPageNaming.course_slug_from_url
split_frontmatter = FrontmatterParser.split
