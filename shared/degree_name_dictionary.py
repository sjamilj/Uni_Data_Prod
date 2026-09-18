#!/usr/bin/env python3
"""Build and load courseName + studyLevel → degreeName dictionary.

UK Course.csv is the source of truth (study level inferred from courseUrlExternal).
Portal CSVs mirror the same columns during export. Rebuild after UK Course.csv changes.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from programme_name_dictionary import course_name_lookup_keys
from study_level import STUDY_LEVELS, StudyLevelClassifier, folder_for_level

DICTIONARY_VERSION = 2


def canonicalize_degree_name(value: str) -> str | None:
    """Avoid importing degree_name_inference (circular via validate_dev_courses)."""
    from llm_extract import DEGREE_ALIASES

    text = (value or "").strip()
    if not text:
        return None
    folded = text.casefold()
    if folded in DEGREE_ALIASES:
        return DEGREE_ALIASES[folded]
    for alias, canonical in DEGREE_ALIASES.items():
        if canonical.casefold() == folded:
            return canonical
    from validate_dev_courses import DevCoursesValidator

    if DevCoursesValidator.known_degree(text):
        if text in DevCoursesValidator.KNOWN_DEGREES:
            return text
        return text
    return None


def normalize_study_level(value: str) -> str:
    level = folder_for_level((value or "").strip().lower().replace("-", "_"))
    if level in STUDY_LEVELS:
        return level
    return "undergraduate"


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UK_COURSE_CSV = REPO_ROOT / "UK Course.csv"
DEFAULT_DICTIONARY_JSON = REPO_ROOT / "degreeName_dictionary.json"


class DegreeNameDictionary:
    """courseName (+ studyLevel) → degreeName map from UK Course.csv."""

    DEFAULT_UK_COURSE_CSV = DEFAULT_UK_COURSE_CSV
    DEFAULT_DICTIONARY_JSON = DEFAULT_DICTIONARY_JSON

    def __init__(self) -> None:
        self.by_study_level: dict[str, dict[str, str]] = {
            level: {} for level in STUDY_LEVELS if level != "other"
        }
        self.global_pairs: dict[str, str] = {}
        self.path: Path | None = None
        self.row_count = 0
        self.skipped_ambiguous = 0

    @property
    def pairs(self) -> dict[str, str]:
        """Flat view (all level-specific entries; keys are not level-qualified)."""
        merged: dict[str, str] = dict(self.global_pairs)
        for level_map in self.by_study_level.values():
            merged.update(level_map)
        return merged

    def lookup(self, course_name: str, *, study_level: str = "") -> str | None:
        level = normalize_study_level(study_level) if study_level else ""
        keys = course_name_lookup_keys(course_name)
        if level:
            level_map = self.by_study_level.get(level, {})
            for key in keys:
                value = level_map.get(key)
                if value:
                    return value
        for key in keys:
            value = self.global_pairs.get(key)
            if value:
                return value
        if not level:
            for level_map in self.by_study_level.values():
                for key in keys:
                    value = level_map.get(key)
                    if value:
                        return value
        return None

    def unique_degree_names(self) -> list[str]:
        values: set[str] = set(self.global_pairs.values())
        for level_map in self.by_study_level.values():
            values.update(level_map.values())
        return sorted(values, key=str.casefold)

    def canonicalize(self, degree_name: str) -> str | None:
        return canonicalize_degree_name(degree_name)

    @classmethod
    def build_from_uk_course_csv(cls, csv_path: Path | None = None) -> DegreeNameDictionary:
        mapping = cls()
        source = csv_path or cls.DEFAULT_UK_COURSE_CSV
        if not source.is_file():
            return mapping

        classifier = StudyLevelClassifier()
        per_level_candidates: dict[str, dict[str, set[str]]] = {
            level: {} for level in mapping.by_study_level
        }
        global_candidates: dict[str, set[str]] = {}

        with source.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                degree_raw = (row.get("degreeName") or "").strip()
                degree = canonicalize_degree_name(degree_raw) or degree_raw
                course_name = row.get("courseName") or ""
                url = (row.get("courseUrlExternal") or "").strip()
                if not degree or not course_name.strip():
                    continue
                study_level = classifier.classify(url, course_name=course_name)
                if study_level == "other":
                    study_level = "undergraduate"
                mapping.row_count += 1
                lookup_keys = course_name_lookup_keys(course_name)
                if study_level in per_level_candidates:
                    for key in lookup_keys:
                        per_level_candidates[study_level].setdefault(key, set()).add(degree)
                for key in lookup_keys:
                    global_candidates.setdefault(key, set()).add(degree)

        ambiguous = 0
        for level, candidates in per_level_candidates.items():
            level_map: dict[str, str] = {}
            for key, values in candidates.items():
                if len(values) == 1:
                    level_map[key] = next(iter(values))
                else:
                    ambiguous += 1
            mapping.by_study_level[level] = level_map

        mapping.skipped_ambiguous = ambiguous
        mapping.global_pairs = {
            key: next(iter(values))
            for key, values in global_candidates.items()
            if len(values) == 1
        }
        mapping.path = source
        return mapping

    def save(self, json_path: Path | None = None) -> Path:
        path = json_path or self.DEFAULT_DICTIONARY_JSON
        payload = {
            "version": DICTIONARY_VERSION,
            "byStudyLevel": self.by_study_level,
            "global": self.global_pairs,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.path = path
        return path

    @classmethod
    def load_json(cls, json_path: Path | None = None) -> DegreeNameDictionary:
        path = json_path or cls.DEFAULT_DICTIONARY_JSON
        payload = json.loads(path.read_text(encoding="utf-8"))
        mapping = cls()
        mapping.path = path

        if isinstance(payload, dict) and payload.get("version") == DICTIONARY_VERSION:
            by_level = payload.get("byStudyLevel") or {}
            if isinstance(by_level, dict):
                for level in mapping.by_study_level:
                    raw = by_level.get(level)
                    if isinstance(raw, dict):
                        mapping.by_study_level[level] = {
                            str(k): str(v) for k, v in raw.items() if not isinstance(v, dict)
                        }
            global_raw = payload.get("global")
            if isinstance(global_raw, dict):
                mapping.global_pairs = {
                    str(k): str(v) for k, v in global_raw.items() if not isinstance(v, dict)
                }
            mapping.row_count = sum(len(m) for m in mapping.by_study_level.values()) + len(
                mapping.global_pairs
            )
            return mapping

        if isinstance(payload, dict) and isinstance(payload.get("global"), dict):
            payload = payload["global"]
        if isinstance(payload, dict):
            mapping.global_pairs = {
                str(key): str(value)
                for key, value in payload.items()
                if not isinstance(value, dict)
            }
            mapping.row_count = len(mapping.global_pairs)
        else:
            raise ValueError(f"{path}: expected degreeName dictionary JSON object")
        return mapping

    @classmethod
    def load(
        cls,
        json_path: Path | None = None,
        *,
        csv_path: Path | None = None,
    ) -> DegreeNameDictionary:
        path = json_path or cls.DEFAULT_DICTIONARY_JSON
        if path.is_file():
            return cls.load_json(path)
        mapping = cls.build_from_uk_course_csv(csv_path)
        if mapping.pairs:
            mapping.save(path)
        return mapping


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build degreeName_dictionary.json from UK Course.csv."
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
        help="Dictionary JSON path (default: repo-root degreeName_dictionary.json)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.uk_course.is_file():
        print(f"UK Course.csv not found: {args.uk_course}", file=sys.stderr)
        return 1
    mapping = DegreeNameDictionary.build_from_uk_course_csv(args.uk_course)
    path = mapping.save(args.output)
    unique_degrees = len(mapping.unique_degree_names())
    level_counts = ", ".join(
        f"{level}={len(mapping.by_study_level.get(level, {}))}"
        for level in STUDY_LEVELS
        if level != "other"
    )
    print(
        f"Wrote {path} (v{DICTIONARY_VERSION}; byStudyLevel: {level_counts}; "
        f"global={len(mapping.global_pairs)}; {unique_degrees} distinct degreeName; "
        f"{mapping.skipped_ambiguous} ambiguous level+title keys skipped; "
        f"from {mapping.row_count} UK Course.csv rows)"
    )
    return 0


build_from_uk_course_csv = DegreeNameDictionary.build_from_uk_course_csv
load_degree_name_dictionary_json = DegreeNameDictionary.load_json
load_degree_name_dictionary = DegreeNameDictionary.load


if __name__ == "__main__":
    raise SystemExit(main())
