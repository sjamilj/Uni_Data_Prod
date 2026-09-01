#!/usr/bin/env python3
"""Build and load the courseName → programmeName dictionary.

UK Course.csv is treated as fixed. University-specific programmeName comes from
each uni's *_portal.csv during export. This file is a single general map.

Run this script once (or after UK Course.csv changes) to write
programmeName_dictionary.json. Validate loads that JSON.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from export_dev_courses import normalize_course_name_key

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UK_COURSE_CSV = REPO_ROOT / "UK Course.csv"
DEFAULT_DICTIONARY_JSON = REPO_ROOT / "programmeName_dictionary.json"

AWARD_SUFFIX_RE = re.compile(
    r"\s*[-–—]\s*"
    r"(bsc|ba|beng|llb|msc|ma|mba|mfa|phd|mres|msci|barch|march|bmus|"
    r"pgdip|hnd|advpgdip|fdsc|fda|fd|mph)\b.*$",
    re.I,
)
FOUNDATION_SUFFIX_RE = re.compile(
    r"\s+(with a foundation year|with foundation year|foundation year)\b",
    re.I,
)
HONS_TAIL_RE = re.compile(r"\s*\((hons|hons\.)\)\s*$", re.I)

LLM_PROGRAMME_BATCH_SIZE = 20


def course_name_lookup_keys(name: str) -> list[str]:
    """Normalized courseName, then award/foundation stem if different."""
    keys: list[str] = []
    exact = normalize_course_name_key(name)
    if exact:
        keys.append(exact)
    stem = FOUNDATION_SUFFIX_RE.sub("", exact)
    stem = AWARD_SUFFIX_RE.sub("", stem)
    stem = HONS_TAIL_RE.sub("", stem).strip(" -")
    if stem and stem not in keys:
        keys.append(stem)
    return keys


class ProgrammeNameDictionary:
    """General courseName → programmeName map (not split by university)."""

    DEFAULT_UK_COURSE_CSV = DEFAULT_UK_COURSE_CSV
    DEFAULT_DICTIONARY_JSON = DEFAULT_DICTIONARY_JSON
    LLM_PROGRAMME_BATCH_SIZE = LLM_PROGRAMME_BATCH_SIZE

    def __init__(self) -> None:
        self.pairs: dict[str, str] = {}
        self.path: Path | None = None
        self.row_count = 0

    def lookup(self, course_name: str) -> str | None:
        for key in course_name_lookup_keys(course_name):
            value = self.pairs.get(key)
            if value:
                return value
        return None

    def unique_programme_names(self) -> list[str]:
        return sorted(set(self.pairs.values()), key=str.casefold)

    def canonicalize(self, programme_name: str) -> str | None:
        folded = (programme_name or "").strip().casefold()
        if not folded:
            return None
        for name in set(self.pairs.values()):
            if name.casefold() == folded:
                return name
        return None

    @classmethod
    def build_from_uk_course_csv(cls, csv_path: Path | None = None) -> ProgrammeNameDictionary:
        mapping = cls()
        source = csv_path or cls.DEFAULT_UK_COURSE_CSV
        if not source.is_file():
            return mapping

        candidates: dict[str, set[str]] = {}
        with source.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                programme = (row.get("programmeName") or "").strip()
                course_name = row.get("courseName") or ""
                if not programme or not course_name.strip():
                    continue
                mapping.row_count += 1
                for key in course_name_lookup_keys(course_name):
                    candidates.setdefault(key, set()).add(programme)

        mapping.path = source
        mapping.pairs = {
            key: next(iter(values)) for key, values in candidates.items() if len(values) == 1
        }
        return mapping

    def save(self, json_path: Path | None = None) -> Path:
        path = json_path or self.DEFAULT_DICTIONARY_JSON
        path.write_text(
            json.dumps(self.pairs, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.path = path
        return path

    @classmethod
    def load_json(cls, json_path: Path | None = None) -> ProgrammeNameDictionary:
        path = json_path or cls.DEFAULT_DICTIONARY_JSON
        payload = json.loads(path.read_text(encoding="utf-8"))
        mapping = cls()
        mapping.path = path
        if isinstance(payload, dict) and isinstance(payload.get("global"), dict):
            payload = payload["global"]
        if not isinstance(payload, dict):
            raise ValueError(f"{path}: expected a JSON object of courseName → programmeName")
        mapping.pairs = {
            str(key): str(value)
            for key, value in payload.items()
            if not isinstance(value, dict)
        }
        mapping.row_count = len(mapping.pairs)
        return mapping

    @classmethod
    def load(
        cls,
        json_path: Path | None = None,
        *,
        csv_path: Path | None = None,
    ) -> ProgrammeNameDictionary:
        """Load programmeName_dictionary.json. Build it from UK Course.csv if missing."""
        path = json_path or cls.DEFAULT_DICTIONARY_JSON
        if path.is_file():
            return cls.load_json(path)
        mapping = cls.build_from_uk_course_csv(csv_path)
        if mapping.pairs:
            mapping.save(path)
        return mapping

    @staticmethod
    def build_programme_pick_prompt(course_names: list[str], allowed: list[str]) -> str:
        listed = "\n".join(f"- {name}" for name in allowed)
        courses = "\n".join(f"- {name}" for name in course_names)
        return (
            "Pick exactly one programmeName for each courseName.\n\n"
            "Rules:\n"
            "- Use ONLY a value from the closed list below.\n"
            "- Do not invent names.\n"
            "- Do not copy the course title unless it equals a list value.\n"
            "- If unsure, pick the closest subject on the list.\n\n"
            f"Closed programmeName list:\n{listed}\n\n"
            f"courseName values:\n{courses}\n\n"
            'Return a JSON object only, with each courseName as a key and one '
            "list programmeName as the value."
        )

    @staticmethod
    def _accepted_llm_matches(
        parsed: object,
        course_names: list[str],
        dictionary: ProgrammeNameDictionary,
    ) -> dict[str, str]:
        if not isinstance(parsed, dict):
            return {}
        matches = parsed.get("matches")
        raw_pairs: list[tuple[str, str]] = []
        if isinstance(matches, list):
            for item in matches:
                if not isinstance(item, dict):
                    continue
                raw_pairs.append(
                    (str(item.get("courseName") or ""), str(item.get("programmeName") or ""))
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

        by_key = {normalize_course_name_key(name): name for name in course_names}
        accepted: dict[str, str] = {}
        for course_name, programme_name in raw_pairs:
            original = by_key.get(normalize_course_name_key(course_name))
            canonical = dictionary.canonicalize(programme_name)
            if original and canonical:
                accepted[original] = canonical
        return accepted

    def infer_with_llm(
        self,
        course_names: list[str],
        *,
        batch_size: int = LLM_PROGRAMME_BATCH_SIZE,
    ) -> dict[str, str]:
        """Map leftover courseNames to a closed programmeName via Ollama."""
        from ollama_client import OllamaError, chat

        allowed = self.unique_programme_names()
        unique_names = list(dict.fromkeys(name for name in course_names if name.strip()))
        if not unique_names or not allowed:
            return {}

        accepted: dict[str, str] = {}
        for start in range(0, len(unique_names), batch_size):
            batch = unique_names[start : start + batch_size]
            print(
                f"  LLM programmeName batch {start + 1}-{start + len(batch)} "
                f"of {len(unique_names)}"
            )
            prompt = self.build_programme_pick_prompt(batch, allowed)
            try:
                parsed, _raw = chat(prompt)
            except OllamaError as exc:
                print(f"LLM programmeName lookup skipped for {len(batch)} course(s): {exc}")
                continue
            accepted.update(self._accepted_llm_matches(parsed, batch, self))
        return accepted


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build programmeName_dictionary.json from UK Course.csv."
    )
    parser.add_argument(
        "--uk-course",
        type=Path,
        default=DEFAULT_UK_COURSE_CSV,
        help="Master UK Course.csv (default: repo-root UK Course.csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DICTIONARY_JSON,
        help="Dictionary JSON path (default: repo-root programmeName_dictionary.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.uk_course.is_file():
        print(f"UK Course.csv not found: {args.uk_course}", file=sys.stderr)
        return 1
    mapping = ProgrammeNameDictionary.build_from_uk_course_csv(args.uk_course)
    path = mapping.save(args.output)
    print(
        f"Wrote {path} ({len(mapping.pairs)} unique courseName keys "
        f"from {mapping.row_count} UK Course.csv rows)"
    )
    return 0


# Backward-compatible module-level aliases
build_from_uk_course_csv = ProgrammeNameDictionary.build_from_uk_course_csv
load_dictionary_json = ProgrammeNameDictionary.load_json
load_programme_name_dictionary = ProgrammeNameDictionary.load
build_programme_pick_prompt = ProgrammeNameDictionary.build_programme_pick_prompt
infer_programme_names_with_llm = ProgrammeNameDictionary().infer_with_llm


def save_dictionary(mapping: ProgrammeNameDictionary, json_path: Path | None = None) -> Path:
    return mapping.save(json_path)


if __name__ == "__main__":
    raise SystemExit(main())
