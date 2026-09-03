#!/usr/bin/env python3
"""Two-stage Ollama extraction: course md -> Stage 1 JSON -> Stage 2 Course.csv row."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from course_markdown_cleanup import parse_uni_json_payload
from normalize_admission_data import derive_hsc_gpa_from_uk_entry_text
from uni_pages import (
    UNI_MD_BY_ROLE,
    UNI_SECTION_TITLES,
    course_slug_from_url,
    split_frontmatter,
)
from ollama_client import chat
from uni_paths import resolve_code_dir, resolve_output_dir
from study_level import (
    PRESETUP_CLEAN_SUBDIR,
    PRESETUP_EXTRACT_SUBDIR,
    clean_courses_root,
    extraction_dir,
    extraction_resume_key,
    intake_start_year_from_md_path,
    is_resume_completed,
    iter_course_markdown,
    llm_course_level,
    load_presetup_sample,
    normalize_url,
    parse_study_levels,
    presetup_sample_urls,
    relative_course_md,
    study_level_from_markdown,
    unique_urls,
)

_SHARED_DIR = Path(__file__).resolve().parent
_CODE_DIR: Path | None = None
_OUTPUT_DIR: Path | None = None
PROMPT_1: Path
PROMPT_2: Path
PROMPT_2_LLM: Path
PROMPT_2_ENTRY: Path
PROMPT_2_ENGLISH: Path
PROMPT_2_SCHOLARSHIP: Path
PROMPT_2_INITIAL_DEPOSIT: Path
MASTER_COURSE_CSV: Path











DEFAULT_UNIVERSITY = "."
COURSE_INDEX_REL = Path("courses.csv")
EXTRACTED_CSV_REL = Path("extracted_courses.csv")
COURSE_MD_INDEX_COLUMN = "course.md"
EXTRACT_INDEX_FILES = (
    "normalized.json",
    "output.json",
    "stage1_parsed.json",
    "parser_hints.json",
    "extraction_warnings.json",
    "entry_requirement_parsed.json",
    "english_requirements_parsed.json",
    "scholarship_parsed.json",
)

COURSE_INDEX_COLUMNS = [
    "uniName",
    "courseName",
    "degreeName",
    "courseUrlExternal",
    "md_file",
    "study_level",
    "expectedFromMd",
    "stage1_output",
    "stage2_output",
    "output_json",
    COURSE_MD_INDEX_COLUMN,
    *EXTRACT_INDEX_FILES,
]

DEGREE_ALIASES = {
    "bsc (hons)": "BSc",
    "bsc hons": "BSc",
    "bsc": "BSc",
    "ba (hons)": "BA",
    "ba hons": "BA",
    "ba": "BA",
    "bba": "BBA",
    "beng (hons)": "BEng",
    "beng": "BEng",
    "llb (hons)": "LLB",
    "llb": "LLB",
    "msc": "MSc",
    "ma": "MA",
    "mba": "MBA",
    "mfa": "MFA",
    "phd": "PhD",
    "mres": "MRes",
    "pgdip": "PGDip",
    "pgcert": "PGCert",
    "fdsc": "FdSc",
    "fd": "Fd",
    "certhe": "CertHE",
    "meng": "MEng",
    "bm bs": "BM BS",
}

COURSE_CSV_COLUMNS = [
   
    "programmeName",
    "courseName",
    "requirements",
    "AcademicRequirementsMetaData",
    "intakeInfo",
    "courseDuration",
    "tuitionFee",
    "currency",
    "initialDeposit",
    "applicationFee",
    "feesMetaData",
   
    "applicationDeadline",
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
    "scholarshipName",
    "scholarshipAmount",
    "scholarshipType",
    "scholarshipMetaData",
    "degreeName",
    "courseUrlExternal",
    
]

LLM_STAGE2_KEYS = (
    "requirements",
    "AcademicRequirementsMetaData",
    "scholarshipName",
    "scholarshipAmount",
    "scholarshipType",
    "scholarshipMetaData",
)

ENGLISH_TEST_KEYS = (
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
)

DEPOSIT_STAGE2_KEYS = (
    "initialDeposit",
    "feesMetaData",
)

STAGE1_SCALAR_KEYS = (
    "tuitionFee",
    "currency",
    "intakeInfo",
    "courseDuration",
    "initialDeposit",
    "applicationFee",
    "applicationDeadline",
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
    "commission",
)

# CCCU (and similar) English table row labels by course level / type
STANDARD_ENGLISH_ROW = "Standard undergraduate and postgraduate programmes"
HEALTH_ENGLISH_ROW = "Professional health undergraduate programmes"
NURSING_2027_ENGLISH_ROW = "Nursing undergraduate programmes starting 2027 onwards"
NON_STANDARD_PG_ENGLISH_ROW = "Non-standard postgraduate programmes"

POSTGRADUATE_AWARD_RE = re.compile(
    r"\b(msc|ma|mba|mres|mphil|phd|pgce|pgdip|pgcert|mch|llm|edd|dba)\b",
    re.I,
)
INTAKE_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
AWARD_TOKEN_RE = re.compile(
    r"\b(BSc|BA|BBA|BEng|LLB|MSc|MA|MBA|MFA|PhD|MRes|PGDip|PGCert|FdSc|Fd|CertHE|MEng|MArch|BM BS)\b",
    re.I,
)
MONTH_YEAR_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.I,
)

BANGLADESH_TABLE_PATTERNS = {
    "foundation": re.compile(
        r"International Foundation Programme\s*\|\s*([^\n|]+)",
        re.I,
    ),
    "undergraduate": re.compile(
        r"Undergraduate Degree\s*\|\s*([^\n|]+)",
        re.I,
    ),
    "postgraduate": re.compile(
        r"Postgraduate Degree\s*\|\s*([^\n|]+)",
        re.I,
    ),
}
BANGLADESH_MARKDOWN_SECTION_PATTERNS = {
    "foundation": re.compile(r"##\s*Foundation\s*\n(.*?)(?=\n##\s|\Z)", re.I | re.S),
    "undergraduate": re.compile(r"##\s*Undergraduate\s*\n(.*?)(?=\n##\s|\Z)", re.I | re.S),
    "postgraduate": re.compile(r"##\s*Postgraduate\s*\n(.*?)(?=\n##\s|\Z)", re.I | re.S),
}
BANGLADESH_BULLET_RE = re.compile(r"^\s*-\s*\*\*([^:*]+):\*\*\s*(.+)$", re.M)
DEGREE_LABEL_MAP = {
    "hsc": "HSC",
    "hsc (alim)": "HSC",
    "hsc/alim": "HSC",
    "completion of hsc (alim)": "HSC",
    "higher secondary certificate": "HSC",
    "intermediate/hsc": "HSC",
    "a level": "A Level",
    "international advanced levels": "A Level",
    "diploma": "Diploma",
    "bachelor degree": "BSc",
    "bachelor's degree": "BSc",
    "bachelors degree": "BSc",
    "2-year bachelor degree": "BSc",
    "4-year bachelor degree": "BSc",
    "4 year bachelor degree": "BSc",
    "master's degree": "MSc",
    "masters degree": "MSc",
    "master degree": "MSc",
    "2 year master's degree": "MSc",
    "ba": "BA",
    "bsc": "BSc",
    "bba": "BBA",
    "beng": "BEng",
    "bcom": "BCom",
    "ma": "MA",
    "msc": "MSc",
    "mba": "MBA",
    "phd": "PhD",
}
ALLOWED_METADATA_SUBTITLES = {"entry requirements", "english requirement"}














































































































UG_ENTRY_DEGREES = {"HSC", "A Level", "Diploma", "BA", "BSc", "BBA", "BEng", "BCom"}
FOUNDATION_ENTRY_DEGREES = {"HSC"}
PG_ENTRY_DEGREES = {
    "BA",
    "BSc",
    "BBA",
    "BEng",
    "BCom",
    "MA",
    "MSc",
    "MBA",
    "PhD",
}
















BANGLADESH_JSON_LEVEL_ALIASES = {
    "foundation": ("foundation", "foundation year"),
    "undergraduate": ("undergraduate",),
   "postgraduate": ("postgraduate", "postgraduate research"),
}
ENGLISH_JSON_LEVEL_ALIASES = {
    "foundation": ("foundation year", "foundation"),
    "undergraduate": ("undergraduate",),
    "postgraduate": ("postgraduate", "postgraduate research"),
}
SCHOLARSHIP_JSON_LEVEL_ALIASES = {
    "foundation": ("foundation", "foundation year"),
    "undergraduate": ("undergraduate",),
    "postgraduate": ("postgraduate", "postgraduate research"),
}








UK_GRADE_LINE_RE = re.compile(r"^([A-D]{3})\s*[—\-–]")
_ENGLISH_PROGRAM_HINTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("audiology",), "healthcare science (audiology)"),
    (("pharmacy", "nursing", "midwifery"), "biomedical science, healthcare science (audiology), pharmacy"),
    (("optometry",), "optometry"),
    (("psychology", "biomedicine", "neuroscience", "biochemistry"), "biomedicine, neuroscience, biochemistry, psychology"),
    (
        ("accounting", "finance", "business", "marketing", "economics", "management", "mba", "analytics"),
        "aston business school",
    ),
    (("law", "politics", "sociology", "criminology", "forensic linguistics"), "school of law"),
    (
        ("engineering", "computer", "robotics", "mechanical", "civil", "chemical", "aerospace", "digital"),
        "engineering and physical sciences",
    ),
    (("medicine", "medical"), "aston medical school"),
)


















































PARSER_OWNED_STAGE1_KEYS = (
    "intakeInfo",
    "courseDuration",
    "tuitionFee",
    "currency",
    "ieltsMinOverall",
    "ieltsMinSection",
)

LLM_GROUNDED_SCALAR_KEYS = (
    "initialDeposit",
    "applicationFee",
    "applicationDeadline",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
)
















EXPLICIT_DEPOSIT_RE = re.compile(
    r"(?:deposit(?:\s+of)?|pay\s+a)\s+£([\d,]+)|£([\d,]+)\s+deposit",
    re.I,
)


































class ExtractionPathConfig:
    """Grouped extraction helpers."""

    @staticmethod
    def resolve_prompt_path(filename: str) -> Path:
        """Load prompt templates from shared/ only."""
        path = _SHARED_DIR / filename
        if path.is_file():
            return path
        raise FileNotFoundError(f'Prompt not found: {path}')

    @staticmethod
    def configure_code_dir(code_dir: Path) -> Path:
        """Set code/output paths for a university."""
        global _CODE_DIR, _OUTPUT_DIR, PROMPT_1, PROMPT_2, PROMPT_2_LLM, PROMPT_2_ENTRY
        global PROMPT_2_ENGLISH, PROMPT_2_SCHOLARSHIP, PROMPT_2_INITIAL_DEPOSIT, MASTER_COURSE_CSV
        _CODE_DIR = resolve_code_dir(code_dir)
        _OUTPUT_DIR = resolve_output_dir(_CODE_DIR)
        PROMPT_1 = resolve_prompt_path('prompt_1.md')
        PROMPT_2 = resolve_prompt_path('prompt_2.md')
        PROMPT_2_LLM = resolve_prompt_path('prompt_2_llm.md')
        PROMPT_2_ENTRY = resolve_prompt_path('prompt_2_entry.md')
        PROMPT_2_ENGLISH = resolve_prompt_path('prompt_2_english.md')
        PROMPT_2_SCHOLARSHIP = resolve_prompt_path('prompt_2_scholarship.md')
        PROMPT_2_INITIAL_DEPOSIT = resolve_prompt_path('prompt_2_initialDeposit.md')
        MASTER_COURSE_CSV = _OUTPUT_DIR / 'Course.csv'
        return _CODE_DIR

    @staticmethod
    def get_output_dir() -> Path:
        if _OUTPUT_DIR is None:
            raise RuntimeError('Call configure_code_dir() first')
        return _OUTPUT_DIR

    @staticmethod
    def get_code_dir() -> Path:
        if _CODE_DIR is None:
            raise RuntimeError('Call configure_code_dir() first')
        return _CODE_DIR

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def load_template(path: Path) -> str:
        return path.read_text(encoding='utf-8')

    @staticmethod
    def fill_template(template: str, **values: str) -> str:
        result = template
        for key, value in values.items():
            result = result.replace('{' + key + '}', value)
        return result

    @staticmethod
    def infer_course_name(body: str, course_url: str) -> str:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith('# '):
                return stripped[2:].strip()
        slug = urlparse(course_url).path.rstrip('/').split('/')[-1]
        return slug.replace('-', ' ').title()

    @staticmethod
    def load_uni_section(output_dir: Path, filename: str) -> str:
        """Load one clean/uni/*.md body with a labeled heading."""
        md_path = output_dir / 'clean' / 'uni' / filename
        if not md_path.exists():
            return ''
        _, body = split_frontmatter(md_path.read_text(encoding='utf-8'))
        title = UNI_SECTION_TITLES.get(filename, md_path.stem.replace('-', ' ').title())
        return f'# {title}\n\nSource file: clean/uni/{filename}\n\n{body.strip()}'

    @staticmethod
    def load_uni_content(output_dir: Path) -> str:
        uni_dir = output_dir / 'clean' / 'uni'
        if not uni_dir.exists():
            return ''
        sections: list[str] = []
        for md_path in sorted(uni_dir.glob('*.md'), key=lambda p: p.name):
            section = load_uni_section(output_dir, md_path.name)
            if section:
                sections.append(section)
        return '\n\n---\n\n'.join(sections)

    @staticmethod
    def load_uni_sections(output_dir: Path) -> dict[str, str]:
        """Load entry / english / scholarship uni markdown by role."""
        return {role: load_uni_section(output_dir, filename) for role, filename in UNI_MD_BY_ROLE.items()}

    @staticmethod
    def normalize_award_label(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", (text or "").strip())
        if not cleaned:
            return ""
        lower = cleaned.lower()
        if lower in DEGREE_ALIASES:
            return DEGREE_ALIASES[lower]
        for alias, degree in sorted(DEGREE_ALIASES.items(), key=lambda item: -len(item[0])):
            if alias in lower:
                return degree
        match = AWARD_TOKEN_RE.search(cleaned)
        if match:
            key = match.group(1).lower()
            return DEGREE_ALIASES.get(key, match.group(1))
        return ""

    @staticmethod
    def infer_degree_name_from_md(body: str) -> str:
        award_match = re.search(r"- Award\s+([^\n]+)", body, re.I)
        if award_match:
            return ExtractionPathConfig.normalize_award_label(award_match.group(1))

        overview_parts = re.split(r"##\s*Course overview\s*\n", body, maxsplit=1, flags=re.I)
        if len(overview_parts) > 1:
            section = overview_parts[1].split("\n##", 1)[0]
            for line in section.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("- "):
                    continue
                lower = stripped.lower()
                if lower.startswith(("placement year", "with foundation")):
                    continue
                award = ExtractionPathConfig.normalize_award_label(stripped)
                if award:
                    return award
                break

        frontmatter = re.match(r"---\s*\n(.*?)\n---", body, re.S)
        if frontmatter:
            for line in frontmatter.group(1).splitlines():
                if not line.lower().startswith("source_html:"):
                    continue
                value = line.split(":", 1)[1].strip().replace(".html", "")
                for part in reversed(value.split(" - ")):
                    award = ExtractionPathConfig.normalize_award_label(part)
                    if award:
                        return award
        return ""

    @staticmethod
    def infer_degree_name(course_name: str) -> str:
        leading = re.match('^(BSc|BA|BBA|BEng|LLB|MSc|MA|MBA|MFA|PhD|MRes|PGDip|PGCert|FdSc|Fd|CertHE|MEng|BM BS)\\b', course_name, re.I)
        if leading:
            key = leading.group(1).lower()
            return DEGREE_ALIASES.get(key, leading.group(1))
        if ' - ' in course_name:
            tail = course_name.split(' - ')[-1].strip().lower()
            if tail in DEGREE_ALIASES:
                return DEGREE_ALIASES[tail]
            for alias, degree in DEGREE_ALIASES.items():
                if alias in tail:
                    return degree
        match = re.search('\\b(BSc|BA|BBA|BEng|LLB|MSc|MA|MBA|MFA|PhD|MRes|PGDip|PgCert|FdSc|MEng)\\b', course_name, re.I)
        if match:
            key = match.group(1).lower()
            return DEGREE_ALIASES.get(key, match.group(1))
        return ''

    @staticmethod
    def extract_response_content(raw: dict) -> str:
        return raw.get('message', {}).get('content', '').strip()

    @staticmethod
    def response_content_from_file(path: Path) -> str:
        if not path.exists():
            return ''
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            return ''
        return extract_response_content(data)

    @staticmethod
    def stage_response_paths(slug: str) -> tuple[str, str]:
        base = f'extracted/{slug}'
        return (f'{base}/stage1_response.json', f'{base}/stage2_llm_parsed.json')

    @staticmethod
    def load_json_file_compact(path: Path) -> str:
        if not path.exists():
            return ''
        try:
            return json.dumps(json.loads(path.read_text(encoding='utf-8')), ensure_ascii=False)
        except json.JSONDecodeError:
            return ''

    @staticmethod
    def detect_stage_outputs(
    output_dir: Path,
    course_url: str,
    study_level: str = "",
) -> tuple[str, str, str]:
        slug = course_slug_from_url(course_url)
        audit_dir = extraction_dir(output_dir, slug, study_level)
        stage1 = response_content_from_file(audit_dir / 'stage1_response.json')
        stage2_path = audit_dir / 'stage2_llm_parsed.json'
        if stage2_path.exists():
            stage2 = load_json_file_compact(stage2_path)
        else:
            stage2 = response_content_from_file(audit_dir / 'stage2_response.json')
        output_json = load_json_file_compact(audit_dir / 'output.json')
        return (stage1, stage2, output_json)

    @staticmethod
    def extract_artifact_relpaths(
    output_dir: Path,
    course_url: str,
    study_level: str,
) -> dict[str, str]:
        """Relative paths under output/extracted/ for each per-course extract file."""
        slug = course_slug_from_url(course_url)
        audit_dir = extraction_dir(output_dir, slug, study_level)
        extracted_root = output_dir / 'extracted'
        paths: dict[str, str] = {}
        for name in EXTRACT_INDEX_FILES:
            path = audit_dir / name
            if path.is_file():
                try:
                    paths[name] = path.relative_to(extracted_root).as_posix()
                except ValueError:
                    paths[name] = path.as_posix()
            else:
                paths[name] = ''
        return paths

    @staticmethod
    def save_audit(audit_dir: Path, name: str, content: str) -> None:
        audit_dir.mkdir(parents=True, exist_ok=True)
        (audit_dir / name).write_text(content, encoding='utf-8')

class Stage1MarkdownParser:
    """Grouped extraction helpers."""

    @staticmethod
    def extract_international_fees_section(body: str) -> str:
        match = re.search('### International students\\s*(.*?)(?:--END--|\\Z)', body, re.S | re.I)
        return match.group(1) if match else ''

    @staticmethod
    def parse_international_fee_options(section: str) -> list[dict[str, str]]:
        options: list[dict[str, str]] = []
        lines = [line.strip() for line in section.splitlines()]
        index = 0
        while index < len(lines):
            if re.fullmatch('-\\s*Full Time', lines[index], re.I):
                duration = ''
                fee = ''
                if index + 1 < len(lines) and lines[index + 1].startswith('- '):
                    duration = lines[index + 1][2:].strip()
                if index + 2 < len(lines) and lines[index + 2].startswith('- £'):
                    fee = lines[index + 2][2:].strip()
                if duration and fee:
                    options.append({'studyMode': 'Full Time', 'courseDuration': duration, 'tuitionFee': fee})
                index += 3
            else:
                index += 1
        return options

    @staticmethod
    def pick_primary_fee_option(options: list[dict[str, str]]) -> dict[str, str] | None:
        if not options:
            return None
        for option in options:
            if 'placement' not in option['courseDuration'].lower():
                return option
        return options[0]

    @staticmethod
    def normalize_short_month_date(text: str) -> str:
        """Sep 2027 -> September 2027 (BCU fees block uses abbreviated months)."""
        month_abbrev = {'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April', 'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August', 'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'}
        match = re.match('^([A-Za-z]{3,})\\s+(\\d{4})$', (text or '').strip())
        if not match:
            return (text or '').strip()
        key = match.group(1).lower()[:3]
        if key in month_abbrev:
            return f'{month_abbrev[key]} {match.group(2)}'
        return match.group(0).strip()

    @staticmethod
    def normalize_intake_text(text: str) -> str:
        """Normalize one intake line; split space-separated Month YYYY tokens."""
        text = (text or '').strip()
        if not text:
            return ''
        if ',' in text:
            return normalize_intake(text)
        tokens = re.findall('\\b(January|February|March|April|May|June|July|August|September|October|November|December)\\s+((?:19|20)\\d{2})\\b', text, re.I)
        if len(tokens) >= 2:
            return ', '.join((f'{month.title()} {year}' for month, year in tokens))
        if len(tokens) == 1:
            return f'{tokens[0][0].title()} {tokens[0][1]}'
        return normalize_short_month_date(text)

    @staticmethod
    def extract_aru_international_tuition_fee(body: str) -> str:
        """ARU course pages: **£17,500** International students starting 2026/27 …"""
        patterns = (
            '£([\\d,]+)\\s+International students starting',
            '\\*\\*£([\\d,]+)\\*\\*\\s*International students starting',
            'International students starting[^£\\n]{0,40}\\*\\*£([\\d,]+)\\*\\*',
            'International students starting[^.\\n]{0,80}£([\\d,]+)\\s*(?:\\(|per year|full-time)',
        )
        for pattern in patterns:
            match = re.search(pattern, body, re.I)
            if match:
                return match.group(1).replace(',', '')
        return ''

    @staticmethod
    def extract_international_fee_from_fees_metadata_dict(
        fees_meta: dict,
    ) -> tuple[str, str]:
        """Read international tuitionFee/currency from flat or nested LLM feesMetaData."""
        if not isinstance(fees_meta, dict):
            return '', ''

        top_fee = fees_meta.get('tuitionFee')
        if top_fee not in (None, '', 0):
            fee_str = normalize_fee_numeric(str(top_fee))
            currency = str(fees_meta.get('currency') or '').strip()
            if fee_str:
                return fee_str, currency or 'GBP'

        international: list[tuple[str, str]] = []
        for key, value in fees_meta.items():
            if str(key).casefold() in {'tuitionfee', 'currency', 'placementyearfee'}:
                continue
            if 'international' not in str(key).casefold():
                continue
            fee_val = ''
            currency = 'GBP'
            if isinstance(value, dict):
                raw_fee = value.get('fee', value.get('tuitionFee'))
                if raw_fee not in (None, '', 0):
                    fee_val = normalize_fee_numeric(str(raw_fee))
                currency = str(value.get('currency') or 'GBP').strip() or 'GBP'
            elif value not in (None, '', 0):
                fee_val = normalize_fee_numeric(str(value))
            if fee_val:
                international.append((fee_val, currency))

        if international:
            return international[0]
        return '', ''

    @staticmethod
    def fees_metadata_object_to_array(
    fees_meta: dict,
    *,
    tuition_fee: str = "",
    include_tuition_line: bool = True,
) -> list[dict[str, object]]:
        """Convert LLM feesMetaData object into standard subtitle/description blocks."""
        descriptions: list[str] = []
        if include_tuition_line:
            fee_val = tuition_fee or fees_meta.get('tuitionFee')
            if fee_val not in (None, ''):
                try:
                    fee_display = f"£{int(str(fee_val).replace(',', '')):,}"
                except ValueError:
                    fee_display = f'£{fee_val}'
                descriptions.append(f'International tuition fee: {fee_display} (full-time, per year)')
        placement = fees_meta.get('placementYearFee')
        if placement not in (None, ''):
            try:
                placement_display = f"£{int(str(placement).replace(',', '')):,}"
            except ValueError:
                placement_display = f'£{placement}'
            descriptions.append(f'Placement year fee: {placement_display}')
        if not descriptions:
            return []
        return [{'subtitle': 'Fees', 'description': descriptions}]

    @staticmethod
    def coalesce_stage1_fields_from_fees_metadata(parsed: dict, course_body: str) -> None:
        """Fill parser-owned scalars from structured feesMetaData when the markdown parser missed them."""
        fees_meta = parsed.get('feesMetaData')
        if not isinstance(fees_meta, dict):
            return
        if not str(parsed.get('tuitionFee', '') or '').strip():
            fee, currency = Stage1MarkdownParser.extract_international_fee_from_fees_metadata_dict(
                fees_meta
            )
            if fee and (not course_body or fee_amount_in_markdown(fee, course_body)):
                parsed['tuitionFee'] = fee
            if currency and not str(parsed.get('currency', '') or '').strip():
                parsed['currency'] = currency
        if not str(parsed.get('currency', '') or '').strip() and fees_meta.get('currency'):
            parsed['currency'] = str(fees_meta.get('currency')).strip()
        parsed['feesMetaData'] = fees_metadata_object_to_array(fees_meta, tuition_fee=str(parsed.get('tuitionFee', '') or ''))

    @staticmethod
    def extract_stage1_fields_from_md(body: str) -> dict[str, str]:
        """Parse intake, fees, duration, and IELTS scalars from clean course markdown."""
        fields: dict[str, str] = {}
        for pattern in ('-\\s*\\*\\*Start date:\\*\\*\\s*([^\\n]+)', '- Start date\\s+([^\\n]+)', '\\*\\*Start date\\*\\*\\s*\\n+\\s*([^\\n#]+)', 'Starting:\\s*([^\\n]+)'):
            start_date_match = re.search(pattern, body, re.I)
            if start_date_match:
                fields['intakeInfo'] = normalize_intake_text(start_date_match.group(1).strip())
                break
        duration_match = re.search('\\*\\*Duration:\\*\\*\\s*(.+)', body, re.I)
        if duration_match:
            fields['courseDuration'] = duration_match.group(1).strip()
        fee_match = re.search('(?:Annual tuition fees|First year tuition fee):\\s*\\|\\s*£([\\d,]+)', body, re.I)
        if fee_match:
            fields['tuitionFee'] = fee_match.group(1).replace(',', '')
            fields['currency'] = 'GBP'
        if not fields.get('tuitionFee'):
            aru_fee = extract_aru_international_tuition_fee(body)
            if aru_fee:
                fields['tuitionFee'] = aru_fee
                fields['currency'] = 'GBP'
        intl_section = extract_international_fees_section(body)
        if intl_section:
            if not fields.get('tuitionFee'):
                aru_fee = extract_aru_international_tuition_fee(intl_section)
                if aru_fee:
                    fields['tuitionFee'] = aru_fee
                    fields['currency'] = 'GBP'
            fee_options = parse_international_fee_options(intl_section)
            primary_fee = pick_primary_fee_option(fee_options)
            if primary_fee:
                if not fields.get('courseDuration'):
                    fields['courseDuration'] = primary_fee['courseDuration']
                if not fields.get('tuitionFee'):
                    fee_raw = primary_fee['tuitionFee']
                    fee_num = re.search('£([\\d,]+)', fee_raw)
                    fields['tuitionFee'] = fee_num.group(1).replace(',', '') if fee_num else fee_raw
            if not fields.get('currency') and (fields.get('tuitionFee') or '£' in intl_section):
                fields['currency'] = 'GBP'
        ielts_match = re.search('IELTS\\s+([\\d.]+)\\s+overall\\s+with\\s+no\\s+less\\s+than\\s+([\\d.]+)\\s+in\\s+each\\s+band', body, re.I)
        if ielts_match:
            fields['ieltsMinOverall'] = ielts_match.group(1)
            fields['ieltsMinSection'] = ielts_match.group(2)
        degree = ExtractionPathConfig.infer_degree_name_from_md(body)
        if degree:
            fields['degreeName'] = degree
        return fields

    @staticmethod
    def extract_expected_from_md(
    body: str,
    *,
    course_name: str,
    course_url: str,
    degree_name: str,
) -> str:
        level_match = re.search('- Level\\s+([^\\n]+)', body)
        study_mode_match = re.search('- Study mode\\s+([^\\n]+)', body)
        award_match = re.search('- Award\\s+([^\\n]+)', body)
        hints = extract_stage1_fields_from_md(body)
        intl_section = extract_international_fees_section(body)
        fee_options = parse_international_fee_options(intl_section)
        primary_fee = pick_primary_fee_option(fee_options)
        expected: dict[str, object] = {'courseName': course_name, 'courseUrlExternal': course_url, 'degreeName': degree_name, 'level': level_match.group(1).strip() if level_match else '', 'studyMode': study_mode_match.group(1).strip() if study_mode_match else '', 'award': award_match.group(1).strip() if award_match else '', 'intakeInfo': hints.get('intakeInfo', ''), 'courseDuration': hints.get('courseDuration', '') or (primary_fee['courseDuration'] if primary_fee else ''), 'tuitionFee': hints.get('tuitionFee', '') or (primary_fee['tuitionFee'] if primary_fee else ''), 'currency': hints.get('currency', '') or ('GBP' if primary_fee or '£' in intl_section else ''), 'ieltsMinOverall': hints.get('ieltsMinOverall', ''), 'ieltsMinSection': hints.get('ieltsMinSection', '')}
        if len(fee_options) > 1:
            seen: set[tuple[str, str]] = set()
            unique_options: list[dict[str, str]] = []
            for option in fee_options:
                key = (option['courseDuration'], option['tuitionFee'])
                if key in seen:
                    continue
                seen.add(key)
                unique_options.append(option)
            expected['tuitionFeeOptions'] = unique_options
        return json.dumps(expected, ensure_ascii=False, indent=2)

    @staticmethod
    def normalize_duration_months(value: str) -> str:
        value = (value or '').strip()
        if not value:
            return ''
        match = re.search('(\\d+)\\s*months?\\b', value, re.I)
        if match:
            return match.group(1)
        match = re.search('(\\d+)\\s*years?\\b', value, re.I)
        if match:
            return str(int(match.group(1)) * 12)
        if value.isdigit():
            return value
        return ''

    @staticmethod
    def normalize_intake(value: str) -> str:
        value = (value or '').strip()
        if not value:
            return ''
        parts = [part.strip() for part in value.split(',') if part.strip()]
        intake_parts = [part for part in parts if INTAKE_YEAR_RE.search(part) or MONTH_YEAR_RE.search(part)]
        return ', '.join(intake_parts) if intake_parts else value

    @staticmethod
    def normalize_fee_numeric(value: str) -> str:
        value = (value or '').strip()
        if not value:
            return ''
        digits = re.sub('[^\\d.]', '', value.replace(',', ''))
        if not digits:
            return ''
        try:
            number = float(digits)
        except ValueError:
            return digits
        if number.is_integer():
            return str(int(number))
        return f'{number:.2f}'.rstrip('0').rstrip('.')

    @staticmethod
    def fee_amount_in_markdown(amount: str, body: str) -> bool:
        amount = str(amount or '').strip()
        if not amount or not body:
            return False
        if amount in body:
            return True
        if amount.isdigit():
            try:
                with_commas = f'{int(amount):,}'
                if with_commas in body:
                    return True
            except ValueError:
                pass
        return False

class CourseIndexManager:
    """Grouped extraction helpers."""

    @staticmethod
    def attach_extract_artifacts(row: dict[str, str], output_dir: Path) -> dict[str, str]:
        row.update(ExtractionPathConfig.extract_artifact_relpaths(output_dir, row.get('courseUrlExternal') or '', row.get('study_level') or ''))
        md_rel = (row.get('md_file') or '').replace('\\', '/').strip()
        md_path = output_dir / 'clean' / 'courses' / md_rel if md_rel else None
        row[COURSE_MD_INDEX_COLUMN] = md_rel if md_path and md_path.is_file() else ''
        return row

    @staticmethod
    def write_course_index(output_dir: Path, rows: list[dict[str, str]]) -> Path:
        output_path = course_index_path(output_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', newline='', encoding='utf-8-sig') as handle:
            writer = csv.DictWriter(handle, fieldnames=COURSE_INDEX_COLUMNS, delimiter=',', quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for row in rows:
                writer.writerow({col: row.get(col, '') for col in COURSE_INDEX_COLUMNS})
        return output_path

    @staticmethod
    def update_course_index_outputs(
    output_dir: Path,
    *,
    md_file: str,
    stage1_output: str,
    stage2_output: str,
    output_json: str = "",
) -> None:
        rows = read_course_index_csv(output_dir)
        target = Path(md_file).as_posix().replace('\\', '/')
        target_name = Path(md_file).name
        updated = False
        for row in rows:
            row_file = row.get('md_file', '').strip().replace('\\', '/')
            if row_file == target:
                row['stage1_output'] = stage1_output
                row['stage2_output'] = stage2_output
                row['output_json'] = output_json
                attach_extract_artifacts(row, output_dir)
                updated = True
                break
        if not updated:
            matches = [row for row in rows if Path(row.get('md_file', '')).name == target_name]
            if len(matches) == 1:
                matches[0]['stage1_output'] = stage1_output
                matches[0]['stage2_output'] = stage2_output
                matches[0]['output_json'] = output_json
                attach_extract_artifacts(matches[0], output_dir)
                updated = True
        if not updated:
            return
        write_course_index(output_dir, rows)

    @staticmethod
    def course_index_path(output_dir: Path) -> Path:
        return output_dir / COURSE_INDEX_REL

    @staticmethod
    def extracted_csv_path(output_dir: Path) -> Path:
        return output_dir / EXTRACTED_CSV_REL

    @staticmethod
    def read_tab_csv(path: Path) -> list[dict[str, str]]:
        text = path.read_text(encoding='utf-8-sig')
        if text.startswith('sep='):
            text = text.split('\n', 1)[1]
        delimiter = '\t' if text.splitlines() and '\t' in text.splitlines()[0] else ','
        reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
        rows = []
        for row in reader:
            if not any((str(value).strip() for value in row.values())):
                continue
            rows.append({key: (value or '').strip() for key, value in row.items()})
        return rows

    @staticmethod
    def read_course_index_csv(output_dir: Path) -> list[dict[str, str]]:
        path = course_index_path(output_dir)
        if not path.exists():
            raise FileNotFoundError(f'{path} not found — run: python llm_extract.py --build-index')
        return read_tab_csv(path)

    @staticmethod
    def index_row_to_entry(row: dict[str, str]) -> dict[str, str]:
        md_file = row.get('md_file', '').strip()
        clean_md = md_file if md_file.startswith('clean/') else f'clean/courses/{md_file}'
        return {'uniName': row.get('uniName', '').strip(), 'courseName': row.get('courseName', '').strip(), 'degreeName': row.get('degreeName', '').strip(), 'course_url': row.get('courseUrlExternal', '').strip(), 'courseUrlExternal': row.get('courseUrlExternal', '').strip(), 'md_file': md_file, 'clean_md': clean_md.replace('\\', '/'), 'study_level': row.get('study_level', '').strip()}

    @staticmethod
    def normalize_course_name_key(name: str) -> str:
        return ' '.join((name or '').strip().split()).casefold()

    @staticmethod
    def canonical_md_priority(md_name: str, course_url: str) -> tuple[int, int, str]:
        """Prefer slug.md over slug-2.md when multiple markdown files share one URL."""
        slug = course_slug_from_url(course_url)
        stem = Path(md_name).stem
        if stem == slug:
            return (0, 0, md_name.lower())
        match = re.fullmatch(re.escape(slug) + '-(\\d+)', stem)
        if match:
            return (1, int(match.group(1)), md_name.lower())
        return (2, 0, md_name.lower())

    @staticmethod
    def group_course_md_paths(courses_dir: Path) -> dict[tuple[str, str], list[Path]]:
        groups: dict[tuple[str, str], list[Path]] = {}
        for md_path in iter_course_markdown(courses_dir):
            meta, body = split_frontmatter(md_path.read_text(encoding='utf-8'))
            course_url = meta.get('course_url', '').strip() or meta.get('source_url', '').strip()
            if not course_url:
                continue
            course_name = ExtractionPathConfig.infer_course_name(body, course_url)
            level = study_level_from_markdown(md_path, meta, courses_dir=courses_dir, course_url=course_url, course_name=course_name)
            groups.setdefault((level, course_url), []).append(md_path)
        return groups

    @staticmethod
    def pick_canonical_md_path(paths: list[Path], course_url: str) -> Path:
        return min(paths, key=lambda path: canonical_md_priority(path.name, course_url))

    @staticmethod
    def select_canonical_course_md_paths(courses_dir: Path) -> list[Path]:
          """One markdown per course for the LLM index.

        1. One file per (study_level, URL) — slug.md beats slug-2.md.
        2. One file per (study_level, course_name) — latest intake year wins
           (e.g. 2027 - 2028 over 2026 - 2027).
          """
          url_picks: list[Path] = []
          for (_level, course_url), paths in sorted(group_course_md_paths(courses_dir).items()):
              url_picks.append(pick_canonical_md_path(paths, course_url))

          by_name: dict[tuple[str, str], list[Path]] = {}
          for md_path in url_picks:
              meta, body = split_frontmatter(md_path.read_text(encoding="utf-8"))
              course_url = meta.get("course_url", "").strip() or meta.get("source_url", "").strip()
              if not course_url:
                  continue
              course_name = infer_course_name(body, course_url)
              level = study_level_from_markdown(
                  md_path,
                  meta,
                  courses_dir=courses_dir,
                  course_url=course_url,
                  course_name=course_name,
              )
              by_name.setdefault((level, normalize_course_name_key(course_name)), []).append(md_path)

          selected: list[Path] = []
          for (_level, _name_key), paths in sorted(by_name.items()):
              if len(paths) == 1:
                  selected.append(paths[0])
                  continue
              selected.append(
                  max(
                      paths,
                      key=lambda path: (
                          intake_start_year_from_md_path(path),
                          path.as_posix().lower(),
                      ),
                  )
              )
          return sorted(selected, key=lambda path: path.as_posix().lower())

    @staticmethod
    def expected_canonical_md_names(courses_dir: Path) -> set[str]:
        return {relative_course_md(md_path, courses_dir) for md_path in select_canonical_course_md_paths(courses_dir)}

    @staticmethod
    def dedupe_course_index_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        """Keep one markdown row per (study_level, URL). Canonical slug.md wins over slug-2.md."""
        grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
        for row in rows:
            course_url = row.get('courseUrlExternal', '').strip()
            if not course_url:
                continue
            level = row.get('study_level', '').strip() or 'undergraduate'
            grouped.setdefault((level, course_url), []).append(row)
        deduped: list[dict[str, str]] = []
        for level, course_url in sorted(grouped):
            rows_for_url = grouped[level, course_url]
            if len(rows_for_url) == 1:
                deduped.append(rows_for_url[0])
                continue
            deduped.append(min(rows_for_url, key=lambda row: canonical_md_priority(Path(row.get('md_file', '')).name, course_url)))
        return deduped

    @staticmethod
    def build_course_index(code_dir: Path) -> Path:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        courses_dir = output_dir / 'clean' / 'courses'
        if not courses_dir.exists():
            raise FileNotFoundError(f'{courses_dir} not found — run download_and_clean_course_pages.py --clean-only first')
        university_name = code_dir.parent.name
        rows: list[dict[str, str]] = []
        canonical_paths = select_canonical_course_md_paths(courses_dir)
        total_md_files = len(iter_course_markdown(courses_dir))
        for md_path in canonical_paths:
            meta, body = split_frontmatter(md_path.read_text(encoding='utf-8'))
            course_url = meta.get('course_url', '').strip() or meta.get('source_url', '').strip()
            if not course_url:
                continue
            course_name = ExtractionPathConfig.infer_course_name(body, course_url)
            degree_name = (
                ExtractionPathConfig.infer_degree_name_from_md(body)
                or ExtractionPathConfig.infer_degree_name(course_name)
            )
            uni_name = meta.get('university', university_name).strip() or university_name
            study_level = study_level_from_markdown(md_path, meta, courses_dir=courses_dir, course_url=course_url, course_name=course_name)
            expected_from_md = Stage1MarkdownParser.extract_expected_from_md(body, course_name=course_name, course_url=course_url, degree_name=degree_name)
            stage1_output, stage2_output, output_json = ExtractionPathConfig.detect_stage_outputs(output_dir, course_url, study_level)
            rows.append(attach_extract_artifacts({'uniName': uni_name, 'courseName': course_name, 'degreeName': degree_name, 'courseUrlExternal': course_url, 'md_file': relative_course_md(md_path, courses_dir), 'study_level': study_level, 'expectedFromMd': expected_from_md, 'stage1_output': stage1_output, 'stage2_output': stage2_output, 'output_json': output_json}, output_dir))
        output_path = write_course_index(output_dir, rows)
        skipped = total_md_files - len(rows)
        if skipped:
            print(f'Skipped {skipped} duplicate intake/URL variant(s) ({total_md_files} markdown files -> {len(rows)} courses)', flush=True)
        print(f'Wrote {output_path} ({len(rows)} courses)')
        return output_path

    @staticmethod
    def course_index_is_stale(output_dir: Path) -> bool:
        courses_dir = output_dir / 'clean' / 'courses'
        if not courses_dir.exists():
            return False
        expected_md = expected_canonical_md_names(courses_dir)
        index_path = course_index_path(output_dir)
        if not index_path.exists():
            return True
        index_md = {row.get('md_file', '').strip() for row in read_course_index_csv(output_dir) if row.get('md_file', '').strip()}
        return expected_md != index_md

    @staticmethod
    def ensure_course_index_synced(code_dir: Path) -> Path:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        if course_index_is_stale(output_dir):
            print('courses.csv out of sync with clean/courses — rebuilding index', flush=True)
            return build_course_index(code_dir)
        return course_index_path(output_dir)

    @staticmethod
    def load_manifest(output_dir: Path) -> dict:
        path = output_dir / 'clean' / 'manifest.json'
        if not path.exists():
            raise FileNotFoundError(f'{path} not found — run download_and_clean_course_pages.py first')
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def entries_from_presetup_clean(output_dir: Path) -> list[dict[str, str]]:
        sample = load_presetup_sample(output_dir)
        sample_urls = presetup_sample_urls(sample)
        wanted = {normalize_url(url) for url in sample_urls}
        url_level: dict[str, str] = {}
        for row in sample.get('courses') or []:
            if not isinstance(row, dict):
                continue
            url = normalize_url(str(row.get('course_url') or ''))
            if url:
                url_level[url] = str(row.get('study_level') or '').strip()
        courses_dir = clean_courses_root(output_dir, presetup=True)
        entries: list[dict[str, str]] = []
        for md_path in iter_course_markdown(courses_dir):
            meta, body = split_frontmatter(md_path.read_text(encoding='utf-8'))
            source_url = (meta.get('source_url') or '').strip()
            key = normalize_url(source_url)
            if wanted and key not in wanted:
                continue
            rel = relative_course_md(md_path, courses_dir)
            study_level = url_level.get(key) or study_level_from_markdown(md_path, meta, courses_dir=courses_dir, course_url=source_url)
            entries.append({'uniName': '', 'courseName': ExtractionPathConfig.infer_course_name(body, source_url), 'degreeName': '', 'course_url': source_url, 'courseUrlExternal': source_url, 'md_file': rel, 'clean_md': f'clean/{PRESETUP_CLEAN_SUBDIR}/{rel}'.replace('\\', '/'), 'study_level': study_level, 'extract_root': PRESETUP_EXTRACT_SUBDIR})
        return entries

    @staticmethod
    def ensure_csv_header(output_path: Path) -> None:
        if output_path.exists():
            return
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', newline='', encoding='utf-8-sig') as handle:
            handle.write('sep=\t\n')
            writer = csv.writer(handle, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(COURSE_CSV_COLUMNS)

    @staticmethod
    def serialize_csv_value(value: object) -> str:
        if value is None:
            return ''
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def append_csv_row(output_path: Path, row: dict[str, object]) -> None:
        ensure_csv_header(output_path)
        with output_path.open('a', newline='', encoding='utf-8-sig') as handle:
            writer = csv.writer(handle, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([serialize_csv_value(row.get(col, '')) for col in COURSE_CSV_COLUMNS])

class ExtractionProgressStore:
    """Grouped extraction helpers."""

    @staticmethod
    def extraction_progress_path(output_dir: Path, *, presetup: bool = False) -> Path:
        if presetup:
            return output_dir / 'extracted' / PRESETUP_EXTRACT_SUBDIR / 'extraction_progress.json'
        return output_dir / 'extracted' / 'extraction_progress.json'

    @staticmethod
    def load_progress(output_dir: Path, *, presetup: bool = False) -> dict:
        path = extraction_progress_path(output_dir, presetup=presetup)
        if not path.exists():
            return {'completed': [], 'failed': [], 'updated_at': ExtractionPathConfig.utc_now()}
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def save_progress(output_dir: Path, progress: dict, *, presetup: bool = False) -> None:
        path = extraction_progress_path(output_dir, presetup=presetup)
        path.parent.mkdir(parents=True, exist_ok=True)
        progress['updated_at'] = ExtractionPathConfig.utc_now()
        path.write_text(json.dumps(progress, indent=2), encoding='utf-8')

class Stage1Enricher:
    """Grouped extraction helpers."""

    @staticmethod
    def filter_stage1_entry_description(text: str) -> bool:
        """Keep only substantive academic entry sentences from Stage 1."""
        text = text.strip()
        if not text:
            return False
        lower = text.lower()
        skip_patterns = ('^see\\s+', 'see information about application', '\\bielts\\b', '\\btoefl\\b', '\\bpearson pte\\b', '\\bpte academic\\b', 'english is not your first language', 'english language requirement', 'proficient in english', 'command of english', 'previously been taught in english', 'sufficient command of english', 'taught in english', 'check the section', 'please contact', 'contact aru', 'admissions@', 'mailto:', 'guide only', 'treat everyone as an individual', 'should still consider applying', 'our decision will be based', 'studying for other qualifications should contact', '^international students$', '^standard entry requirements$', '^requirement \\d+$', '^applicants must have:\\s*$', 'did not achieve our required grades', 'life/work skills', 'whole application', 'personal circumstances', 'equivalent english', 'welcome applications from international', 'computer and reliable internet', 'digital audition', 'portfolios? and auditions', 'clearing auditions')
        for pattern in skip_patterns:
            if re.search(pattern, lower):
                return False
        keep_patterns = ('\\b2:2\\b', '\\b2:1\\b', '\\b3:2\\b', '\\bbachelor', '\\bmaster', '\\bdegree\\b', '\\bgcse\\b', '\\bucas\\b', '\\ba[- ]?level', '\\bbtec\\b', '\\bib\\b', '\\bhonou?rs\\b', '\\bqualifications\\b', '\\bnormally a minimum\\b', 'applicants must have:', '\\bphd\\b', '\\bmphil\\b', '\\blower second\\b', '\\bupper second\\b', '\\btariff points\\b', '\\bdiploma\\b', "you'll need a", 'you will need a', 'pass in', 'at grade', '\\bcccs?\\b', '\\bpoints\\b')
        return any((re.search(pattern, lower) for pattern in keep_patterns))

    @staticmethod
    def extract_stage1_entry_descriptions(stage1_json: dict) -> list[str]:
        descriptions: list[str] = []
        for item in Stage2Enricher.normalize_metadata_array(stage1_json.get('AcademicRequirementsMetaData')):
            if str(item.get('subtitle', '')).strip().lower() != 'entry requirements':
                continue
            for line in normalize_description_list(item.get('description')):
                if filter_stage1_entry_description(line):
                    descriptions.append(line)
        return descriptions

    @staticmethod
    def normalize_description_list(raw: object) -> list[str]:
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
        if raw:
            text = str(raw).strip()
            return [text] if text else []
        return []

    @staticmethod
    def extract_uk_offer_grades(text: str) -> set[str]:
        grades: set[str] = set()
        for match in re.finditer('\\b([A-D]{3})(?:\\s*[-–]\\s*([A-D]{3}))?\\b', text, re.I):
            grades.add(match.group(1).upper())
            if match.group(2):
                grades.add(match.group(2).upper())
        return grades

    @staticmethod
    def filter_bangladesh_descriptions_for_course(
    descriptions: list[str],
    *,
    course_text: str,
) -> list[str]:
        """Keep intro/policy lines plus Bangladesh grade rows matching this course's UK offers."""
        if not descriptions:
            return []
        uk_grades = extract_uk_offer_grades(course_text)
        if not uk_grades:
            return descriptions
        kept: list[str] = []
        for line in descriptions:
            stripped = line.strip()
            grade_match = UK_GRADE_LINE_RE.match(stripped)
            if grade_match:
                if grade_match.group(1).upper() in uk_grades:
                    kept.append(line)
                continue
            kept.append(line)
        return kept

    @staticmethod
    def extract_entry_lines_from_course_markdown(course_body: str) -> list[str]:
        """Parse ## Entry requirements section tables and essential UCAS lines from clean course md."""
        section_match = re.search('^##\\s+Entry requirements\\s*$', course_body, re.I | re.M)
        if not section_match:
            return []
        rest = course_body[section_match.end():]
        next_heading = re.search('^##\\s+', rest, re.M)
        section = rest[:next_heading.start()] if next_heading else rest
        lines: list[str] = []
        seen: set[str] = set()

        def add_line(text: str) -> None:
            cleaned = text.strip()
            if not cleaned or cleaned in seen:
                return
            if filter_stage1_entry_description(cleaned):
                lines.append(cleaned)
                seen.add(cleaned)
        for raw_line in section.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith('|') and '|' in stripped[1:]:
                cells = [cell.strip() for cell in stripped.strip('|').split('|')]
                if len(cells) < 2:
                    continue
                if all((re.fullmatch('-+', cell.replace(' ', '')) for cell in cells[:2])):
                    continue
                if cells[0].lower() in {'qualification', 'entry requirements'}:
                    continue
                add_line(f'{cells[0]}: {cells[1]}')
                continue
            if re.search('\\bucas tariff points\\b', stripped, re.I):
                add_line(stripped if stripped.endswith('.') else f'{stripped}.')
                continue
            if re.search('\\bgcse\\b', stripped, re.I) and re.search('grade|at grade|c/4|4 or above', stripped, re.I):
                add_line(stripped)
        return lines

    @staticmethod
    def assert_grounded(value: str, body: str) -> bool:
        """True when value is empty or its numbers/dates appear in the source body."""
        text = (value or '').strip()
        if not text:
            return True
        if not body:
            return False
        if text in body:
            return True
        if Stage1MarkdownParser.fee_amount_in_markdown(text, body):
            return True
        digits = re.sub('[^\\d.]', '', text.replace(',', ''))
        if digits and Stage1MarkdownParser.fee_amount_in_markdown(digits, body):
            return True
        tokens = re.findall('\\d+(?:[./-]\\d+)*|\\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\\b', text, re.I)
        if not tokens:
            return False
        body_cf = body.casefold()
        return all((token.casefold() in body_cf for token in tokens))

    @staticmethod
    def parser_hints_payload(hints: dict[str, str], course_body: str) -> dict[str, object]:
        snippets: dict[str, str] = {}
        fee = hints.get('tuitionFee', '')
        for line in course_body.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if fee and '£' in stripped and Stage1MarkdownParser.fee_amount_in_markdown(fee, stripped):
                snippets.setdefault('tuitionFee', stripped)
            if hints.get('intakeInfo') and (stripped.lower().startswith('starting:') or 'start date' in stripped.lower()):
                snippets.setdefault('intakeInfo', stripped)
            if hints.get('courseDuration') and re.search('\\d+\\s*(?:year|month)', stripped, re.I):
                snippets.setdefault('courseDuration', stripped)
            if hints.get('ieltsMinOverall') and 'ielts' in stripped.lower():
                snippets.setdefault('ielts', stripped)
        return {**hints, 'snippets': snippets}

    @staticmethod
    def drop_ungrounded_stage1_scalars(parsed: dict, course_body: str) -> list[str]:
        warnings: list[str] = []
        for key in LLM_GROUNDED_SCALAR_KEYS:
            value = str(parsed.get(key, '') or '').strip()
            if value and (not assert_grounded(value, course_body)):
                parsed[key] = ''
                warnings.append(f'{key}: dropped ungrounded value {value!r}')
        return warnings

    @staticmethod
    def apply_parser_owned_stage1_fields(
    parsed: dict,
    hints: dict[str, str],
    *,
    course_body: str = "",
) -> None:
        """Parser always wins for structured Stage 1 fields. Empty parser → empty field."""
        for key in PARSER_OWNED_STAGE1_KEYS:
            parsed[key] = hints.get(key, '') or ''
        if isinstance(parsed.get('feesMetaData'), dict):
            fees_dict = parsed['feesMetaData']
            if not str(parsed.get('tuitionFee', '') or '').strip():
                fee, currency = Stage1MarkdownParser.extract_international_fee_from_fees_metadata_dict(
                    fees_dict
                )
                if fee and (not course_body or Stage1MarkdownParser.fee_amount_in_markdown(fee, course_body)):
                    parsed['tuitionFee'] = fee
                if currency and not str(parsed.get('currency', '') or '').strip():
                    parsed['currency'] = currency
            if not str(parsed.get('currency', '') or '').strip() and fees_dict.get('currency'):
                parsed['currency'] = str(fees_dict.get('currency')).strip()
            parsed['feesMetaData'] = Stage1MarkdownParser.fees_metadata_object_to_array(fees_dict, tuition_fee=str(parsed.get('tuitionFee', '') or ''), include_tuition_line=not bool(str(parsed.get('tuitionFee', '') or '').strip()))
        elif not hints.get('tuitionFee'):
            Stage1MarkdownParser.coalesce_stage1_fields_from_fees_metadata(parsed, course_body)
        tuition_fee = str(parsed.get('tuitionFee', '') or '').strip()
        if tuition_fee:
            parsed['feesMetaData'] = patch_fees_metadata_international_fee(parsed.get('feesMetaData'), tuition_fee)

    @staticmethod
    def enrich_stage1_from_markdown(
    stage1_json: dict,
    *,
    course_body: str,
    course_name: str,
    course_url: str,
    warnings: list[str] | None = None,
) -> dict:
        """Apply parser-owned fields, then drop ungrounded LLM scalars."""
        parsed = dict(stage1_json) if isinstance(stage1_json, dict) else {}
        if not str(parsed.get('courseName', '') or '').strip():
            parsed['courseName'] = course_name
        if not str(parsed.get('courseUrl', '') or '').strip():
            parsed['courseUrl'] = course_url
        hints = Stage1MarkdownParser.extract_stage1_fields_from_md(course_body)
        apply_parser_owned_stage1_fields(parsed, hints, course_body=course_body)
        degree = hints.get('degreeName') or ExtractionPathConfig.infer_degree_name_from_md(course_body)
        if degree and not str(parsed.get('degreeName', '') or '').strip():
            parsed['degreeName'] = degree
        dropped = drop_ungrounded_stage1_scalars(parsed, course_body)
        if warnings is not None:
            warnings.extend(dropped)
        if not extract_stage1_entry_descriptions(parsed):
            entry_lines = extract_entry_lines_from_course_markdown(course_body)
            if not entry_lines:
                for line in course_body.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('- **A-levels:**') or stripped.startswith('- **BTEC:**'):
                        entry_lines.append(stripped.lstrip('- ').strip())
                    elif re.search('\\bBCC\\b|\\bBBB\\b|\\bBBC\\b|\\bCCD\\b|\\bCDD\\b|\\bDDM\\b|\\bDMM\\b', stripped):
                        if 'A-level' in stripped or stripped.startswith('B/') or stripped.startswith('C/'):
                            entry_lines.append(stripped)
            if entry_lines:
                parsed['AcademicRequirementsMetaData'] = [{'subtitle': 'Entry Requirements', 'description': entry_lines}]
        return parsed

    @staticmethod
    def patch_fees_metadata_international_fee(
    fees_meta: object,
    tuition_fee: str,
) -> list[dict[str, object]]:
        """Replace LLM placeholder fee lines with the parsed international tuition fee."""
        try:
            fee_display = f"£{int(str(tuition_fee).replace(',', '')):,}"
        except ValueError:
            fee_display = f'£{tuition_fee}'
        fee_line = f'International tuition fee: {fee_display}'
        meta = Stage2Enricher.normalize_metadata_array(fees_meta)
        patched = False
        for block in meta:
            subtitle = str(block.get('subtitle', '')).strip().lower()
            if subtitle != 'fees':
                continue
            descriptions: list[str] = []
            for item in block.get('description') or []:
                text = str(item)
                lower = text.lower()
                if 'find out more about the international student fee' in lower:
                    continue
                if 'example.com' in lower:
                    continue
                descriptions.append(text)
            block['description'] = [fee_line] + descriptions
            patched = True
        if not patched:
            meta.insert(0, {'subtitle': 'Fees', 'description': [fee_line]})
        return meta

class Stage2Enricher:
    """Grouped extraction helpers."""

    @staticmethod
    def canonicalize_requirement_degree(degree: str) -> str:
        normalized = re.sub('\\s+', ' ', (degree or '').strip()).lower()
        return DEGREE_LABEL_MAP.get(normalized, degree.strip())

    @staticmethod
    def extract_grade_from_requirement_text(text: str) -> str:
        value = (text or '').strip()
        if not value:
            return ''
        cgpa = re.search('CGPA\\s*([\\d.]+)', value, re.I)
        if cgpa:
            return f'CGPA {cgpa.group(1)}'
        pct = re.search('(\\d+)\\s*%', value)
        if pct:
            return f'{pct.group(1)}%'
        gpa = re.search('GPA\\s*(?:of\\s+)?([\\d.]+)', value, re.I)
        if gpa:
            return f'GPA {gpa.group(1)}'
        score = re.search('\\b(\\d{2,3})\\b', value)
        if score:
            return score.group(1)
        return value

    @staticmethod
    def extract_bangladesh_section_text(uni_content: str, course_level: str) -> str:
        markdown_pattern = BANGLADESH_MARKDOWN_SECTION_PATTERNS.get(course_level)
        if markdown_pattern:
            match = markdown_pattern.search(uni_content)
            if match:
                return match.group(1).strip()
        table_pattern = BANGLADESH_TABLE_PATTERNS.get(course_level)
        if table_pattern:
            match = table_pattern.search(uni_content)
            if match:
                return match.group(1).strip()
        return ''

    @staticmethod
    def parse_bangladesh_bullet_requirements(section_text: str) -> list[dict[str, str]]:
        requirements: list[dict[str, str]] = []
        for match in BANGLADESH_BULLET_RE.finditer(section_text):
            label = match.group(1).strip()
            if label.lower() == 'description':
                continue
            degree = canonicalize_requirement_degree(label)
            grade = extract_grade_from_requirement_text(match.group(2))
            if degree and grade:
                requirements.append({'degree': degree, 'grade': grade})
        return requirements

    @staticmethod
    def normalize_requirements_list(
    raw: object,
    *,
    course_level: str = "",
) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            return []
        items: list[dict[str, str]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            if 'degree' not in entry:
                continue
            degree = canonicalize_requirement_degree(str(entry.get('degree', '') or ''))
            grade = str(entry.get('grade', '') or '').strip()
            if not degree or not grade:
                continue
            items.append({'degree': degree, 'grade': grade})
        if course_level == 'undergraduate':
            items = [item for item in items if item['degree'] in UG_ENTRY_DEGREES]
        elif course_level == 'foundation':
            items = [item for item in items if item['degree'] in FOUNDATION_ENTRY_DEGREES]
        elif course_level == 'postgraduate':
            items = [item for item in items if item['degree'] in PG_ENTRY_DEGREES]
        return items

    @staticmethod
    def normalize_metadata_array(
    raw: object,
    *,
    default_subtitle: str = "",
) -> list[dict[str, object]]:
        if isinstance(raw, dict):
            return Stage1MarkdownParser.fees_metadata_object_to_array(raw)
        if not isinstance(raw, list):
            return []
        items: list[dict[str, object]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            subtitle = str(entry.get('subtitle') or entry.get('title') or '').strip()
            description = entry.get('description', [])
            if not isinstance(description, list):
                description = [str(description)] if description else []
            description = [str(item).strip() for item in description if str(item).strip()]
            if not subtitle and default_subtitle and description:
                subtitle = default_subtitle
            if not subtitle and (not description):
                continue
            items.append({'subtitle': subtitle, 'description': description})
        return items

    @staticmethod
    def filter_academic_metadata(metadata: list[dict[str, object]]) -> list[dict[str, object]]:
        filtered: list[dict[str, object]] = []
        for item in metadata:
            subtitle = str(item.get('subtitle', '') or '').strip().lower()
            description = item.get('description', [])
            if not isinstance(description, list) or not description:
                continue
            if not subtitle and any(('ielts' in str(d).lower() or 'overall' in str(d).lower() for d in description)):
                subtitle = 'english requirement'
                fixed_desc: list[str] = []
                for desc in description:
                    text = str(desc).strip()
                    if text and (not re.search('\\bIELTS\\b', text, re.I)) and re.search('\\d\\.\\d', text):
                        text = f'IELTS {text}'
                    fixed_desc.append(text)
                description = fixed_desc
            if subtitle not in ALLOWED_METADATA_SUBTITLES:
                continue
            filtered.append({'subtitle': 'Entry Requirements' if subtitle == 'entry requirements' else 'English Requirement', 'description': description})
        return filtered

    @staticmethod
    def score_english_program(program_name: str, haystack: str) -> int:
        program_lower = program_name.strip().lower()
        haystack_lower = haystack.casefold()
        score = 0
        for keywords, hint in _ENGLISH_PROGRAM_HINTS:
            if hint in program_lower and any((keyword in haystack_lower for keyword in keywords)):
                score += 10
        for token in re.split('[\\s:,&/()\\-]+', program_lower):
            if len(token) > 3 and token in haystack_lower:
                score += 2
        return score

    @staticmethod
    def select_english_json_program(
    programs: list[dict],
    *,
    course_level: str,
    course_name: str,
    course_body: str = "",
) -> dict | None:
        aliases = ENGLISH_JSON_LEVEL_ALIASES.get(course_level, (course_level,))
        candidates = [item for item in programs if isinstance(item, dict) and str(item.get('TestStudyLevel', '') or '').strip().lower() in aliases]
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        haystack = f'{course_name}\n{course_body}'.casefold()
        scored = sorted(((score_english_program(str(item.get('ProgramName', '') or ''), haystack), item) for item in candidates), key=lambda pair: pair[0], reverse=True)
        if scored and scored[0][0] > 0:
            return scored[0][1]
        return candidates[0]

    @staticmethod
    def extract_bangladesh_json_descriptions(
    entry_content: str,
    course_level: str,
    *,
    course_text: str = "",
) -> list[str]:
        entry_json = parse_uni_json_payload(entry_content, 'bangladesh-entry')
        if not isinstance(entry_json, dict):
            return []
        aliases = BANGLADESH_JSON_LEVEL_ALIASES.get(course_level, (course_level,))
        for level in entry_json.get('studyLevels', []):
            if not isinstance(level, dict):
                continue
            study_level = str(level.get('studyLevel', '') or '').strip().lower()
            if study_level not in aliases:
                continue
            for program in level.get('programs', []):
                if not isinstance(program, dict):
                    continue
                descriptions = Stage1Enricher.normalize_description_list(program.get('description'))
                return Stage1Enricher.filter_bangladesh_descriptions_for_course(descriptions, course_text=course_text)
        return []

    @staticmethod
    def extract_english_json_descriptions(
    english_content: str,
    course_level: str,
    *,
    course_name: str = "",
    course_body: str = "",
) -> list[str]:
        data = parse_uni_json_payload(english_content, 'english-requirements')
        if not isinstance(data, list):
            return []
        program = select_english_json_program(data, course_level=course_level, course_name=course_name, course_body=course_body)
        if not program:
            return []
        return Stage1Enricher.normalize_description_list(program.get('description'))

    @staticmethod
    def finalize_academic_requirements_metadata(
    metadata: object,
    *,
    stage1_json: dict,
    uni_content: str,
    english_content: str,
    course_level: str,
    english_scalars: dict | None = None,
    course_name: str = "",
    course_body: str = "",
    entry_content: str = "",
) -> list[dict[str, object]]:
        """Build Entry + English metadata from stage1, bangladesh JSON, and english JSON."""
        english_scalars = english_scalars or {}
        course_text = f'{course_name}\n{course_body}'.strip()
        bangladesh_source = entry_content or uni_content
        entry_descriptions: list[str] = list(Stage1Enricher.extract_stage1_entry_descriptions(stage1_json))
        seen = set(entry_descriptions)
        for line in extract_bangladesh_json_descriptions(bangladesh_source, course_level, course_text=course_text):
            if line not in seen:
                entry_descriptions.append(line)
                seen.add(line)
        english_descriptions = extract_english_json_descriptions(english_content, course_level, course_name=course_name, course_body=course_body)
        if not english_descriptions:
            for item in normalize_metadata_array(metadata):
                if str(item.get('subtitle', '')).strip().lower() == 'english requirement':
                    english_descriptions = Stage1Enricher.normalize_description_list(item.get('description'))
                    break
        if not english_descriptions:
            overall = str(english_scalars.get('ieltsMinOverall', '') or '').strip()
            section = str(english_scalars.get('ieltsMinSection', '') or '').strip()
            if overall:
                english_descriptions = [f'IELTS {overall} overall with no element below {section}' if section else f'IELTS {overall} overall']
        result: list[dict[str, object]] = []
        if entry_descriptions:
            result.append({'subtitle': 'Entry Requirements', 'description': entry_descriptions})
        if english_descriptions:
            result.append({'subtitle': 'English Requirement', 'description': english_descriptions})
        return filter_academic_metadata(result)

    @staticmethod
    def parse_bangladesh_json_requirements(data: dict, course_level: str) -> list[dict[str, str]]:
        aliases = BANGLADESH_JSON_LEVEL_ALIASES.get(course_level, (course_level,))
        requirements: list[dict[str, str]] = []
        for level in data.get('studyLevels', []):
            if not isinstance(level, dict):
                continue
            study_level = str(level.get('studyLevel', '') or '').strip().lower()
            if study_level not in aliases:
                continue
            for program in level.get('programs', []):
                if not isinstance(program, dict):
                    continue
                for requirement in program.get('requirements', []):
                    if not isinstance(requirement, dict):
                        continue
                    degree = canonicalize_requirement_degree(str(requirement.get('degree', '') or ''))
                    grade = extract_grade_from_requirement_text(str(requirement.get('grade', '') or ''))
                    if degree and grade:
                        requirements.append({'degree': degree, 'grade': grade})
        return requirements

    @staticmethod
    def parse_bangladesh_requirements(
    uni_content: str,
    course_level: str,
    *,
    entry_content: str | None = None,
) -> list[dict[str, str]]:
        for source in (entry_content, uni_content):
            if not source:
                continue
            entry_json = parse_uni_json_payload(source, 'bangladesh-entry')
            if isinstance(entry_json, dict):
                json_requirements = normalize_requirements_list(parse_bangladesh_json_requirements(entry_json, course_level), course_level=course_level)
                if json_requirements:
                    return json_requirements
        text = extract_bangladesh_section_text(entry_content or uni_content, course_level)
        if not text:
            return []
        bullet_requirements = parse_bangladesh_bullet_requirements(text)
        if bullet_requirements:
            return bullet_requirements
        requirements: list[dict[str, str]] = []
        if course_level == 'foundation':
            cgpa = re.search('CGPA\\s*([\\d.]+)', text, re.I)
            pct = re.search('(\\d+)\\s*%', text)
            if cgpa:
                requirements.append({'degree': 'HSC', 'grade': f'CGPA {cgpa.group(1)}'})
            elif pct:
                requirements.append({'degree': 'HSC', 'grade': f'{pct.group(1)}%'})
            return requirements
        if course_level == 'undergraduate':
            hsc = re.search('(?:Intermediate/)?HSC[^\\d]*CGPA\\s*([\\d.]+)', text, re.I)
            if hsc:
                requirements.append({'degree': 'HSC', 'grade': f'CGPA {hsc.group(1)}'})
            diploma = re.search('(?:polytechnic\\s+)?Diploma[^\\d]*(?:with\\s+grades\\s+above\\s+)?(\\d+)\\s*%', text, re.I)
            if diploma:
                requirements.append({'degree': 'Diploma', 'grade': f'{diploma.group(1)}%'})
            return requirements
        if course_level == 'postgraduate':
            bachelor = re.search('bachelor[^\\d]*(\\d+)\\s*%|bachelor[^\\d]*CGPA\\s*([\\d.]+)', text, re.I)
            if bachelor:
                grade = f'CGPA {bachelor.group(2)}' if bachelor.group(2) else f'{bachelor.group(1)}%'
                requirements.append({'degree': 'BSc', 'grade': grade})
            master = re.search('master[^\\d]*(\\d+)\\s*%|master[^\\d]*CGPA\\s*([\\d.]+)', text, re.I)
            if master:
                grade = f'CGPA {master.group(2)}' if master.group(2) else f'{master.group(1)}%'
                requirements.append({'degree': 'MSc', 'grade': grade})
        return requirements

    @staticmethod
    def select_english_row_label(course_name: str, course_level: str, english_content: str) -> str:
        """Pick the English table row label for this course."""
        name_lower = course_name.lower()
        for line in english_content.splitlines():
            if '|' not in line or line.strip().startswith('| ---'):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) < 2:
                continue
            label = cells[0]
            if label.lower() == course_name.lower() or (len(label) > 8 and label.lower() in name_lower):
                if re.search('\\d\\.\\d|overall|minimum', cells[1], re.I):
                    return label
        health_keywords = ('nursing', 'physiotherapy', 'midwifery', 'radiography', 'occupational therapy', 'paramedic', 'operating department', 'social work')
        if any((k in name_lower for k in health_keywords)) and course_level == 'undergraduate':
            if '2027' in name_lower and NURSING_2027_ENGLISH_ROW.lower() in english_content.lower():
                return NURSING_2027_ENGLISH_ROW
            return HEALTH_ENGLISH_ROW
        if course_level == 'postgraduate' and NON_STANDARD_PG_ENGLISH_ROW.lower() in english_content.lower():
            list_match = re.search('List of non-standard programmes(.*?)(?:\\n##|\\Z)', english_content, re.S | re.I)
            if list_match:
                blob = list_match.group(1).lower()
                tokens = [t for t in re.split('[\\s/-]+', name_lower) if len(t) > 3]
                if any((tok in blob for tok in tokens[:4])):
                    return NON_STANDARD_PG_ENGLISH_ROW
        return STANDARD_ENGLISH_ROW

    @staticmethod
    def parse_english_test_scores(
    english_content: str,
    *,
    course_name: str,
    course_level: str,
) -> dict[str, str]:
        """Rule-parse IELTS / PTE / TOEFL from the matching English table row."""
        scores = {key: '' for key in ENGLISH_TEST_KEYS}
        if not english_content.strip():
            return scores
        row_label = select_english_row_label(course_name, course_level, english_content)
        label_re = re.escape(row_label)
        ielts = re.search(f'{label_re}\\s*\\|\\s*([\\d.]+)\\s+overall with no element below\\s+([\\d.]+)', english_content, re.I)
        if ielts:
            scores['ieltsMinOverall'] = ielts.group(1)
            scores['ieltsMinSection'] = ielts.group(2)
        pte_block = re.search('Pearson PTE.*?(?=\\n##|\\nThe TOEFL|\\Z)', english_content, re.S | re.I)
        if pte_block:
            pte = re.search(f'{label_re}\\s*\\|\\s*(\\d+)\\s+overall with no element below\\s+(\\d+)', pte_block.group(0), re.I)
            if pte:
                scores['pteMinOverall'] = pte.group(1)
                scores['pteMinSection'] = pte.group(2)
        toefl_block = re.search('TOEFL.*?(?=\\n##|\\Z)', english_content, re.S | re.I)
        if toefl_block:
            toefl = re.search(f'{label_re}\\s*\\|\\s*Minimum of\\s*([\\d.]+)\\s*overall:\\s*Reading\\s*([\\d.]+),\\s*Listening\\s*([\\d.]+),\\s*Speaking\\s*([\\d.]+)\\s*(?:and|,)\\s*Writing\\s*([\\d.]+)', toefl_block.group(0), re.I)
            if toefl:
                sections = [float(toefl.group(i)) for i in range(2, 6)]
                scores['toeflMinOverall'] = toefl.group(1)
                min_section = min(sections)
                scores['toeflMinSection'] = str(int(min_section)) if min_section.is_integer() else str(min_section)
            else:
                toefl_simple = re.search(f'{label_re}\\s*\\|\\s*(?:Minimum of\\s*)?([\\d.]+)\\s*overall', toefl_block.group(0), re.I)
                if toefl_simple:
                    scores['toeflMinOverall'] = toefl_simple.group(1)
        if not scores['ieltsMinOverall']:
            named = re.search(f'\\|\\s*{label_re}\\s*\\|\\s*(?:IELTS[^|]*?)?([\\d.]+)\\s+overall with no element below\\s+([\\d.]+)', english_content, re.I)
            if named:
                scores['ieltsMinOverall'] = named.group(1)
                scores['ieltsMinSection'] = named.group(2)
        return scores

    @staticmethod
    def enrich_english_parsed(
    english_json: dict,
    english_content: str,
    *,
    course_name: str,
    course_level: str,
    stage1_json: dict | None = None,
    course_body: str = "",
) -> dict:
        """Ensure english_requirements_parsed.json has test scalars (+ metadata)."""
        parsed = dict(english_json) if isinstance(english_json, dict) else {}
        fallback = parse_english_test_scores(english_content, course_name=course_name, course_level=course_level)
        json_program = select_english_json_program(parse_uni_json_payload(english_content, 'english-requirements') or [], course_level=course_level, course_name=course_name, course_body=course_body)
        if isinstance(json_program, dict):
            for test in json_program.get('TestRequirements', []):
                if not isinstance(test, dict):
                    continue
                name = str(test.get('TestName', '') or '').lower()
                if 'ielts' in name:
                    fallback['ieltsMinOverall'] = str(test.get('ieltsMinOverall', '') or '').strip()
                    fallback['ieltsMinSection'] = str(test.get('ieltsMinSection', '') or '').strip()
                elif 'toefl' in name:
                    fallback['toeflMinOverall'] = str(test.get('toeflMinOverall', '') or '').strip()
                    fallback['toeflMinSection'] = str(test.get('toeflMinSection', '') or '').strip()
                elif 'pearson' in name or 'pte' in name:
                    fallback['pteMinOverall'] = str(test.get('pteMinOverall', '') or '').strip()
                    fallback['pteMinSection'] = str(test.get('pteMinSection', '') or '').strip()
        for key in ENGLISH_TEST_KEYS:
            current = str(parsed.get(key, '') or '').strip()
            if not current:
                parsed[key] = fallback.get(key, '')
            else:
                parsed[key] = current
        stage1_json = stage1_json or {}
        for key in ('ieltsMinOverall', 'ieltsMinSection'):
            stage1_val = str(stage1_json.get(key, '') or '').strip()
            if stage1_val:
                parsed[key] = stage1_val
        meta = normalize_metadata_array(parsed.get('AcademicRequirementsMetaData'), default_subtitle='English Requirement')
        meta = filter_academic_metadata(meta)
        json_descriptions = extract_english_json_descriptions(english_content, course_level, course_name=course_name, course_body=course_body)
        if json_descriptions:
            meta = [{'subtitle': 'English Requirement', 'description': json_descriptions}]
        elif not meta and parsed.get('ieltsMinOverall'):
            overall = parsed['ieltsMinOverall']
            section = parsed.get('ieltsMinSection', '')
            sentence = f'IELTS {overall} overall with no element below {section}' if section else f'IELTS {overall} overall'
            meta = [{'subtitle': 'English Requirement', 'description': [sentence]}]
        parsed['AcademicRequirementsMetaData'] = meta
        return {'AcademicRequirementsMetaData': parsed.get('AcademicRequirementsMetaData', []), **{key: str(parsed.get(key, '') or '').strip() for key in ENGLISH_TEST_KEYS}}

    @staticmethod
    def scholarship_study_level_matches(study_level: str, course_level: str) -> bool:
        aliases = SCHOLARSHIP_JSON_LEVEL_ALIASES.get(course_level, (course_level,))
        tokens = [token.strip().lower() for token in re.split('[,/&]', study_level) if token.strip()]
        return any((token in aliases for token in tokens))

    @staticmethod
    def parse_scholarship_numeric_amount(item: dict) -> float:
        amount_text = str(item.get('Amount', '') or '')
        amount_numbers = [float(Stage1MarkdownParser.normalize_fee_numeric(match)) for match in re.findall('£[\\d,]+(?:\\.\\d+)?', amount_text) if Stage1MarkdownParser.normalize_fee_numeric(match)]
        if amount_numbers:
            return max(amount_numbers)
        description = str(item.get('description', '') or '')
        total_match = re.search('£([\\d,]+(?:\\.\\d+)?)\\s+total\\b', description, re.I)
        if total_match:
            return float(Stage1MarkdownParser.normalize_fee_numeric(total_match.group(1)))
        value_match = re.search('(?:scholarship value|value)\\s*:\\s*£([\\d,]+(?:\\.\\d+)?)', description, re.I)
        if value_match:
            return float(Stage1MarkdownParser.normalize_fee_numeric(value_match.group(1)))
        description_numbers = [float(Stage1MarkdownParser.normalize_fee_numeric(match)) for match in re.findall('£([\\d,]+(?:\\.\\d+)?)', description) if Stage1MarkdownParser.normalize_fee_numeric(match)]
        return max(description_numbers) if description_numbers else -1.0

    @staticmethod
    def select_scholarships_for_course(
    scholarships: list[dict],
    *,
    course_level: str,
    course_name: str,
    course_body: str = "",
) -> list[dict]:
        eligible = [item for item in scholarships if isinstance(item, dict) and scholarship_study_level_matches(str(item.get('scholarshipStudyLevel', '') or ''), course_level)]
        if not eligible:
            return []
        haystack = f'{course_name}\n{course_body}'.casefold()
        is_mba_course = bool(re.search('\\bmba\\b', haystack))
        if is_mba_course:
            mba_only = [item for item in eligible if 'mba' in str(item.get('scholarshipName', '') or '').casefold()]
            if mba_only:
                return mba_only
        elif course_level == 'postgraduate':
            eligible = [item for item in eligible if 'mba' not in str(item.get('scholarshipName', '') or '').casefold()]
        return eligible

    @staticmethod
    def scholarship_item_to_parsed(item: dict) -> dict:
        amount_value = parse_scholarship_numeric_amount(item)
        amount = str(int(amount_value)) if amount_value >= 0 else ''
        scholarship_type = str(item.get('scholarshipType', '') or '').strip()
        if scholarship_type.lower() == 'percentage':
            scholarship_type = 'Percentage'
        elif scholarship_type.lower() == 'amount' or amount:
            scholarship_type = 'Amount'
        else:
            scholarship_type = ''
        descriptions: list[str] = []
        for field in ('Eligibility', 'Amount', 'description'):
            value = str(item.get(field, '') or '').strip()
            if value and value not in descriptions:
                descriptions.append(value)
        return {'scholarshipName': str(item.get('scholarshipName', '') or '').strip(), 'scholarshipAmount': amount, 'scholarshipType': scholarship_type, 'scholarshipMetaData': normalize_metadata_array([{'subtitle': 'Scholarships', 'description': descriptions}], default_subtitle='Scholarships')}

    @staticmethod
    def enrich_scholarship_parsed(
    scholarship_json: dict,
    scholarship_content: str,
    *,
    course_name: str,
    course_level: str,
    course_body: str = "",
) -> dict:
        """Pick the highest-value scholarship that matches the course study level."""
        parsed = dict(scholarship_json) if isinstance(scholarship_json, dict) else {}
        data = parse_uni_json_payload(scholarship_content, 'scholarships')
        if not isinstance(data, list):
            return parsed
        eligible = select_scholarships_for_course(data, course_level=course_level, course_name=course_name, course_body=course_body)
        if not eligible:
            return parsed
        best = max(eligible, key=parse_scholarship_numeric_amount)
        deterministic = scholarship_item_to_parsed(best)
        parsed.update(deterministic)
        return parsed

    @staticmethod
    def enrich_entry_parsed(
    entry_json: dict,
    entry_content: str,
    *,
    course_level: str,
    stage1_json: dict,
    course_name: str,
    course_body: str,
) -> dict:
        """Fill entry_requirement_parsed.json AcademicRequirementsMetaData from stage1 + Bangladesh JSON."""
        parsed = dict(entry_json) if isinstance(entry_json, dict) else {}
        course_text = f'{course_name}\n{course_body}'.strip()
        descriptions: list[str] = list(Stage1Enricher.extract_stage1_entry_descriptions(stage1_json))
        seen = set(descriptions)
        for line in extract_bangladesh_json_descriptions(entry_content, course_level, course_text=course_text):
            if line not in seen:
                descriptions.append(line)
                seen.add(line)
        if descriptions:
            parsed['AcademicRequirementsMetaData'] = [{'subtitle': 'Entry Requirements', 'description': descriptions}]
        else:
            parsed['AcademicRequirementsMetaData'] = []
        return parsed

    @staticmethod
    def _requirement_identity(req: dict[str, str]) -> tuple[str, str]:
        return (str(req.get('degree', '') or '').strip().lower(), str(req.get('grade', '') or '').strip().lower())

    @staticmethod
    def merge_requirement_lists(
    *lists: object,
    course_level: str = "",
) -> list[dict[str, str]]:
        merged: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for raw in lists:
            for item in normalize_requirements_list(raw, course_level=course_level):
                key = _requirement_identity(item)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    @staticmethod
    def derive_uk_equivalent_requirements(
    course_body: str,
    course_level: str,
) -> list[dict[str, str]]:
        """Derive an HSC GPA row from UK UCAS / A-Level text on the course page."""
        if course_level not in {'foundation', 'undergraduate'}:
            return []
        grade = derive_hsc_gpa_from_uk_entry_text(course_body)
        if not grade:
            return []
        return [{'degree': 'HSC', 'grade': grade}]

    @staticmethod
    def build_deterministic_row(
    stage1_json: dict,
    *,
    university_name: str,
    course_url: str,
    course_name: str,
    degree_name: str,
) -> dict[str, object]:
        row: dict[str, object] = {col: '' for col in COURSE_CSV_COLUMNS}
        row['uniName'] = university_name
        row['courseName'] = course_name
        row['programmeName'] = course_name
        row['degreeName'] = degree_name
        row['courseUrlExternal'] = course_url
        row['courseScraped'] = course_url
        row['tuitionFee'] = Stage1MarkdownParser.normalize_fee_numeric(str(stage1_json.get('tuitionFee', '') or ''))
        row['currency'] = str(stage1_json.get('currency', '') or '').strip() or 'GBP'
        row['intakeInfo'] = Stage1MarkdownParser.normalize_intake(str(stage1_json.get('intakeInfo', '') or ''))
        row['courseDuration'] = Stage1MarkdownParser.normalize_duration_months(str(stage1_json.get('courseDuration', '') or ''))
        for key in STAGE1_SCALAR_KEYS:
            if key in {'tuitionFee', 'currency', 'intakeInfo', 'courseDuration'}:
                continue
            row[key] = str(stage1_json.get(key, '') or '').strip()
        fees_meta = stage1_json.get('feesMetaData')
        row['feesMetaData'] = normalize_metadata_array(fees_meta) if fees_meta else []
        row['requirements'] = []
        row['AcademicRequirementsMetaData'] = []
        row['scholarshipMetaData'] = []
        row['Result'] = 'ok'
        row['Paste_AI_output'] = ''
        return row

    @staticmethod
    def extract_llm_stage2_fields(
    llm_json: dict,
    *,
    course_level: str = "",
) -> dict[str, object]:
        extracted: dict[str, object] = {}
        for key in LLM_STAGE2_KEYS:
            if key not in llm_json:
                continue
            extracted[key] = llm_json[key]
        extracted['requirements'] = normalize_requirements_list(extracted.get('requirements'), course_level=course_level)
        extracted['AcademicRequirementsMetaData'] = filter_academic_metadata(normalize_metadata_array(extracted.get('AcademicRequirementsMetaData')))
        extracted['scholarshipMetaData'] = normalize_metadata_array(extracted.get('scholarshipMetaData'), default_subtitle='Scholarships')
        extracted['scholarshipName'] = str(extracted.get('scholarshipName', '') or '').strip()
        extracted['scholarshipAmount'] = Stage1MarkdownParser.normalize_fee_numeric(str(extracted.get('scholarshipAmount', '') or ''))
        extracted['scholarshipType'] = str(extracted.get('scholarshipType', '') or '').strip()
        if extracted['scholarshipType'].lower() == 'percentage':
            extracted['scholarshipType'] = 'Percentage'
        elif extracted['scholarshipType'].lower() == 'amount':
            extracted['scholarshipType'] = 'Amount'
        elif extracted['scholarshipType'] and extracted['scholarshipType'] not in ('Amount', 'Percentage'):
            lowered = extracted['scholarshipType'].lower()
            if '%' in lowered or 'percent' in lowered:
                extracted['scholarshipType'] = 'Percentage'
            elif 'amount' in lowered or '£' in extracted['scholarshipType'] or 'off' in lowered:
                extracted['scholarshipType'] = 'Amount'
            else:
                extracted['scholarshipType'] = ''
        return extracted

    @staticmethod
    def format_gbp_deposit(amount: str) -> str:
        digits = re.sub('[^\\d]', '', amount or '')
        if not digits:
            return ''
        return f'£{int(digits):,}'

    @staticmethod
    def extract_explicit_deposit_from_text(*texts: str) -> str:
        for text in texts:
            if not text:
                continue
            for match in EXPLICIT_DEPOSIT_RE.finditer(text):
                amount = match.group(1) or match.group(2)
                if amount:
                    return format_gbp_deposit(amount)
        return ''

    @staticmethod
    def enrich_deposit_parsed(
    deposit_json: dict,
    *,
    course_content: str = "",
    deposit_content: str = "",
) -> dict:
        enriched = dict(deposit_json)
        fees_meta = normalize_metadata_array(enriched.get('feesMetaData'), default_subtitle='Initial tuition Deposit')
        enriched['feesMetaData'] = fees_meta
        meta_text = '\n'.join((line for item in fees_meta for line in item.get('description') or [] if isinstance(line, str)))
        explicit = extract_explicit_deposit_from_text(course_content, deposit_content, meta_text)
        if explicit:
            enriched['initialDeposit'] = explicit
        return enriched

    @staticmethod
    def extract_deposit_stage2_fields(deposit_json: dict) -> dict[str, object]:
        fees_meta = normalize_metadata_array(deposit_json.get('feesMetaData'), default_subtitle='Initial tuition Deposit')
        return {'initialDeposit': str(deposit_json.get('initialDeposit', '') or '').strip(), 'feesMetaData': fees_meta}

    @staticmethod
    def merge_fees_metadata(
    existing: object,
    deposit_meta: list[dict[str, object]],
) -> list[dict[str, object]]:
        merged = normalize_metadata_array(existing)
        if not deposit_meta:
            return merged
        existing_subtitles = {str(item.get('subtitle', '')).strip().lower() for item in merged}
        for item in deposit_meta:
            subtitle = str(item.get('subtitle', '')).strip().lower()
            if subtitle and subtitle in existing_subtitles:
                continue
            merged.append(item)
        return merged

    @staticmethod
    def combine_stage2_llm_parts(
    entry_json: dict,
    english_json: dict,
    scholarship_json: dict,
    deposit_json: dict,
) -> dict[str, object]:
        """Merge the three focused Stage 2 LLM JSON blobs into one LLM field set."""
        metadata: list[dict[str, object]] = []
        metadata.extend(normalize_metadata_array(entry_json.get('AcademicRequirementsMetaData'), default_subtitle='Entry Requirements'))
        metadata.extend(normalize_metadata_array(english_json.get('AcademicRequirementsMetaData'), default_subtitle='English Requirement'))
        combined: dict[str, object] = {'requirements': entry_json.get('requirements', []), 'AcademicRequirementsMetaData': metadata, 'scholarshipName': scholarship_json.get('scholarshipName', ''), 'scholarshipAmount': scholarship_json.get('scholarshipAmount', ''), 'scholarshipType': scholarship_json.get('scholarshipType', ''), 'scholarshipMetaData': normalize_metadata_array(scholarship_json.get('scholarshipMetaData'), default_subtitle='Scholarships')}
        for key in ENGLISH_TEST_KEYS:
            combined[key] = str(english_json.get(key, '') or '').strip()
        deposit_fields = extract_deposit_stage2_fields(deposit_json)
        combined['initialDeposit'] = deposit_fields['initialDeposit']
        combined['feesMetaData'] = deposit_fields['feesMetaData']
        return combined

    @staticmethod
    def run_stage2_llm_part(
    *,
    audit_dir: Path,
    name: str,
    prompt: str,
    model: str | None,
    host: str | None,
) -> dict:
        """Run one Stage 2 sub-prompt and write audit files."""
        ExtractionPathConfig.save_audit(audit_dir, f'{name}_prompt.txt', prompt)
        print(f'  Stage 2 ({name})', flush=True)
        t0 = time.time()
        parsed, raw = chat(prompt, model=model, host=host)
        print(f'    done in {int(time.time() - t0)}s', flush=True)
        ExtractionPathConfig.save_audit(audit_dir, f'{name}_response.json', json.dumps(raw, indent=2))
        ExtractionPathConfig.save_audit(audit_dir, f'{name}_parsed.json', json.dumps(parsed, indent=2, ensure_ascii=False))
        return parsed

    @staticmethod
    def merge_stage2_row(
    deterministic: dict[str, object],
    llm_json: dict,
    *,
    uni_content: str = "",
    entry_content: str = "",
    course_level: str = "",
    course_body: str = "",
) -> dict[str, object]:
        merged = dict(deterministic)
        merged['uniName'] = deterministic['uniName']
        merged['courseUrlExternal'] = deterministic['courseUrlExternal']
        merged['courseName'] = deterministic['courseName']
        merged['programmeName'] = deterministic['programmeName']
        merged['degreeName'] = deterministic['degreeName']
        llm_fields = extract_llm_stage2_fields(llm_json, course_level=course_level)
        for key in LLM_STAGE2_KEYS:
            value = llm_fields.get(key)
            if value in ('', None, []):
                continue
            merged[key] = value
        for key in ENGLISH_TEST_KEYS:
            value = str(llm_json.get(key, '') or '').strip()
            if not value:
                continue
            if key.startswith('ielts'):
                if not str(merged.get(key, '') or '').strip():
                    merged[key] = value
            else:
                merged[key] = value
        deposit_initial = str(llm_json.get('initialDeposit', '') or '').strip()
        if deposit_initial:
            merged['initialDeposit'] = deposit_initial
        deposit_fees = normalize_metadata_array(llm_json.get('feesMetaData'), default_subtitle='Initial tuition Deposit')
        if deposit_fees:
            merged['feesMetaData'] = merge_fees_metadata(merged.get('feesMetaData'), deposit_fees)
        if (entry_content or uni_content) and course_level:
            fallback = normalize_requirements_list(parse_bangladesh_requirements(uni_content, course_level, entry_content=entry_content), course_level=course_level)
            existing = normalize_requirements_list(merged.get('requirements'), course_level=course_level)
            use_fallback = bool(fallback) and (not existing or (course_level == 'postgraduate' and all((item['degree'] in UG_ENTRY_DEGREES for item in existing))))
            if use_fallback:
                merged['requirements'] = fallback
            elif existing:
                merged['requirements'] = merge_requirement_lists(existing, fallback, course_level=course_level)
            elif fallback:
                merged['requirements'] = fallback
        if course_body and course_level:
            merged['requirements'] = merge_requirement_lists(merged.get('requirements', []), derive_uk_equivalent_requirements(course_body, course_level), course_level=course_level)
        return merged

    @staticmethod
    def append_stage1_entry_metadata(row: dict[str, object], stage1_json: dict) -> None:
        stage1_meta = normalize_metadata_array(stage1_json.get('AcademicRequirementsMetaData'))
        if not stage1_meta:
            return
        metadata = normalize_metadata_array(row.get('AcademicRequirementsMetaData'))
        if any((str(item.get('subtitle', '')).strip().lower() == 'entry requirements' for item in metadata)):
            row['AcademicRequirementsMetaData'] = metadata
            return
        for item in stage1_meta:
            if str(item.get('subtitle', '')).strip().lower() == 'entry requirements':
                metadata.insert(0, item)
                break
        row['AcademicRequirementsMetaData'] = metadata

    @staticmethod
    def append_english_requirement_metadata(
    row: dict[str, object],
    stage1_json: dict,
) -> None:
        """Ensure English Requirement metadata exists when Stage 1 has IELTS scores."""
        overall = str(stage1_json.get('ieltsMinOverall', '') or '').strip()
        section = str(stage1_json.get('ieltsMinSection', '') or '').strip()
        if not overall:
            return
        metadata = normalize_metadata_array(row.get('AcademicRequirementsMetaData'))
        english_text = f'IELTS {overall} overall with no element below {section}' if section else f'IELTS {overall} overall'
        for item in metadata:
            if str(item.get('subtitle', '')).strip().lower() == 'english requirement':
                descriptions = item.get('description', [])
                if isinstance(descriptions, list) and descriptions:
                    row['AcademicRequirementsMetaData'] = metadata
                    return
        metadata.append({'subtitle': 'English Requirement', 'description': [english_text]})
        row['AcademicRequirementsMetaData'] = metadata

    @staticmethod
    def normalize_row(row: dict, university_name: str, course_url: str) -> dict:
        normalized = {col: row.get(col, '') for col in COURSE_CSV_COLUMNS}
        for col in COURSE_CSV_COLUMNS:
            if isinstance(normalized[col], (list, dict)):
                continue
            if normalized[col] is None:
                normalized[col] = ''
        requirements = row.get('requirements')
        if requirements in ('', None) and any((row.get(key) for key in ('minDegreeName', 'minGpa', 'higherDegreeName', 'higherGpa'))):
            legacy: list[dict[str, str]] = []
            if row.get('minDegreeName') or row.get('minGpa'):
                legacy.append({'degree': str(row.get('minDegreeName', '') or ''), 'grade': str(row.get('minGpa', '') or '')})
            if row.get('higherDegreeName') or row.get('higherGpa'):
                legacy.append({'degree': str(row.get('higherDegreeName', '') or ''), 'grade': str(row.get('higherGpa', '') or '')})
            requirements = legacy
        if not isinstance(requirements, list):
            requirements = []
        normalized['requirements'] = requirements
        normalized['uniName'] = normalized.get('uniName') or university_name
        normalized['courseUrlExternal'] = normalized.get('courseUrlExternal') or course_url
        normalized['courseScraped'] = normalized.get('courseScraped') or course_url
        if not normalized.get('Paste_AI_output'):
            normalized['Paste_AI_output'] = ''
        return normalized

    @staticmethod
    def infer_course_level(course_name: str, course_url: str, study_level: str = "") -> str:
        if study_level:
            return llm_course_level(study_level)
        text = f'{course_name} {course_url}'.lower()
        if 'foundation' in text:
            return 'foundation'
        if '/postgraduate/' in text or POSTGRADUATE_AWARD_RE.search(course_name):
            return 'postgraduate'
        return 'undergraduate'

class OutputJsonBuilder:
    """Grouped extraction helpers."""

    @staticmethod
    def build_output_json(
    stage1_json: dict,
    llm_json: dict,
    *,
    university_name: str,
    course_name: str,
    course_url: str,
    degree_name: str = "",
    requirements: list[dict[str, str]] | None = None,
    academic_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
        """Merge Stage 1 course fields + Stage 2 LLM parts into extracted/{slug}/output.json."""
        award = (
            (degree_name or "").strip()
            or str(stage1_json.get("degreeName", "") or "").strip()
        )
        output: dict[str, object] = {'uniName': university_name, 'courseName': course_name or str(stage1_json.get('courseName', '') or '').strip(), 'courseUrl': course_url or str(stage1_json.get('courseUrl', '') or stage1_json.get('courseUrlExternal', '') or '').strip(), 'intakeInfo': str(stage1_json.get('intakeInfo', '') or '').strip(), 'courseDuration': str(stage1_json.get('courseDuration', '') or '').strip(), 'tuitionFee': str(stage1_json.get('tuitionFee', '') or '').strip(), 'currency': str(stage1_json.get('currency', '') or '').strip(), 'initialDeposit': str(stage1_json.get('initialDeposit', '') or '').strip(), 'applicationFee': str(stage1_json.get('applicationFee', '') or '').strip(), 'feesMetaData': Stage2Enricher.merge_fees_metadata(Stage2Enricher.normalize_metadata_array(stage1_json.get('feesMetaData')), Stage2Enricher.normalize_metadata_array(llm_json.get('feesMetaData'), default_subtitle='Initial tuition Deposit')), 'applicationDeadline': str(stage1_json.get('applicationDeadline', '') or '').strip(), 'requirements': requirements if requirements is not None else Stage2Enricher.normalize_requirements_list(llm_json.get('requirements')), 'AcademicRequirementsMetaData': Stage2Enricher.filter_academic_metadata(Stage2Enricher.normalize_metadata_array(academic_metadata if academic_metadata is not None else llm_json.get('AcademicRequirementsMetaData'))), 'scholarshipName': str(llm_json.get('scholarshipName', '') or '').strip(), 'scholarshipAmount': Stage1MarkdownParser.normalize_fee_numeric(str(llm_json.get('scholarshipAmount', '') or '')), 'scholarshipType': str(llm_json.get('scholarshipType', '') or '').strip(), 'scholarshipMetaData': Stage2Enricher.normalize_metadata_array(llm_json.get('scholarshipMetaData'), default_subtitle='Scholarships')}
        if award:
            output["degreeName"] = award
        for key in ENGLISH_TEST_KEYS:
            value = str(llm_json.get(key, '') or '').strip()
            if not value:
                value = str(stage1_json.get(key, '') or '').strip()
            output[key] = value
        deposit_initial = str(llm_json.get('initialDeposit', '') or '').strip()
        if deposit_initial:
            output['initialDeposit'] = deposit_initial
        tuition_fee = str(output.get('tuitionFee', '') or '').strip()
        currency = str(output.get('currency', '') or '').strip()
        if tuition_fee and currency:
            output['tuitionFeeCandidates'] = [{'label': 'INTERNATIONAL', 'amount': tuition_fee, 'currency': currency}]
        return output

class CourseExtractor:
    """Grouped extraction helpers."""

    @staticmethod
    def extract_course(
    code_dir: Path,
    course_entry: dict,
    *,
    model: str | None = None,
    host: str | None = None,
    skip_stage1: bool = False,
) -> dict:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        university_name = code_dir.parent.name
        course_url = course_entry.get('course_url') or course_entry.get('courseUrlExternal', '')
        slug = course_slug_from_url(course_url)
        study_level = course_entry.get('study_level') or ''
        extract_root = course_entry.get('extract_root') or None
        audit_dir = extraction_dir(output_dir, slug, study_level, extract_root=extract_root)
        course_path = output_dir / course_entry['clean_md']
        meta, course_body = split_frontmatter(course_path.read_text(encoding='utf-8'))
        course_name = course_entry.get('courseName') or ExtractionPathConfig.infer_course_name(course_body, course_url)
        if not study_level:
            study_level = study_level_from_markdown(course_path, meta, course_url=course_url, course_name=course_name)
            audit_dir = extraction_dir(output_dir, slug, study_level, extract_root=extract_root)
        prompt_1_template = ExtractionPathConfig.load_template(PROMPT_1)
        prompt_2_entry = ExtractionPathConfig.load_template(PROMPT_2_ENTRY)
        prompt_2_english = ExtractionPathConfig.load_template(PROMPT_2_ENGLISH)
        prompt_2_scholarship = ExtractionPathConfig.load_template(PROMPT_2_SCHOLARSHIP)
        prompt_2_initial_deposit = ExtractionPathConfig.load_template(PROMPT_2_INITIAL_DEPOSIT)
        uni_sections = ExtractionPathConfig.load_uni_sections(output_dir)
        uni_content = ExtractionPathConfig.load_uni_content(output_dir)
        course_level = Stage2Enricher.infer_course_level(course_name, course_url, study_level)
        degree_name = (
            course_entry.get('degreeName')
            or ExtractionPathConfig.infer_degree_name_from_md(course_body)
            or ExtractionPathConfig.infer_degree_name(course_name)
        )
        stage1_json_text = ''
        parser_hints = Stage1MarkdownParser.extract_stage1_fields_from_md(course_body)
        ExtractionPathConfig.save_audit(audit_dir, 'parser_hints.json', json.dumps(Stage1Enricher.parser_hints_payload(parser_hints, course_body), indent=2, ensure_ascii=False))
        stage1_path = audit_dir / 'stage1_parsed.json'
        stage1_response_path = audit_dir / 'stage1_response.json'
        stage1_content = ''
        if skip_stage1 and stage1_path.exists():
            stage1_json = json.loads(stage1_path.read_text(encoding='utf-8'))
            stage1_content = ExtractionPathConfig.response_content_from_file(stage1_response_path)
        else:
            stage1_prompt = ExtractionPathConfig.fill_template(prompt_1_template, COURSE_NAME=course_name, COURSE_URL=course_url, INPUT_CONTENT=course_body.strip(), KNOWN_FIELDS=json.dumps(parser_hints, indent=2, ensure_ascii=False))
            ExtractionPathConfig.save_audit(audit_dir, 'stage1_prompt.txt', stage1_prompt)
            print(f'  Stage 1: {course_name}', flush=True)
            t0 = time.time()
            stage1_json, stage1_raw = chat(stage1_prompt, model=model, host=host)
            print(f'    done in {int(time.time() - t0)}s', flush=True)
            stage1_content = ExtractionPathConfig.extract_response_content(stage1_raw)
            ExtractionPathConfig.save_audit(audit_dir, 'stage1_response.json', json.dumps(stage1_raw, indent=2))
        grounding_warnings: list[str] = []
        stage1_json = Stage1Enricher.enrich_stage1_from_markdown(stage1_json, course_body=course_body, course_name=course_name, course_url=course_url, warnings=grounding_warnings)
        if not degree_name and str(stage1_json.get('degreeName', '') or '').strip():
            degree_name = str(stage1_json['degreeName']).strip()
        ExtractionPathConfig.save_audit(audit_dir, 'extraction_warnings.json', json.dumps({'grounding': grounding_warnings}, indent=2, ensure_ascii=False))
        ExtractionPathConfig.save_audit(audit_dir, 'stage1_parsed.json', json.dumps(stage1_json, indent=2))
        stage1_json_text = json.dumps(stage1_json, indent=2, ensure_ascii=False)
        entry_json = Stage2Enricher.run_stage2_llm_part(audit_dir=audit_dir, name='entry_requirement', prompt=ExtractionPathConfig.fill_template(prompt_2_entry, COURSE_NAME=course_name, COURSE_URL=course_url, COURSE_LEVEL=course_level, STAGE1_JSON=stage1_json_text, ENTRY_CONTENT=uni_sections.get('entry', '')), model=model, host=host)
        entry_json = Stage2Enricher.enrich_entry_parsed(entry_json, uni_sections.get('entry', ''), course_level=course_level, stage1_json=stage1_json, course_name=course_name, course_body=course_body)
        ExtractionPathConfig.save_audit(audit_dir, 'entry_requirement_parsed.json', json.dumps(entry_json, indent=2, ensure_ascii=False))
        english_json = Stage2Enricher.run_stage2_llm_part(audit_dir=audit_dir, name='english_requirements', prompt=ExtractionPathConfig.fill_template(prompt_2_english, COURSE_NAME=course_name, COURSE_URL=course_url, COURSE_LEVEL=course_level, STAGE1_JSON=stage1_json_text, ENGLISH_CONTENT=uni_sections.get('english', '')), model=model, host=host)
        english_json = Stage2Enricher.enrich_english_parsed(english_json, uni_sections.get('english', ''), course_name=course_name, course_level=course_level, stage1_json=stage1_json, course_body=course_body)
        ExtractionPathConfig.save_audit(audit_dir, 'english_requirements_parsed.json', json.dumps(english_json, indent=2, ensure_ascii=False))
        scholarship_json = Stage2Enricher.run_stage2_llm_part(audit_dir=audit_dir, name='scholarship', prompt=ExtractionPathConfig.fill_template(prompt_2_scholarship, COURSE_NAME=course_name, COURSE_URL=course_url, STAGE1_JSON=stage1_json_text, SCHOLARSHIP_CONTENT=uni_sections.get('scholarship', '')), model=model, host=host)
        scholarship_json = Stage2Enricher.enrich_scholarship_parsed(scholarship_json, uni_sections.get('scholarship', ''), course_name=course_name, course_level=course_level, course_body=course_body)
        ExtractionPathConfig.save_audit(audit_dir, 'scholarship_parsed.json', json.dumps(scholarship_json, indent=2, ensure_ascii=False))
        tuition_fee = str(stage1_json.get('tuitionFee', '') or '').strip()
        deposit_json = Stage2Enricher.run_stage2_llm_part(audit_dir=audit_dir, name='initial_deposit', prompt=ExtractionPathConfig.fill_template(prompt_2_initial_deposit, COURSE_NAME=course_name, COURSE_URL=course_url, TUITION_FEE=tuition_fee, STAGE1_JSON=stage1_json_text, COURSE_CONTENT=course_body.strip(), DEPOSIT_CONTENT=uni_sections.get('deposit', '')), model=model, host=host)
        deposit_json = Stage2Enricher.enrich_deposit_parsed(deposit_json, course_content=course_body.strip(), deposit_content=uni_sections.get('deposit', ''))
        ExtractionPathConfig.save_audit(audit_dir, 'initial_deposit_parsed.json', json.dumps(deposit_json, indent=2, ensure_ascii=False))
        llm_json = Stage2Enricher.combine_stage2_llm_parts(entry_json, english_json, scholarship_json, deposit_json)
        ExtractionPathConfig.save_audit(audit_dir, 'stage2_llm_parsed.json', json.dumps(llm_json, indent=2, ensure_ascii=False))
        stage2_content = json.dumps(llm_json, ensure_ascii=False)
        deterministic = Stage2Enricher.build_deterministic_row(stage1_json, university_name=university_name, course_url=course_url, course_name=course_name, degree_name=degree_name)
        stage2_json = Stage2Enricher.merge_stage2_row(deterministic, llm_json, uni_content=uni_content, entry_content=uni_sections.get('entry', ''), course_level=course_level, course_body=course_body)
        stage2_json['AcademicRequirementsMetaData'] = Stage2Enricher.finalize_academic_requirements_metadata(stage2_json.get('AcademicRequirementsMetaData'), stage1_json=stage1_json, uni_content=uni_content, english_content=uni_sections.get('english', ''), course_level=course_level, english_scalars={key: llm_json.get(key, '') for key in ENGLISH_TEST_KEYS}, course_name=course_name, course_body=course_body, entry_content=uni_sections.get('entry', ''))
        stage2_json['uniName'] = university_name
        stage2_json['courseUrlExternal'] = course_url
        stage2_json['courseScraped'] = course_url
        ExtractionPathConfig.save_audit(audit_dir, 'stage2_parsed.json', json.dumps(stage2_json, indent=2, default=str))
        output_json = OutputJsonBuilder.build_output_json(stage1_json, llm_json, university_name=university_name, course_name=course_name, course_url=course_url, degree_name=degree_name or str(stage1_json.get('degreeName', '') or '').strip(), requirements=stage2_json.get('requirements'), academic_metadata=stage2_json.get('AcademicRequirementsMetaData'))
        output_json_text = json.dumps(output_json, ensure_ascii=False, default=str)
        ExtractionPathConfig.save_audit(audit_dir, 'output.json', json.dumps(output_json, indent=2, ensure_ascii=False, default=str))
        row = Stage2Enricher.normalize_row(stage2_json, university_name, course_url)
        if course_entry.get('courseName'):
            row['courseName'] = course_entry['courseName']
            row['programmeName'] = course_entry['courseName']
        if course_entry.get('degreeName'):
            row['degreeName'] = course_entry['degreeName']
        row['uniName'] = university_name
        if not row.get('Result'):
            row['Result'] = 'ok'
        row['Paste_AI_output'] = f'extracted/{slug}/stage2_llm_parsed.json'
        return (row, stage1_content, stage2_content, output_json_text)

class LlmExtractCLI:
    """Grouped extraction helpers."""

    @staticmethod
    def run_extraction(
    code_dir: Path,
    *,
    course_index: int | None = None,
    md_file: str | None = None,
    limit: int | None = None,
    resume: bool = False,
    model: str | None = None,
    host: str | None = None,
    skip_stage1: bool = False,
    skip_uni_validation: bool = False,
    study_levels: list[str] | None = None,
    urls: list[str] | None = None,
    presetup: bool = False,
) -> None:
        code_dir = resolve_code_dir(code_dir)
        output_dir = resolve_output_dir(code_dir)
        if not skip_uni_validation:
            from validate_uni_clean import ensure_uni_clean_valid
            ensure_uni_clean_valid(output_dir, university_name=code_dir.parent.name)
        if presetup:
            sample_urls = presetup_sample_urls(load_presetup_sample(output_dir))
            if not sample_urls:
                raise ValueError(f"No {output_dir / 'presetup_sample.json'}. Run --presetup first.")
            courses = CourseIndexManager.entries_from_presetup_clean(output_dir)
            if not courses:
                raise ValueError('No markdown in output/clean/pre_setup_course matches presetup_sample.json. Run --presetup first.')
        else:
            CourseIndexManager.ensure_course_index_synced(code_dir)
            index_rows = CourseIndexManager.read_course_index_csv(output_dir)
            courses = [CourseIndexManager.index_row_to_entry(row) for row in index_rows]
        valid_keys: set[str] = set()
        for entry in courses:
            slug = course_slug_from_url(entry['course_url'])
            valid_keys.add(slug)
            valid_keys.add(extraction_resume_key(entry.get('study_level'), slug))
        progress = ExtractionProgressStore.load_progress(output_dir, presetup=presetup)
        completed = {key for key in progress.get('completed', []) if key in valid_keys}
        failed = [key for key in progress.get('failed', []) if key in valid_keys]
        if completed != set(progress.get('completed', [])) or failed != progress.get('failed', []):
            progress['completed'] = sorted(completed)
            progress['failed'] = failed
            ExtractionProgressStore.save_progress(output_dir, progress, presetup=presetup)
        if md_file:
            md_name = Path(md_file).name
            courses = [entry for entry in courses if entry['md_file'] == md_name or Path(entry['md_file']).name == md_name]
            if not courses:
                raise ValueError(f'md_file not found in {COURSE_INDEX_REL}: {md_name}')
        elif urls:
            wanted = {normalize_url(url) for url in unique_urls(urls)}
            courses = [entry for entry in courses if normalize_url(entry.get('course_url') or '') in wanted]
            if not courses:
                raise ValueError('No indexed courses match the given URL(s). Run clean first.')
        elif study_levels:
            allowed = set(parse_study_levels(study_levels))
            courses = [entry for entry in courses if (entry.get('study_level') or '').strip() in allowed]
            if not courses:
                raise ValueError(f"No indexed courses for study level(s): {', '.join(sorted(allowed))}")
        elif course_index is not None:
            if course_index < 1 or course_index > len(courses):
                raise ValueError(f'course_index must be 1–{len(courses)}')
            courses = [courses[course_index - 1]]
        elif limit is not None:
            courses = courses[:limit]
        if limit is not None and (urls or presetup or study_levels):
            courses = courses[:limit]
        if presetup:
            output_csv = output_dir / 'extracted' / PRESETUP_EXTRACT_SUBDIR / 'extracted_courses.csv'
            index_csv = None
            input_label = f'clean/{PRESETUP_CLEAN_SUBDIR}/'
            output_label = f'extracted/{PRESETUP_EXTRACT_SUBDIR}/'
        else:
            output_csv = CourseIndexManager.extracted_csv_path(output_dir)
            index_csv = CourseIndexManager.course_index_path(output_dir)
            input_label = str(index_csv.relative_to(output_dir))
            output_label = str(output_csv.relative_to(output_dir))
        print(f'University: {code_dir.parent.name}', flush=True)
        print(f'Input: {input_label}', flush=True)
        print(f'Courses to process: {len(courses)}', flush=True)
        print(f'Output: {output_label}', flush=True)
        skip_batch = 0
        for index, entry in enumerate(courses, start=1):
            slug = course_slug_from_url(entry['course_url'])
            resume_key = extraction_resume_key(entry.get('study_level'), slug)
            if resume and is_resume_completed(completed, study_level=entry.get('study_level'), slug=slug):
                skip_batch += 1
                continue
            if skip_batch:
                print(f'Resume: skipped {skip_batch} already-completed course(s)', flush=True)
                skip_batch = 0
            print(f"[{index}/{len(courses)}] {entry['md_file']} — {entry['course_url']}", flush=True)
            try:
                row, stage1_output, stage2_output, output_json = CourseExtractor.extract_course(code_dir, entry, model=model, host=host, skip_stage1=skip_stage1)
                CourseIndexManager.append_csv_row(output_csv, row)
                if not presetup:
                    CourseIndexManager.update_course_index_outputs(output_dir, md_file=entry['md_file'], stage1_output=stage1_output, stage2_output=stage2_output, output_json=output_json)
                completed.add(resume_key)
                progress['completed'] = sorted(completed)
                ExtractionProgressStore.save_progress(output_dir, progress, presetup=presetup)
                print(f'  -> appended to {output_csv.name}', flush=True)
                if index_csv is not None:
                    print(f'  -> updated {index_csv.name} (stage1_output, stage2_output, output_json)', flush=True)
            except Exception as exc:
                print(f'  ERROR: {exc}', file=sys.stderr, flush=True)
                failed = progress.setdefault('failed', [])
                if resume_key not in failed and slug not in failed:
                    failed.append(resume_key)
                ExtractionProgressStore.save_progress(output_dir, progress, presetup=presetup)
                raise

    @staticmethod
    def main(code_dir: Path | None = None) -> int:
        parser = argparse.ArgumentParser(description='Extract Course.csv rows using Ollama (Stage 1 + Stage 2).')
        parser.add_argument('university_dir', nargs='?', default=DEFAULT_UNIVERSITY, help='University code/ folder (default: current working directory)')
        parser.add_argument('--course-index', type=int, help='Process one course by index (1-based)')
        parser.add_argument('--md-file', help='Process one course by md filename (e.g. courses-accounting-and-finance-bsc-hons-2026-27.md)')
        parser.add_argument('--build-index', action='store_true', help=f'Build {COURSE_INDEX_REL} from clean/courses/*.md')
        parser.add_argument('--limit', type=int, help='Process first N courses')
        parser.add_argument('--resume', action='store_true', help='Skip courses already in progress file')
        parser.add_argument('--model', default=None, help='Ollama model (default: llama3.1:8b)')
        parser.add_argument('--host', default=None, help='Ollama host (default: http://localhost:11434)')
        parser.add_argument('--skip-stage1', action='store_true', help='Reuse existing extracted/{slug}/stage1_parsed.json')
        parser.add_argument('--skip-uni-validation', action='store_true', help='Skip output/clean/uni validation gate before LLM extraction')
        parser.add_argument('--study-level', action='append', default=[], metavar='LEVEL', help='Restrict to a study level (repeatable)')
        parser.add_argument('--url', action='append', default=[], metavar='URL', help='Process only this course URL (repeatable)')
        parser.add_argument('--presetup', action='store_true', help='Extract presetup_sample.json courses from clean/pre_setup_course into extracted/pre_setup_course_extracted')
        args = parser.parse_args()
        try:
            code_dir = ExtractionPathConfig.configure_code_dir(Path(code_dir) if code_dir is not None else Path(args.university_dir))
            if args.build_index:
                CourseIndexManager.build_course_index(code_dir)
                return 0
            run_extraction(code_dir, course_index=args.course_index, md_file=args.md_file, limit=args.limit, resume=args.resume, model=args.model, host=args.host, skip_stage1=args.skip_stage1, skip_uni_validation=args.skip_uni_validation, study_levels=args.study_level or None, urls=args.url or None, presetup=args.presetup)
        except Exception as exc:
            print(f'Error: {exc}', file=sys.stderr)
            return 1
        return 0


# Backward-compatible module-level aliases

resolve_prompt_path = ExtractionPathConfig.resolve_prompt_path
configure_code_dir = ExtractionPathConfig.configure_code_dir
get_output_dir = ExtractionPathConfig.get_output_dir
get_code_dir = ExtractionPathConfig.get_code_dir
utc_now = ExtractionPathConfig.utc_now
load_template = ExtractionPathConfig.load_template
fill_template = ExtractionPathConfig.fill_template
infer_course_name = ExtractionPathConfig.infer_course_name
load_uni_section = ExtractionPathConfig.load_uni_section
load_uni_content = ExtractionPathConfig.load_uni_content
load_uni_sections = ExtractionPathConfig.load_uni_sections
infer_degree_name = ExtractionPathConfig.infer_degree_name
infer_degree_name_from_md = ExtractionPathConfig.infer_degree_name_from_md
normalize_award_label = ExtractionPathConfig.normalize_award_label
extract_response_content = ExtractionPathConfig.extract_response_content
response_content_from_file = ExtractionPathConfig.response_content_from_file
stage_response_paths = ExtractionPathConfig.stage_response_paths
load_json_file_compact = ExtractionPathConfig.load_json_file_compact
detect_stage_outputs = ExtractionPathConfig.detect_stage_outputs
extract_artifact_relpaths = ExtractionPathConfig.extract_artifact_relpaths
save_audit = ExtractionPathConfig.save_audit
extract_international_fees_section = Stage1MarkdownParser.extract_international_fees_section
parse_international_fee_options = Stage1MarkdownParser.parse_international_fee_options
pick_primary_fee_option = Stage1MarkdownParser.pick_primary_fee_option
normalize_short_month_date = Stage1MarkdownParser.normalize_short_month_date
normalize_intake_text = Stage1MarkdownParser.normalize_intake_text
extract_aru_international_tuition_fee = Stage1MarkdownParser.extract_aru_international_tuition_fee
extract_international_fee_from_fees_metadata_dict = Stage1MarkdownParser.extract_international_fee_from_fees_metadata_dict
fees_metadata_object_to_array = Stage1MarkdownParser.fees_metadata_object_to_array
coalesce_stage1_fields_from_fees_metadata = Stage1MarkdownParser.coalesce_stage1_fields_from_fees_metadata
extract_stage1_fields_from_md = Stage1MarkdownParser.extract_stage1_fields_from_md
extract_expected_from_md = Stage1MarkdownParser.extract_expected_from_md
normalize_duration_months = Stage1MarkdownParser.normalize_duration_months
normalize_intake = Stage1MarkdownParser.normalize_intake
normalize_fee_numeric = Stage1MarkdownParser.normalize_fee_numeric
fee_amount_in_markdown = Stage1MarkdownParser.fee_amount_in_markdown
attach_extract_artifacts = CourseIndexManager.attach_extract_artifacts
write_course_index = CourseIndexManager.write_course_index
update_course_index_outputs = CourseIndexManager.update_course_index_outputs
course_index_path = CourseIndexManager.course_index_path
extracted_csv_path = CourseIndexManager.extracted_csv_path
read_tab_csv = CourseIndexManager.read_tab_csv
read_course_index_csv = CourseIndexManager.read_course_index_csv
index_row_to_entry = CourseIndexManager.index_row_to_entry
normalize_course_name_key = CourseIndexManager.normalize_course_name_key
canonical_md_priority = CourseIndexManager.canonical_md_priority
group_course_md_paths = CourseIndexManager.group_course_md_paths
pick_canonical_md_path = CourseIndexManager.pick_canonical_md_path
select_canonical_course_md_paths = CourseIndexManager.select_canonical_course_md_paths
expected_canonical_md_names = CourseIndexManager.expected_canonical_md_names
dedupe_course_index_rows = CourseIndexManager.dedupe_course_index_rows
build_course_index = CourseIndexManager.build_course_index
course_index_is_stale = CourseIndexManager.course_index_is_stale
ensure_course_index_synced = CourseIndexManager.ensure_course_index_synced
load_manifest = CourseIndexManager.load_manifest
entries_from_presetup_clean = CourseIndexManager.entries_from_presetup_clean
ensure_csv_header = CourseIndexManager.ensure_csv_header
serialize_csv_value = CourseIndexManager.serialize_csv_value
append_csv_row = CourseIndexManager.append_csv_row
extraction_progress_path = ExtractionProgressStore.extraction_progress_path
load_progress = ExtractionProgressStore.load_progress
save_progress = ExtractionProgressStore.save_progress
filter_stage1_entry_description = Stage1Enricher.filter_stage1_entry_description
extract_stage1_entry_descriptions = Stage1Enricher.extract_stage1_entry_descriptions
normalize_description_list = Stage1Enricher.normalize_description_list
extract_uk_offer_grades = Stage1Enricher.extract_uk_offer_grades
filter_bangladesh_descriptions_for_course = Stage1Enricher.filter_bangladesh_descriptions_for_course
extract_entry_lines_from_course_markdown = Stage1Enricher.extract_entry_lines_from_course_markdown
assert_grounded = Stage1Enricher.assert_grounded
parser_hints_payload = Stage1Enricher.parser_hints_payload
drop_ungrounded_stage1_scalars = Stage1Enricher.drop_ungrounded_stage1_scalars
apply_parser_owned_stage1_fields = Stage1Enricher.apply_parser_owned_stage1_fields
enrich_stage1_from_markdown = Stage1Enricher.enrich_stage1_from_markdown
patch_fees_metadata_international_fee = Stage1Enricher.patch_fees_metadata_international_fee
canonicalize_requirement_degree = Stage2Enricher.canonicalize_requirement_degree
extract_grade_from_requirement_text = Stage2Enricher.extract_grade_from_requirement_text
extract_bangladesh_section_text = Stage2Enricher.extract_bangladesh_section_text
parse_bangladesh_bullet_requirements = Stage2Enricher.parse_bangladesh_bullet_requirements
normalize_requirements_list = Stage2Enricher.normalize_requirements_list
normalize_metadata_array = Stage2Enricher.normalize_metadata_array
filter_academic_metadata = Stage2Enricher.filter_academic_metadata
score_english_program = Stage2Enricher.score_english_program
select_english_json_program = Stage2Enricher.select_english_json_program
extract_bangladesh_json_descriptions = Stage2Enricher.extract_bangladesh_json_descriptions
extract_english_json_descriptions = Stage2Enricher.extract_english_json_descriptions
finalize_academic_requirements_metadata = Stage2Enricher.finalize_academic_requirements_metadata
parse_bangladesh_json_requirements = Stage2Enricher.parse_bangladesh_json_requirements
parse_bangladesh_requirements = Stage2Enricher.parse_bangladesh_requirements
select_english_row_label = Stage2Enricher.select_english_row_label
parse_english_test_scores = Stage2Enricher.parse_english_test_scores
enrich_english_parsed = Stage2Enricher.enrich_english_parsed
scholarship_study_level_matches = Stage2Enricher.scholarship_study_level_matches
parse_scholarship_numeric_amount = Stage2Enricher.parse_scholarship_numeric_amount
select_scholarships_for_course = Stage2Enricher.select_scholarships_for_course
scholarship_item_to_parsed = Stage2Enricher.scholarship_item_to_parsed
enrich_scholarship_parsed = Stage2Enricher.enrich_scholarship_parsed
enrich_entry_parsed = Stage2Enricher.enrich_entry_parsed
_requirement_identity = Stage2Enricher._requirement_identity
merge_requirement_lists = Stage2Enricher.merge_requirement_lists
derive_uk_equivalent_requirements = Stage2Enricher.derive_uk_equivalent_requirements
build_deterministic_row = Stage2Enricher.build_deterministic_row
extract_llm_stage2_fields = Stage2Enricher.extract_llm_stage2_fields
format_gbp_deposit = Stage2Enricher.format_gbp_deposit
extract_explicit_deposit_from_text = Stage2Enricher.extract_explicit_deposit_from_text
enrich_deposit_parsed = Stage2Enricher.enrich_deposit_parsed
extract_deposit_stage2_fields = Stage2Enricher.extract_deposit_stage2_fields
merge_fees_metadata = Stage2Enricher.merge_fees_metadata
combine_stage2_llm_parts = Stage2Enricher.combine_stage2_llm_parts
run_stage2_llm_part = Stage2Enricher.run_stage2_llm_part
merge_stage2_row = Stage2Enricher.merge_stage2_row
append_stage1_entry_metadata = Stage2Enricher.append_stage1_entry_metadata
append_english_requirement_metadata = Stage2Enricher.append_english_requirement_metadata
normalize_row = Stage2Enricher.normalize_row
infer_course_level = Stage2Enricher.infer_course_level
build_output_json = OutputJsonBuilder.build_output_json
extract_course = CourseExtractor.extract_course
run_extraction = LlmExtractCLI.run_extraction
main = LlmExtractCLI.main

configure_code_dir(Path.cwd())


if __name__ == "__main__":
    raise SystemExit(main())
