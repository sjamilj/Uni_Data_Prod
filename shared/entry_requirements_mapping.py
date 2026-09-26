"""Course entry patterns: IELTS resolution and Bangladesh UCAS/class maps."""

from __future__ import annotations

import re
from typing import Any

from course_markdown_cleanup import parse_uni_json_payload

_IELTS_STRICT = re.compile(
    r"IELTS\s+([\d.]+)\s+with\s+a\s+minimum\s+of\s+"
    r"([\d.;,\s\w]+?)(?:\(or recognised equivalent\)\.?)?",
    re.I,
)
_IELTS_ALL_COMPONENTS = re.compile(
    r"IELTS\s+([\d.]+)\s+with\s+a\s+minimum\s+of\s+([\d.]+)\s+in\s+each\s+component",
    re.I,
)
_IELTS_LOOSE = re.compile(r"IELTS\s+([\d.]+)", re.I)

_UCAS_STANDARD = re.compile(
    r"(\d+)\s*UCAS\s*points?\s*\(standard\s*offer\)",
    re.I,
)
_UCAS_CONTEXTUAL = re.compile(
    r"(\d+)\s*UCAS\s*points?\s*\(contextual\s*offer\)",
    re.I,
)
_UCAS_FOUNDATION = re.compile(
    r"(\d+)\s*UCAS\s*points?\s+from\s+an\s+equivalent\s+Level\s+3",
    re.I,
)

_ENGLISH_LEVEL_ALIASES = {
    "foundation": ("foundation",),
    "undergraduate": ("undergraduate",),
    "postgraduate": ("postgraduate",),
}

_UCAS_GPA_RE = re.compile(
    r"GPA\s+([\d.]+)\s*\(\s*(\d+)\s*UCAS\s*\)",
    re.I,
)


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _format_ielts_band(value: str | float) -> str:
    text = str(value).strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return f"{number:.1f}"


def parse_ielts_bands(ielts_text: str) -> tuple[str, str]:
    """Return (overall, min_section) best-effort from an IELTS sentence."""
    text = _normalize_ws(ielts_text)
    if not text:
        return "", ""

    no_component = re.search(
        r"IELTS\s+([\d.]+).*?(?:no component below|minimum of)\s+([\d.]+)",
        text,
        re.I,
    )
    m = _IELTS_ALL_COMPONENTS.search(text)
    if m:
        return _format_ielts_band(m.group(1)), _format_ielts_band(m.group(2))

    overall_match = _IELTS_LOOSE.search(text)
    if not overall_match:
        return "", ""
    overall = _format_ielts_band(overall_match.group(1))
    nums = [_format_ielts_band(n) for n in re.findall(r"\d+\.\d+|\d+", text)]
    section_nums = nums[1:]
    if no_component and "no component below" in text.lower():
        return overall, _format_ielts_band(no_component.group(2))
    if not section_nums:
        return overall, ""
    if "each component" in text.lower() or len(set(section_nums)) == 1:
        return overall, section_nums[0]
    values = [float(n) for n in section_nums]
    return overall, _format_ielts_band(min(values))


def extract_ielts_from_course_markdown(
    markdown: str,
    *,
    entry_block: str = "",
) -> str:
    """IELTS from course markdown; prefer English Language section in entry block."""
    entry = entry_block or ""
    if not entry and markdown:
        m = re.search(
            r"### English Language requirements\s*\n(.*?)(?=\n### |\n## |\Z)",
            markdown,
            re.M | re.S | re.I,
        )
        if m:
            entry = m.group(1)

    for blob in (entry, markdown):
        if not blob:
            continue
        for line in blob.splitlines():
            line = line.strip().lstrip("-").strip()
            if not re.search(r"\bIELTS\b", line, re.I):
                continue
            if re.search(r"\d", line):
                return _normalize_ws(line)
        m = _IELTS_STRICT.search(blob)
        if m:
            return _normalize_ws(m.group(0))
        m = _IELTS_ALL_COMPONENTS.search(blob)
        if m:
            return _normalize_ws(m.group(0))
    return ""


