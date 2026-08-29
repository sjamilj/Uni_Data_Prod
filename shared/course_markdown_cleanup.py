"""Shared course markdown post-processing.

Generic engine in shared/:
  - COURSE_MARKDOWN_REMOVE_SECTIONS from code/.env (heading removal)
  - uni_req JSON formatting and UNI_REQ_SOURCE_URLS

University-specific conditional rules live in {University}/code/course_markdown_cleanup.py
(cleanup_course_markdown_uni).

Run from university code/:

  python "../../shared/course_markdown_cleanup.py" .
  python course_markdown_cleanup.py .
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType

from uni_paths import resolve_code_dir, resolve_output_dir

_ENV_FILE_NAME = ".env"
_UNI_REQ_SOURCE_URLS_KEY = "UNI_REQ_SOURCE_URLS"
_COURSE_MARKDOWN_REMOVE_SECTIONS_KEY = "COURSE_MARKDOWN_REMOVE_SECTIONS"

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _parse_heading(line: str) -> tuple[int, str] | None:
    match = _HEADING_RE.match(line)
    if not match:
        return None
    return len(match.group(1)), match.group(2).strip()


def _normalize_blank_lines(markdown: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", markdown.strip())


def _heading_matches_pattern(actual: str, pattern: str) -> bool:
    """Match a heading: exact, `prefix*`, `*contains*`, or `*suffix`."""
    actual_l = actual.strip().lower()
    pattern_l = pattern.strip().lower()
    if not pattern_l:
        return False
    if pattern_l.startswith("*") and pattern_l.endswith("*") and len(pattern_l) > 1:
        needle = pattern_l[1:-1]
        return bool(needle) and needle in actual_l
    if pattern_l.endswith("*"):
        return actual_l.startswith(pattern_l[:-1])
    if pattern_l.startswith("*"):
        return actual_l.endswith(pattern_l[1:])
    return actual_l == pattern_l


def remove_markdown_heading_section(
    markdown: str,
    *,
    heading: str,
    level: int,
    until_level: int | None = None,
) -> str:
    """Drop one section that starts at a matching heading until the next stop heading."""
    stop_level = level if until_level is None else until_level
    lines = markdown.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        parsed = _parse_heading(line)
        if parsed and parsed[0] == level and _heading_matches_pattern(parsed[1], heading):
            index += 1
            while index < len(lines):
                next_heading = _parse_heading(lines[index])
                if next_heading and next_heading[0] <= stop_level:
                    break
                index += 1
            continue
        kept.append(line)
        index += 1
    return "\n".join(kept)


def _parse_remove_section_line(line: str) -> tuple[int, str, int | None] | None:
    """Parse 'level :: heading' or 'level :: heading :: until_level'."""
    for sep in ("::", "|"):
        if sep in line:
            parts = [part.strip() for part in line.split(sep)]
            break
    else:
        return None
    if len(parts) < 2:
        return None
    try:
        level = int(parts[0])
    except ValueError:
        return None
    heading = parts[1]
    if not heading:
        return None
    until_level: int | None = None
    if len(parts) >= 3 and parts[2].isdigit():
        until_level = int(parts[2])
    return level, heading, until_level


def apply_env_remove_sections_for_key(
    markdown: str,
    code_dir: Path,
    env_key: str,
) -> str:
    """Remove markdown sections listed under a named .env key."""
    env = _load_env(resolve_code_dir(code_dir))
    cleaned = markdown
    for line in _parse_env_list(env.get(env_key)):
        parsed = _parse_remove_section_line(line)
        if not parsed:
            continue
        level, heading, until_level = parsed
        stop_level = until_level if until_level is not None else level
        while True:
            next_cleaned = remove_markdown_heading_section(
                cleaned,
                heading=heading,
                level=level,
                until_level=stop_level,
            )
            if next_cleaned == cleaned:
                break
            cleaned = next_cleaned
    return _normalize_blank_lines(cleaned)


def apply_env_remove_sections(markdown: str, code_dir: Path) -> str:
    """Remove markdown sections listed in COURSE_MARKDOWN_REMOVE_SECTIONS (.env)."""
    return apply_env_remove_sections_for_key(
        markdown,
        code_dir,
        _COURSE_MARKDOWN_REMOVE_SECTIONS_KEY,
    )


class _EnvFile:
    """Minimal .env loader (quoted multiline values) without scrape_course_urls deps."""

    def __init__(self, path: Path):
        self.values = self._load(path)

    def _load(self, path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        if not path.is_file():
            return values
        lines = path.read_text(encoding="utf-8").splitlines()
        index = 0
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()
            index += 1
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
                value = value[1:-1]
            elif value.startswith('"') or value.startswith("'"):
                quote = value[0]
                chunks = [value[1:]]
                while index < len(lines):
                    next_line = lines[index]
                    index += 1
                    if next_line.rstrip().endswith(quote):
                        chunks.append(next_line.rstrip()[:-1])
                        break
                    chunks.append(next_line)
                value = "\n".join(chunks)
            values[key] = value
        return values


def _load_env(code_dir: Path) -> dict[str, str]:
    return _EnvFile(code_dir / _ENV_FILE_NAME).values


def _parse_env_list(value: str | None) -> list[str]:
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


def _parse_stem_url_line(line: str) -> tuple[str, str] | None:
    for sep in ("::", "|"):
        if sep in line:
            stem, url = line.split(sep, 1)
            stem = stem.strip()
            url = url.strip()
            if stem and url:
                return stem, url
    return None


def uni_source_urls_from_env(code_dir: Path) -> dict[str, str]:
    """Load uni_req canonical URLs from code/.env (html_stem → source URL)."""
    env = _load_env(resolve_code_dir(code_dir))
    urls: dict[str, str] = {}
    for line in _parse_env_list(env.get(_UNI_REQ_SOURCE_URLS_KEY)):
        parsed = _parse_stem_url_line(line)
        if parsed:
            urls[parsed[0]] = parsed[1]
    for stem, key in (
        ("bangladesh-entry", "UNI_SOURCE_URL_BANGLADESH_ENTRY"),
        ("english-requirements", "UNI_SOURCE_URL_ENGLISH_REQUIREMENTS"),
        ("scholarships", "UNI_SOURCE_URL_SCHOLARSHIPS"),
        ("deposit", "UNI_SOURCE_URL_DEPOSIT"),
    ):
        value = (env.get(key) or "").strip()
        if value and stem not in urls:
            urls[stem] = value
    return urls


def _load_uni_course_cleanup_module(code_dir: Path) -> ModuleType | None:
    """Load {University}/code/course_markdown_cleanup.py when present."""
    path = resolve_code_dir(code_dir) / "course_markdown_cleanup.py"
    if not path.is_file():
        return None
    module_name = f"uni_course_markdown_cleanup_{abs(hash(path.resolve()))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    uni_code = str(path.parent)
    if uni_code not in sys.path:
        sys.path.insert(0, uni_code)
    spec.loader.exec_module(module)
    return module


def cleanup_course_markdown(markdown: str, *, code_dir: Path | None = None) -> str:
    """Apply .env section removal, then optional per-university cleanup_course_markdown_uni."""
    if code_dir is None:
        return markdown
    cleaned = apply_env_remove_sections(markdown, code_dir)
    module = _load_uni_course_cleanup_module(code_dir)
    if module is None:
        return cleaned
    extra = getattr(module, "cleanup_course_markdown_uni", None)
    if callable(extra):
        return extra(cleaned)
    return cleaned


_SCHOLARSHIP_FIELD_LABELS = (
    ("scholarshipType", "Type"),
    ("scholarshipStudyLevel", "Study level"),
    ("Eligibility", "Eligibility"),
    ("Amount", "Amount"),
    ("description", "Description"),
)

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)


def _strip_source_markdown(text: str) -> str:
    stripped = text.strip()
    stripped = _FRONTMATTER_RE.sub("", stripped, count=1).strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", stripped, re.S | re.I)
    if fence:
        return fence.group(1).strip()
    lines: list[str] = []
    for line in stripped.splitlines():
        item = line.strip()
        if item.startswith("#"):
            continue
        if item.lower().startswith("source file:"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


_UNI_JSON_TITLES = {
    "bangladesh-entry": "Bangladesh Entry Requirements",
    "english-requirements": "English Language Requirements",
    "scholarships": "Scholarships",
    "deposit": "Tuition Fee Deposit",
}


def format_json_as_markdown(data: object, *, title: str) -> str:
    """Render curated uni_req JSON as markdown with a fenced JSON block."""
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    return f"# {title}\n\n```json\n{payload}\n```\n"


def _try_parse_json(text: str) -> object | None:
    payload = _strip_source_markdown(text)
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


def _try_parse_scholarships_json(text: str) -> list[dict] | None:
    data = _try_parse_json(text)
    if not isinstance(data, list) or not data:
        return None
    if not all(isinstance(item, dict) for item in data):
        return None
    return data


def _try_parse_bangladesh_entry_json(text: str) -> dict | None:
    data = _try_parse_json(text)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("studyLevels"), list):
        return None
    return data


def _try_parse_deposit_json(text: str) -> dict | None:
    payload = _strip_source_markdown(text)
    if not payload:
        return None
    if not payload.startswith("{"):
        payload = "{" + payload.rstrip(",") + "}"
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if "initialDeposit" not in data and "feesMetaData" not in data:
        return None
    return data


def _try_parse_english_requirements_json(text: str) -> list[dict] | None:
    return _try_parse_scholarships_json(text)


def _join_description(values: list[str] | str | None) -> str:
    if not values:
        return ""
    if isinstance(values, str):
        return values.strip()
    return " ".join(str(value).strip() for value in values if str(value).strip())


def _format_test_requirement(test: dict) -> str:
    name = str(test.get("TestName") or "Test").strip()
    if test.get("ieltsMinOverall"):
        return (
            f"**{name}:** {test['ieltsMinOverall']} overall, "
            f"{test.get('ieltsMinSection', '')} minimum per section"
        )
    if test.get("toeflMinOverall"):
        return (
            f"**{name}:** {test['toeflMinOverall']} overall, "
            f"{test.get('toeflMinSection', '')} minimum per section"
        )
    if test.get("pteMinOverall"):
        return (
            f"**{name}:** {test['pteMinOverall']} overall, "
            f"{test.get('pteMinSection', '')} minimum per section"
        )
    return ""


def format_scholarships_json(data: list[dict]) -> str:
    """Turn curated scholarships JSON into readable markdown for LLM extraction."""
    lines = ["# Scholarships", ""]
    for item in data:
        name = str(item.get("scholarshipName") or "Scholarship").strip()
        lines.append(f"## {name}")
        lines.append("")
        for key, label in _SCHOLARSHIP_FIELD_LABELS:
            value = item.get(key)
            if value:
                lines.append(f"- **{label}:** {str(value).strip()}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_bangladesh_entry_json(data: dict) -> str:
    lines = ["# Bangladesh Entry Requirements", ""]
    for level in data.get("studyLevels", []):
        if not isinstance(level, dict):
            continue
        study_level = str(level.get("studyLevel") or "Entry").strip()
        lines.append(f"## {study_level}")
        lines.append("")
        for program in level.get("programs", []):
            if not isinstance(program, dict):
                continue
            program_name = str(program.get("program") or "").strip()
            if program_name:
                lines.append(f"- **Program:** {program_name}")
            for requirement in program.get("requirements", []):
                if not isinstance(requirement, dict):
                    continue
                degree = str(requirement.get("degree") or "Qualification").strip()
                grade = str(requirement.get("grade") or "").strip()
                if grade:
                    lines.append(f"- **{degree}:** {grade}")
            description = _join_description(program.get("description"))
            if description:
                lines.append(f"- **Description:** {description}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_deposit_json(data: dict) -> str:
    lines = ["# Tuition Fee Deposit", ""]
    initial_deposit = str(data.get("initialDeposit") or "").strip()
    metadata = [
        item for item in data.get("feesMetaData", []) if isinstance(item, dict)
    ]
    if not metadata and initial_deposit:
        lines.append("## Initial Deposit")
        lines.append("")
        lines.append(f"- **Amount:** {initial_deposit}")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    for item in metadata:
        subtitle = str(item.get("subtitle") or "Deposit").strip()
        lines.append(f"## {subtitle}")
        lines.append("")
        if initial_deposit:
            lines.append(f"- **Amount:** {initial_deposit}")
        description = _join_description(item.get("description"))
        if description:
            lines.append(f"- **Description:** {description}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def format_english_requirements_json(data: list[dict]) -> str:
    lines = ["# English Language Requirements", ""]
    for item in data:
        study_level = str(item.get("TestStudyLevel") or "Requirements").strip()
        lines.append(f"## {study_level}")
        lines.append("")
        program_name = str(item.get("ProgramName") or "").strip()
        if program_name:
            lines.append(f"- **Program:** {program_name}")
        for test in item.get("TestRequirements", []):
            if not isinstance(test, dict):
                continue
            formatted = _format_test_requirement(test)
            if formatted:
                lines.append(f"- {formatted}")
        description = _join_description(item.get("description"))
        if description:
            lines.append(f"- **Description:** {description}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_uni_json_payload(text: str, html_stem: str) -> object | None:
    """Parse a uni_req JSON payload from HTML or clean/uni markdown."""
    parser = _JSON_UNI_PARSERS.get(html_stem)
    if parser is None:
        return None
    return parser(text)


def _json_uni_cleanup(markdown: str, *, html_stem: str, raw_source: str) -> str:
    """Keep curated uni_req JSON in markdown as a fenced ```json block."""
    title = _UNI_JSON_TITLES.get(html_stem, html_stem.replace("-", " ").title())
    for source in (raw_source, markdown):
        data = parse_uni_json_payload(source, html_stem)
        if data is not None:
            return format_json_as_markdown(data, title=title)
    return markdown


_JSON_UNI_PARSERS = {
    "bangladesh-entry": _try_parse_bangladesh_entry_json,
    "english-requirements": _try_parse_english_requirements_json,
    "scholarships": _try_parse_scholarships_json,
    "deposit": _try_parse_deposit_json,
}


def cleanup_uni_markdown(
    markdown: str,
    *,
    html_stem: str,
    raw_source: str,
    code_dir: Path | None = None,
) -> str:
    return _json_uni_cleanup(markdown, html_stem=html_stem, raw_source=raw_source)


def uni_source_url(
    raw_source: str,
    *,
    html_stem: str,
    code_dir: Path | None = None,
) -> str | None:
    if code_dir is None:
        return None
    parser = _JSON_UNI_PARSERS.get(html_stem)
    if parser is None or parser(raw_source) is None:
        return None
    return uni_source_urls_from_env(code_dir).get(html_stem)


def scholarships_source_url(
    raw_source: str,
    *,
    code_dir: Path | None = None,
) -> str | None:
    return uni_source_url(raw_source, html_stem="scholarships", code_dir=code_dir)


def _format_frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def apply_course_cleanup_to_dir(courses_dir: Path, code_dir: Path) -> tuple[int, int]:
    """Re-apply cleanup_course_markdown to existing clean/courses/**/*.md bodies."""
    if not courses_dir.is_dir():
        raise FileNotFoundError(f"Course markdown directory not found: {courses_dir}")

    from study_level import iter_course_markdown

    updated = 0
    total = 0
    for path in iter_course_markdown(courses_dir):
        total += 1
        raw = path.read_text(encoding="utf-8")
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                meta_lines = parts[1].strip().splitlines()
                meta: dict[str, str] = {}
                for line in meta_lines:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        meta[key.strip()] = value.strip()
                body = parts[2].lstrip("\n")
            else:
                meta, body = {}, raw
        else:
            meta, body = {}, raw

        cleaned_body = cleanup_course_markdown(body.rstrip("\n"), code_dir=code_dir)
        output = _format_frontmatter(meta) + cleaned_body + "\n"
        if output != raw:
            path.write_text(output, encoding="utf-8")
            updated += 1
            print(f"  updated {path.name}")
        else:
            print(f"  unchanged {path.name}")

    return updated, total


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Re-apply shared course_markdown_cleanup to output/clean/courses/*.md"
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help="University code/ directory (default: current working directory)",
    )
    args = parser.parse_args(argv)

    code_dir = resolve_code_dir(args.code_dir)
    courses_dir = resolve_output_dir(code_dir) / "clean" / "courses"
    print(f"Cleaning course markdown in {courses_dir}...")
    updated, total = apply_course_cleanup_to_dir(courses_dir, code_dir)
    print(f"Done: {updated}/{total} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
