#!/usr/bin/env python3
"""Infer degreeName from clean course markdown and course title via heuristics + LLM."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from llm_extract import infer_degree_name, infer_degree_name_from_md
from validate_dev_courses import DevCoursesValidator

LLM_DEGREE_BATCH_SIZE = 20

SECTION_HEADING_RE = re.compile(r"^##\s+.+$", re.M)
AWARD_LINE_RE = re.compile(r"^\s*-\s*Award\s+(.+)$", re.I | re.M)


def find_course_markdown(output_dir: Path, slug: str) -> Path | None:
    courses_dir = output_dir / "clean" / "courses"
    if not courses_dir.is_dir():
        return None
    matches = sorted(courses_dir.rglob(f"{slug}.md"), key=lambda path: len(path.parts))
    return matches[0] if matches else None


def split_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    if not markdown.startswith("---"):
        return {}, markdown
    end = markdown.find("\n---", 3)
    if end == -1:
        return {}, markdown
    header = markdown[3:end].strip()
    body = markdown[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta, body


def markdown_excerpt_for_degree(md_text: str, *, max_chars: int = 2500) -> str:
    meta, body = split_frontmatter(md_text)
    chunks: list[str] = []
    if meta.get("study_level"):
        chunks.append(f"study_level: {meta['study_level']}")
    if meta.get("course_url"):
        chunks.append(f"course_url: {meta['course_url']}")

    title_match = re.search(r"^#\s+(.+)$", body, re.M)
    if title_match:
        chunks.append(f"title: {title_match.group(1).strip()}")

    for heading in ("Key information", "Course overview", "Entry requirements"):
        match = re.search(
            rf"^##\s+{heading}\s*\n+(.*?)(?=\n## |\Z)",
            body,
            re.S | re.I,
        )
        if match:
            section = match.group(1).strip()
            if section:
                chunks.append(f"## {heading}\n{section}")

    for award in AWARD_LINE_RE.findall(body):
        chunks.append(f"Award: {award.strip()}")

    excerpt = "\n\n".join(chunks).strip()
    if len(excerpt) > max_chars:
        return excerpt[: max_chars - 3].rstrip() + "..."
    return excerpt


def allowed_degree_names() -> list[str]:
    return sorted(DevCoursesValidator.KNOWN_DEGREES, key=str.casefold)


def canonicalize_degree_name(value: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if DevCoursesValidator.known_degree(text):
        if text in DevCoursesValidator.KNOWN_DEGREES:
            return text
        from llm_extract import DEGREE_ALIASES

        folded = text.casefold()
        if folded in DEGREE_ALIASES:
            return DEGREE_ALIASES[folded]
        for alias, canonical in DEGREE_ALIASES.items():
            if canonical.casefold() == folded:
                return canonical
        return text
    return None


def infer_degree_heuristic(
    course_name: str,
    md_text: str,
    *,
    study_level: str = "",
) -> str:
    _, body = split_frontmatter(md_text)
    degree = infer_degree_name_from_md(body or md_text)
    if degree and canonicalize_degree_name(degree):
        return canonicalize_degree_name(degree) or ""

    degree = infer_degree_name(course_name)
    if degree and canonicalize_degree_name(degree):
        return canonicalize_degree_name(degree) or ""

    if (study_level or "").strip().lower() == "postgraduate_research":
        return "PhD"
    return ""


@dataclass(frozen=True)
class DegreeInferenceInput:
    course_name: str
    study_level: str
    md_excerpt: str
    slug: str
    course_dir: Path


class DegreeNameInferrer:
    """Closed-list degreeName inference using markdown context and Ollama."""

    LLM_DEGREE_BATCH_SIZE = LLM_DEGREE_BATCH_SIZE

    @staticmethod
    def build_degree_pick_prompt(items: list[DegreeInferenceInput], allowed: list[str]) -> str:
        allowed_list = "\n".join(f"- {name}" for name in allowed)
        course_blocks: list[str] = []
        for item in items:
            course_blocks.append(
                "\n".join(
                    [
                        f"courseName: {item.course_name}",
                        f"study_level: {item.study_level or 'unknown'}",
                        "markdown:",
                        item.md_excerpt or "(no markdown excerpt available)",
                    ]
                )
            )
        courses = "\n\n---\n\n".join(course_blocks)
        return (
            "Pick exactly one degreeName for each course.\n\n"
            "Rules:\n"
            "- Use ONLY a value from the closed list below.\n"
            "- Do not invent degree codes.\n"
            "- Prefer explicit Award lines or degree tokens in markdown.\n"
            "- postgraduate_research courses are usually PhD unless markdown clearly says MRes.\n"
            "- Foundation routes for undergraduate subjects are usually BSc, BA, BEng, or LLB.\n"
            "- Taught postgraduate courses are usually MSc, MA, MBA, LLM, PGDip, or PGCert.\n"
            "- If unsure, pick the closest standard UK award on the list.\n\n"
            f"Closed degreeName list:\n{allowed_list}\n\n"
            f"Courses:\n{courses}\n\n"
            "Return a JSON object only, with each courseName as a key and one list "
            "degreeName as the value."
        )

    @staticmethod
    def _accepted_llm_matches(
        parsed: object,
        course_names: list[str],
    ) -> dict[str, str]:
        if not isinstance(parsed, dict):
            return {}
        raw_pairs: list[tuple[str, str]] = []
        matches = parsed.get("matches")
        if isinstance(matches, list):
            for item in matches:
                if not isinstance(item, dict):
                    continue
                raw_pairs.append(
                    (str(item.get("courseName") or ""), str(item.get("degreeName") or ""))
                )
        elif isinstance(matches, dict):
            raw_pairs = [
                (str(key), str(value))
                for key, value in matches.items()
                if not isinstance(value, (dict, list))
            ]
        else:
            raw_pairs = [
                (str(key), str(value))
                for key, value in parsed.items()
                if key != "matches" and not isinstance(value, (dict, list))
            ]

        from export_dev_courses import normalize_course_name_key

        by_key = {normalize_course_name_key(name): name for name in course_names}
        accepted: dict[str, str] = {}
        for course_name, degree_name in raw_pairs:
            original = by_key.get(normalize_course_name_key(course_name))
            canonical = canonicalize_degree_name(degree_name)
            if original and canonical:
                accepted[original] = canonical
        return accepted

    def infer_with_llm(
        self,
        items: list[DegreeInferenceInput],
        *,
        batch_size: int = LLM_DEGREE_BATCH_SIZE,
    ) -> dict[str, str]:
        from ollama_client import OllamaError, chat

        allowed = allowed_degree_names()
        pending = [item for item in items if item.course_name.strip()]
        if not pending or not allowed:
            return {}

        accepted: dict[str, str] = {}
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            print(
                f"  LLM degreeName batch {start + 1}-{start + len(batch)} "
                f"of {len(pending)}"
            )
            prompt = self.build_degree_pick_prompt(batch, allowed)
            try:
                parsed, _raw = chat(prompt)
            except OllamaError as exc:
                print(f"LLM degreeName lookup skipped for {len(batch)} course(s): {exc}")
                continue
            accepted.update(
                self._accepted_llm_matches(parsed, [item.course_name for item in batch])
            )
        return accepted


def apply_degree_to_course_dir(course_dir: Path, degree_name: str) -> bool:
    if not degree_name or not course_dir.is_dir():
        return False

    from normalize_admission_data import AdmissionRecordNormalizer

    changed = False
    for name in ("stage1_parsed.json", "output.json", "normalized.json"):
        path = course_dir / name
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        data["degreeName"] = degree_name
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed = True

    output_json = course_dir / "output.json"
    if output_json.is_file():
        raw = json.loads(output_json.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            normalized = AdmissionRecordNormalizer().process_record(raw)
            (course_dir / "normalized.json").write_text(
                json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            changed = True
    return changed


DUPLICATE_LEVEL_SYNC_ORDER = ("undergraduate", "foundation")


def read_degree_name_from_course_dir(course_dir: Path) -> str:
    for name in ("normalized.json", "stage1_parsed.json", "output.json"):
        path = course_dir / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            value = str(data.get("degreeName") or "").strip()
            if value:
                return value
    return ""


def resolve_degree_name_across_levels(output_dir: Path, slug: str) -> str:
    from study_level import extraction_dir

    for level in DUPLICATE_LEVEL_SYNC_ORDER:
        course_dir = extraction_dir(output_dir, slug, level)
        if course_dir.is_dir():
            value = read_degree_name_from_course_dir(course_dir)
            if value:
                return value
    return ""


def apply_degree_to_slug_levels(output_dir: Path, slug: str, degree_name: str) -> bool:
    from study_level import extraction_dir

    changed = False
    for level in DUPLICATE_LEVEL_SYNC_ORDER:
        course_dir = extraction_dir(output_dir, slug, level)
        if course_dir.is_dir():
            changed |= apply_degree_to_course_dir(course_dir, degree_name)
    return changed


def sync_degree_name_for_slug(output_dir: Path, slug: str) -> bool:
    """No-op unless both levels already agree; foundation and undergraduate stay separate."""
    from study_level import extraction_dir

    ug_dir = extraction_dir(output_dir, slug, "undergraduate")
    foundation_dir = extraction_dir(output_dir, slug, "foundation")
    if not ug_dir.is_dir() or not foundation_dir.is_dir():
        return False

    ug_name = read_degree_name_from_course_dir(ug_dir)
    foundation_name = read_degree_name_from_course_dir(foundation_dir)
    if not ug_name or not foundation_name or ug_name != foundation_name:
        return False
    return False


def sync_duplicate_level_degree_names(output_dir: Path) -> int:
    """Sync degreeName across foundation/undergraduate dirs that share the same slug."""
    foundation_root = output_dir / "extracted" / "foundation"
    if not foundation_root.is_dir():
        return 0
    synced = 0
    for course_dir in sorted(foundation_root.iterdir()):
        if course_dir.is_dir() and sync_degree_name_for_slug(output_dir, course_dir.name):
            synced += 1
    return synced