def _ielts_sentence_from_program(program: dict[str, Any]) -> str:
    overall = ""
    section = ""
    for test in program.get("TestRequirements") or []:
        if not isinstance(test, dict):
            continue
        name = str(test.get("TestName", "") or "").lower()
        if "ielts" not in name:
            continue
        overall = str(test.get("ieltsMinOverall", "") or "").strip()
        section = str(test.get("ieltsMinSection", "") or "").strip()
        break
    descriptions = program.get("description") or []
    for line in descriptions:
        text = str(line).strip()
        if re.search(r"\bIELTS\b", text, re.I):
            return _normalize_ws(text)
    if overall and section:
        if overall == section:
            return (
                f"IELTS {overall} overall with a minimum of {section} "
                "in each component (or recognised equivalent)."
            )
        return (
            f"IELTS {overall} overall with a minimum of {section} "
            "(or recognised equivalent)."
        )
    if overall:
        return f"IELTS {overall} overall (or recognised equivalent)."
    return ""


def _study_level_program(programs: list[dict], study_level: str) -> dict | None:
    aliases = _ENGLISH_LEVEL_ALIASES.get(study_level, (study_level,))
    for item in programs:
        if not isinstance(item, dict):
            continue
        level = str(item.get("TestStudyLevel", "") or "").strip().lower()
        if level in aliases:
            return item
    return None


def _program_by_ielts_band(programs: list[dict], overall: str, section: str) -> dict | None:
    target_overall = overall.strip()
    target_section = section.strip()
    for item in programs:
        if not isinstance(item, dict):
            continue
        name = str(item.get("ProgramName", "") or "")
        if not re.search(r"IELTS", name, re.I):
            continue
        if target_overall and target_overall not in name:
            continue
        if target_section and target_section not in name:
            continue
        return item
    for item in programs:
        if not isinstance(item, dict):
            continue
        for test in item.get("TestRequirements") or []:
            if not isinstance(test, dict):
                continue
            if "ielts" not in str(test.get("TestName", "") or "").lower():
                continue
            if str(test.get("ieltsMinOverall", "") or "").strip() == target_overall:
                if not target_section or str(test.get("ieltsMinSection", "") or "").strip() == target_section:
                    return item
    return None


def resolve_ielts_for_course(
    *,
    course_markdown: str,
    study_level: str,
    english_requirements_content: str,
    entry_block: str = "",
) -> dict[str, str]:
    """
    Priority: course .md IELTS → english-requirements.md by band match → study level default.
    """
    from_course = extract_ielts_from_course_markdown(
        course_markdown,
        entry_block=entry_block,
    )
    programs = parse_uni_json_payload(english_requirements_content, "english-requirements")
    if not isinstance(programs, list):
        programs = []

    if from_course:
        overall, section = parse_ielts_bands(from_course)
        program = _program_by_ielts_band(programs, overall, section)
        return {
            "ielts": from_course,
            "ielts_source": "course_markdown",
            "ielts_overall": overall,
            "ielts_min_section": section,
            "ielts_program_name": str((program or {}).get("ProgramName", "") or ""),
        }

    level_program = _study_level_program(programs, study_level)
    sentence = _ielts_sentence_from_program(level_program or {})
    overall, section = parse_ielts_bands(sentence)
    if level_program and sentence:
        return {
            "ielts": sentence,
            "ielts_source": "english_requirements_study_level",
            "ielts_overall": overall,
            "ielts_min_section": section,
            "ielts_program_name": str(level_program.get("ProgramName", "") or ""),
        }

    return {
        "ielts": "",
        "ielts_source": "",
        "ielts_overall": "",
        "ielts_min_section": "",
        "ielts_program_name": "",
    }


_ENTRY_UG = re.compile(
    r"^## Entry requirements\s*-\s*Degree \(including contextual offer\)\s*\n"
    r"(.*?)(?=\n## |\Z)",
    re.M | re.S,
)
_ENTRY_FOUNDATION = re.compile(
    r"^## Entry requirements\s*-\s*Degree with foundation year\s*\n"
    r"(.*?)(?=\n## |\Z)",
    re.M | re.S,
)
_ENTRY_PG = re.compile(
    r"^## Entry requirements\s*\n(.*?)(?=\n## |\Z)",
    re.M | re.S,
)
_ENTRY_FALLBACK = re.compile(
    r"^## Entry requirements[^\n]*\n(.*?)(?=\n## |\Z)",
    re.M | re.S,
)

_PG_DEGREE_ALIASES = {
    "BA": ("BA",),
    "BSc": ("BSc",),
    "BEng": ("BEng",),
    "BBA": ("BBA",),
    "MA": ("MA", "BA"),
    "MSc": ("MSc", "BSc"),
    "MBA": ("MBA",),
    "LLM": ("BA", "LLB"),
    "MEng": ("BEng",),
}


def extract_entry_block(text: str, study_level: str) -> str:
    if study_level == "undergraduate":
        match = _ENTRY_UG.search(text) or _ENTRY_FALLBACK.search(text)
    elif study_level == "foundation":
        match = _ENTRY_FOUNDATION.search(text) or _ENTRY_FALLBACK.search(text)
    else:
        match = _ENTRY_PG.search(text) or _ENTRY_FALLBACK.search(text)
    return (match.group(1).strip() if match else "").strip()


def _scalars_from_program(program: dict[str, Any] | None) -> dict[str, str]:
    out = {
        "ieltsMinOverall": "",
        "ieltsMinSection": "",
        "toeflMinOverall": "",
        "toeflMinSection": "",
        "pteMinOverall": "",
        "pteMinSection": "",
    }
    if not program:
        return out
    for test in program.get("TestRequirements") or []:
        if not isinstance(test, dict):
            continue
        name = str(test.get("TestName", "") or "").lower()
        if "ielts" in name:
            out["ieltsMinOverall"] = str(test.get("ieltsMinOverall", "") or "").strip()
            out["ieltsMinSection"] = str(test.get("ieltsMinSection", "") or "").strip()
        elif "toefl" in name:
            out["toeflMinOverall"] = str(test.get("toeflMinOverall", "") or "").strip()
            out["toeflMinSection"] = str(test.get("toeflMinSection", "") or "").strip()
        elif "pearson" in name or "pte" in name:
            out["pteMinOverall"] = str(test.get("pteMinOverall", "") or "").strip()
            out["pteMinSection"] = str(test.get("pteMinSection", "") or "").strip()
    return out


def _closest_named_ielts_program(
    programs: list[dict],
    overall: str,
    section: str,
) -> dict | None:
    try:
        overall_n = float(overall) if overall else None
        section_n = float(section) if section else None
    except ValueError:
        return None
    if overall_n is None:
        return None
    best: tuple[float, dict] | None = None
    for item in programs:
        if not isinstance(item, dict):
            continue
        name = str(item.get("ProgramName", "") or "")
        if not re.search(r"IELTS", name, re.I):
            continue
        if item.get("TestStudyLevel"):
            continue
        scalars = _scalars_from_program(item)
        try:
            prog_overall = float(scalars["ieltsMinOverall"] or "0")
            prog_section = float(scalars["ieltsMinSection"] or prog_overall)
        except ValueError:
            continue
        distance = abs(prog_overall - overall_n)
        if section_n is not None:
            distance += abs(prog_section - section_n) * 0.5
        if best is None or distance < best[0]:
            best = (distance, item)
    return best[1] if best else None


def resolve_english_tests_for_course(
    *,
    course_markdown: str,
    study_level: str,
    english_requirements_content: str,
    entry_block: str = "",
) -> dict[str, str]:
    """Course .md IELTS first; then english-requirements.md band or study-level tests."""
    ielts_info = resolve_ielts_for_course(
        course_markdown=course_markdown,
        study_level=study_level,
        english_requirements_content=english_requirements_content,
        entry_block=entry_block,
    )
    programs = parse_uni_json_payload(english_requirements_content, "english-requirements")
    if not isinstance(programs, list):
        programs = []

    level_program = _study_level_program(programs, study_level)
    program = None
    if ielts_info.get("ielts_source") == "course_markdown":
        program = _program_by_ielts_band(
            programs,
            ielts_info.get("ielts_overall", ""),
            ielts_info.get("ielts_min_section", ""),
        )
        if program is None and level_program:
            level_scalars = _scalars_from_program(level_program)
            if (
                level_scalars["ieltsMinOverall"] == ielts_info.get("ielts_overall")
                or not ielts_info.get("ielts_overall")
            ):
                program = level_program
        if program is None:
            program = _closest_named_ielts_program(
                programs,
                ielts_info.get("ielts_overall", ""),
                ielts_info.get("ielts_min_section", ""),
            )
        if program is None:
            program = level_program
    else:
        program = level_program

    scalars = _scalars_from_program(program)
    if ielts_info.get("ielts_overall"):
        scalars["ieltsMinOverall"] = ielts_info["ielts_overall"]
    if ielts_info.get("ielts_min_section"):
        scalars["ieltsMinSection"] = ielts_info["ielts_min_section"]
    elif scalars.get("ieltsMinSection"):
        scalars["ieltsMinSection"] = _format_ielts_band(scalars["ieltsMinSection"])

    description = ielts_info.get("ielts") or _ielts_sentence_from_program(program or {})
    return {
        **scalars,
        "ielts": description,
        "english_description": description,
        "ielts_source": ielts_info.get("ielts_source", ""),
        "ielts_overall": scalars.get("ieltsMinOverall", ""),
        "ielts_min_section": scalars.get("ieltsMinSection", ""),
        "ielts_program_name": str((program or {}).get("ProgramName", "") or ""),
    }


def build_stage1_mapping_hints(
    *,
    course_body: str,
    course_level: str,
    entry_content: str = "",
    english_content: str = "",
    degree_name: str = "",
) -> dict:
    entry_block = extract_entry_block(course_body, course_level)
    english = resolve_english_tests_for_course(
        course_markdown=course_body,
        study_level=course_level,
        english_requirements_content=english_content,
        entry_block=entry_block,
    )
    requirements = bangladesh_hsc_requirements_for_llm(
        study_level=course_level,
        course_body=course_body,
        entry_content=entry_content,
        entry_block=entry_block,
        degree_name=degree_name,
    )
    ucas = ucas_points_from_entry(course_level, entry_block)
    postgraduate_class = (
        classify_postgraduate(entry_block or course_body)
        if course_level == "postgraduate"
        else ""
    )
    return {
        "ieltsMinOverall": english.get("ieltsMinOverall", ""),
        "ieltsMinSection": english.get("ieltsMinSection", ""),
        "toeflMinOverall": english.get("toeflMinOverall", ""),
        "toeflMinSection": english.get("toeflMinSection", ""),
        "pteMinOverall": english.get("pteMinOverall", ""),
        "pteMinSection": english.get("pteMinSection", ""),
        "ielts": english.get("ielts", ""),
        "english_description": english.get("english_description", ""),
        "ielts_source": english.get("ielts_source", ""),
        "ielts_program_name": english.get("ielts_program_name", ""),
        "requirements": requirements,
        "ucas_standard": ucas.get("ucas_standard", ""),
        "ucas_contextual": ucas.get("ucas_contextual", ""),
        "ucas_foundation": ucas.get("ucas_foundation", ""),
        "postgraduate_class": postgraduate_class,
    }


def pg_degrees_for_award(degree_name: str) -> list[str]:
    award = (degree_name or "").strip()
    if not award:
        return ["BA", "BSc", "MA", "MSc"]
    return list(_PG_DEGREE_ALIASES.get(award, (award,)))


def load_bangladesh_ucas_maps(bangladesh_content: str) -> dict[str, dict[int, str]]:
    """Parse UCAS → HSC GPA maps from bangladesh-entry JSON embedded in markdown."""
    data = parse_uni_json_payload(bangladesh_content, "bangladesh-entry")
    maps: dict[str, dict[int, str]] = {
        "foundation": {},
        "undergraduate": {},
    }
    if not isinstance(data, dict):
        return maps

    for level in data.get("studyLevels") or []:
        if not isinstance(level, dict):
            continue
        study = str(level.get("studyLevel", "") or "").strip().lower()
        if study not in maps:
            continue
        for program in level.get("programs") or []:
            if not isinstance(program, dict):
                continue
            for line in program.get("description") or []:
                for gpa, ucas in _UCAS_GPA_RE.findall(str(line)):
                    maps[study][int(ucas)] = gpa
    return maps


def load_postgraduate_cgpa_map(bangladesh_content: str) -> dict[str, str]:
    """UK class label → Bangladesh CGPA from bangladesh-entry requirements."""
    data = parse_uni_json_payload(bangladesh_content, "bangladesh-entry")
    mapping = {"2:2": "2.75", "2:1": "3.00"}
    if not isinstance(data, dict):
        return mapping

    grades: set[str] = set()
    for level in data.get("studyLevels") or []:
        if not isinstance(level, dict):
            continue
        if str(level.get("studyLevel", "") or "").strip().lower() != "postgraduate":
            continue
        for program in level.get("programs") or []:
            if not isinstance(program, dict):
                continue
            for req in program.get("requirements") or []:
                if isinstance(req, dict):
                    grade = str(req.get("grade", "") or "").strip()
                    if grade:
                        grades.add(grade)
    if "2.75" in grades:
        mapping["2:2"] = "2.75"
    if "3.00" in grades:
        mapping["2:1"] = "3.00"
    return mapping


def ucas_points_from_entry(
    study_level: str,
    entry_block: str,
    *,
    ucas_standard: str = "",
    ucas_contextual: str = "",
    ucas_foundation: str = "",
) -> dict[str, str]:
    entry = entry_block or ""
    out = {
        "ucas_standard": ucas_standard,
        "ucas_contextual": ucas_contextual,
        "ucas_foundation": ucas_foundation,
    }
    if study_level == "undergraduate":
        if not out["ucas_standard"]:
            m = _UCAS_STANDARD.search(entry)
            if m:
                out["ucas_standard"] = m.group(1)
        if not out["ucas_contextual"]:
            m = _UCAS_CONTEXTUAL.search(entry)
            if m:
                out["ucas_contextual"] = m.group(1)
    elif study_level == "foundation":
        if not out["ucas_foundation"]:
            m = _UCAS_FOUNDATION.search(entry)
            if m:
                out["ucas_foundation"] = m.group(1)
            else:
                m = re.search(r"^(\d+)\s*UCAS\s*points?", entry, re.I | re.M)
                if m:
                    out["ucas_foundation"] = m.group(1)
    return out


def map_ucas_to_hsc_gpa(
    ucas_points: str | int,
    *,
    study_level: str,
    bangladesh_content: str,
) -> str:
    if not ucas_points:
        return ""
    points = int(ucas_points)
    maps = load_bangladesh_ucas_maps(bangladesh_content)
    key = "foundation" if study_level == "foundation" else "undergraduate"
    return maps.get(key, {}).get(points, "")


def map_postgraduate_class_to_cgpa(
    uk_class: str,
    *,
    bangladesh_content: str,
) -> str:
    if not uk_class:
        return ""
    pg_map = load_postgraduate_cgpa_map(bangladesh_content)
    if uk_class in ("2:2", "2:1_or_2:2"):
        return pg_map.get("2:2", "")
    if uk_class == "2:1":
        return pg_map.get("2:1", "")
    if uk_class == "2:1_or_2:2":
        return f"{pg_map.get('2:2', '')}/{pg_map.get('2:1', '')}".strip("/")
    return ""


def bangladesh_requirements_from_course(
    *,
    study_level: str,
    entry_block: str,
    course_markdown: str,
    bangladesh_content: str,
    postgraduate_class: str = "",
    degree_name: str = "",
) -> list[dict[str, str]]:
    """HSC/CGPA requirement rows from course entry + bangladesh-entry maps."""
    ucas = ucas_points_from_entry(study_level, entry_block)
    rows: list[dict[str, str]] = []

    if study_level == "undergraduate":
        for label, points in (
            ("standard", ucas["ucas_standard"]),
            ("contextual", ucas["ucas_contextual"]),
        ):
            if not points:
                continue
            gpa = map_ucas_to_hsc_gpa(points, study_level=study_level, bangladesh_content=bangladesh_content)
            if gpa:
                rows.append({"degree": "HSC", "grade": gpa, "ucas_points": points, "offer": label})
    elif study_level == "foundation":
        points = ucas["ucas_foundation"]
        if points:
            gpa = map_ucas_to_hsc_gpa(points, study_level=study_level, bangladesh_content=bangladesh_content)
            if gpa:
                rows.append({"degree": "HSC", "grade": gpa, "ucas_points": points, "offer": "foundation"})

    if study_level == "postgraduate" and postgraduate_class:
        pg_map = load_postgraduate_cgpa_map(bangladesh_content)
        classes = [postgraduate_class]
        if postgraduate_class == "2:1_or_2:2":
            classes = ["2:2", "2:1"]
        degrees = pg_degrees_for_award(degree_name)
        for uk_class in classes:
            cgpa = pg_map.get(uk_class, "")
            if not cgpa:
                continue
            for degree in degrees:
                rows.append(
                    {
                        "degree": degree,
                        "grade": cgpa,
                        "uk_class": uk_class,
                    }
                )

    return rows


def classify_postgraduate(entry: str) -> str:
    if not entry:
        return ""
    low = entry.lower()
    has_21 = bool(
        re.search(
            r"2\s*:\s*1|upper\s+second|upper-second|\b2\.1\b|first[\s-]class",
            low,
        )
    )
    has_22 = bool(
        re.search(
            r"2\s*:\s*2|lower\s+second|second\s+class\s*\(\s*2\s*:\s*2\s*\)"
            r"|minimum\s+second\s+class|\b2\.2\b",
            low,
        )
    )
    has_both = bool(re.search(r"first[\s-]or[\s-]second[\s-]class", low))
    if (has_21 and has_22) or has_both:
        return "2:1_or_2:2"
    if has_21:
        return "2:1"
    if has_22:
        return "2:2"
    if re.search(
        r"\bmaster|\bmres\b|\bmphil\b|doctorate|\bedd\b|\bphd\b|full masters",
        low,
    ):
        return "masters_or_higher"
    if re.search(r"bachelor|undergraduate|honours|hons|\bdegree\b", low):
        return "degree_unspecified"
    return "other_text"


def bangladesh_hsc_requirements_for_llm(
    *,
    study_level: str,
    course_body: str,
    entry_content: str,
    entry_block: str = "",
    postgraduate_class: str = "",
    degree_name: str = "",
) -> list[dict[str, str]]:
    """Simplified {degree, grade} rows for requirements[] merge."""
    pg_class = postgraduate_class
    if study_level == "postgraduate" and not pg_class:
        pg_class = classify_postgraduate(entry_block or course_body)
    raw = bangladesh_requirements_from_course(
        study_level=study_level,
        entry_block=entry_block or extract_entry_block(course_body, study_level),
        course_markdown=course_body,
        bangladesh_content=entry_content,
        postgraduate_class=pg_class,
        degree_name=degree_name,
    )
    seen: set[tuple[str, str]] = set()
    out: list[dict[str, str]] = []
    for row in raw:
        key = (row["degree"], row["grade"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"degree": row["degree"], "grade": row["grade"]})
    return out
