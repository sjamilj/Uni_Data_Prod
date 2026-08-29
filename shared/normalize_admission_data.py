"""
University Admission Data Normalization Pipeline
===================================================
Converts raw scraped/model-extracted university data into the strict
production JSON schema, applying all confirmed business rules:

- Degree normalization (allowed list only)
- GPA normalization (HSC 5.0-scale vs UG/PG/Diploma 4.0-scale, with
  A-Level -> HSC-equivalent conversion, uni-specific override support,
  and "explicit GPA stated" short-circuit)
- English test score extraction (IELTS / TOEFL / PTE)
- Tuition fee / deposit / application fee normalization (international only, numeric)
- Intake info / application deadlines (month-only tokens get current/next year; join with ", ")
- Course duration (years -> months)
- Scholarship selection (highest value wins) + full metadata list
- Metadata structure enforcement (always array of {subtitle, description[]})

Nothing is invented or estimated. Missing data -> "" or [] per the spec.
"""

import re
import json
from datetime import date
from pathlib import Path


# ============================================================
# 1. DEGREE NORMALIZATION
# ============================================================

ALLOWED_DEGREES = ["HSC", "Diploma", "BA", "BSc", "BBA", "BEng", "BCom",
                    "MA", "MSc", "MBA", "PhD"]

# Order matters: more specific patterns checked before generic ones
DEGREE_PATTERNS = [
    (r"\bA[\s-]?LEVEL\b", "HSC"),          # A-Level treated as HSC-equivalent entry
    (r"\bHSC\b", "HSC"),
    (r"\bDAKHIL\b", "HSC"),
    (r"\bALIM\b", "HSC"),
    (r"\bSSC\b", "HSC"),
    (r"\bDIPLOMA\b", "Diploma"),
    (r"\bPH\.?D\b", "PhD"),
    (r"\bMBA\b", "MBA"),
    (r"\bM\.?SC\b|\bMASTER\s+OF\s+SCIENCE\b", "MSc"),
    (r"\bM\.?A\b|\bMASTER\s+OF\s+ARTS\b", "MA"),
    (r"\bMASTER'?S?\b", "MSc"),             # generic "Master's" -> MSc default
    (r"\bBBA\b", "BBA"),
    (r"\bB\.?ENG\b|\bBENG\b", "BEng"),
    (r"\bB\.?COM\b", "BCom"),
    (r"\bB\.?SC\b|\bBACHELOR\s+OF\s+SCIENCE\b", "BSc"),
    (r"\bB\.?A\b|\bBACHELOR\s+OF\s+ARTS\b", "BA"),
    (r"\bBACHELOR'?S?\b", "BSc"),           # generic "Bachelor's" -> BSc default
]

DEGREE_LEVEL_RANK = {
    "HSC": 0, "Diploma": 0,
    "BA": 1, "BSc": 1, "BBA": 1, "BEng": 1, "BCom": 1,
    "MA": 2, "MSc": 2, "MBA": 2,
    "PhD": 3,
}


def normalize_degree_name(text):
    """Map free-text degree mention to the allowed enum. Returns '' if no match."""
    if not text:
        return ""
    upper = text.upper()
    for pattern, mapped in DEGREE_PATTERNS:
        if re.search(pattern, upper):
            return mapped
    return ""


def pick_min_and_higher_degree(requirements):
    """
    requirements: list of {"degree": str, "grade": str}
    Returns (min_degree_name, min_gpa_raw, higher_degree_name, higher_gpa_raw)
    choosing the LOWEST-ranked qualifying degree as 'min' and the
    HIGHEST-ranked as 'higher' (per: choose minimum entry requirement
    if multiple exist; higher-degree fields capture postgrad-level asks).
    """
    normalized = []
    for req in requirements or []:
        mapped = normalize_degree_name(req.get("degree", ""))
        if mapped:
            normalized.append((mapped, req.get("grade", ""), DEGREE_LEVEL_RANK.get(mapped, 1)))

    if not normalized:
        return "", "", "", ""

    normalized.sort(key=lambda x: x[2])
    min_deg, min_grade = normalized[0][0], normalized[0][1]

    higher_candidates = [n for n in normalized if n[2] >= 2]  # MA/MSc/MBA/PhD tier
    if higher_candidates:
        higher_candidates.sort(key=lambda x: -x[2])
        higher_deg, higher_grade = higher_candidates[0][0], higher_candidates[0][1]
    else:
        higher_deg, higher_grade = "", ""

    return min_deg, min_grade, higher_deg, higher_grade


# ============================================================
# 2. GPA NORMALIZATION
# ============================================================

# HSC official Bangladesh Education Board scale (DEFAULT for bare HSC %)
BD_OFFICIAL_5_SCALE = {80: 5.00, 70: 4.00, 60: 3.50, 50: 3.00, 40: 2.00, 33: 1.00}

# HSC university-defined threshold scale (used ONLY when a specific uni
# publishes its own conversion table -- see UNI_SPECIFIC_SCALES below)
BD_UNI_THRESHOLD_5_SCALE = {
    80: 5.00, 75: 4.69, 70: 4.38, 65: 4.06, 60: 3.75,
    55: 3.44, 50: 3.13, 45: 2.81, 40: 2.50
}

# UG / PG / Diploma 4.0-scale
UNIVERSITY_4_SCALE = {
    80: 4.00, 75: 3.75, 70: 3.50, 65: 3.25, 60: 3.00,
    55: 2.75, 50: 2.50, 45: 2.25, 40: 2.00
}

# UK Degree Classification -> 4.0 scale
UK_DEGREE_CLASS_SCALE = [
    (70, 4.00),  # First Class
    (60, 3.00),  # Upper Second (2:1)
    (50, 2.50),  # Lower Second (2:2)
    (40, 2.00),  # Third Class
]

# UK GCSE grade -> 5.0-ish scale (kept separate; rarely used for GPA field
# but included for completeness per original spec)
UK_GCSE_SCALE = {
    9: 5.00, 8: 5.00, 7: 5.00,
    6: 4.00, 5: 4.00,
    4: 2.00,
}

# Official UCAS Tariff points per single A-Level subject
UCAS_TARIFF = {"A*": 56, "A": 48, "B": 40, "C": 32, "D": 24, "E": 16}
UCAS_GRADE_ORDER = ("A*", "A", "B", "C", "D", "E")

# A-Level letter grade -> HSC-equivalent CGPA (direct mapping, NOT re-run
# through the percentage tables above -- combo-level profile, not per-subject average)
ALEVEL_TO_HSC_EQUIVALENT = {
    "AAA": 5.0, "AAB": 5.0, "ABB": 5.0,
    "BBB": 4.0, "BBC": 4.0,
    "BCC": 3.5, "CCC": 3.5, "CCD": 3.5, "CDD": 3.5,
    "DDD": 2.0,
}

# ------------------------------------------------------------
# UNI-SPECIFIC OVERRIDE TEMPLATE
# Copy this block, fill in the exact %->GPA table a university
# publishes on their own admissions page, and register it below.
# ------------------------------------------------------------
# UNI_SPECIFIC_SCALES = {
#     "example_university_slug": {
#         80: 5.00,
#         75: 4.50,   # <- replace with that uni's exact published values
#         70: 4.00,
#         65: 3.50,
#         60: 3.00,
#         # ... add every band the uni publishes
#     },
# }
UNI_SPECIFIC_SCALES = {}


def _canonicalize_alevel_combo(grades: list[str]) -> str:
    order = {grade: index for index, grade in enumerate(UCAS_GRADE_ORDER)}
    return "".join(sorted(grades, key=lambda g: order.get(g, 99)))


def parse_ucas_points(text: str) -> int | None:
    if not text:
        return None
    match = re.search(r"(\d{2,3})\s*UCAS\s+Tariff\s+points", text, re.I)
    if match:
        return int(match.group(1))
    return None


def parse_alevel_combo(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\b([A-D]{3})\b", text.upper())
    if not match:
        return ""
    combo = match.group(1).upper()
    if all(ch in "ABCDE" for ch in combo):
        return combo
    return ""


def ucas_points_to_alevel_combo(points: int, subjects: int = 3) -> str:
    """Resolve UCAS tariff points to a canonical 3-subject A-Level combo (e.g. 80 -> CDD)."""
    if points <= 0 or subjects <= 0:
        return ""
    from itertools import combinations_with_replacement

    matches: list[str] = []
    for combo in combinations_with_replacement(UCAS_GRADE_ORDER, subjects):
        total = sum(UCAS_TARIFF[grade] for grade in combo)
        if total != points:
            continue
        matches.append(_canonicalize_alevel_combo(list(combo)))
    if not matches:
        return ""
    return sorted(matches)[-1]


def alevel_combo_to_hsc_gpa(combo: str) -> float | str:
    combo = (combo or "").strip().upper()
    if not combo:
        return ""
    return ALEVEL_TO_HSC_EQUIVALENT.get(combo, "")


def derive_hsc_gpa_from_uk_entry_text(text: str) -> str:
    """UCAS points and/or A-Level combo -> HSC GPA grade string for requirements[]."""
    combo = parse_alevel_combo(text)
    points = parse_ucas_points(text)
    if not combo and points:
        combo = ucas_points_to_alevel_combo(points)
    gpa = alevel_combo_to_hsc_gpa(combo)
    if gpa == "":
        return ""
    if isinstance(gpa, float):
        if gpa % 1:
            return f"GPA {gpa:.2f}".rstrip("0").rstrip(".")
        return f"GPA {int(gpa)}"
    return f"GPA {gpa}"


def max_gpa_for_degree(requirements, degree_name, uni_key=None):
    """When multiple requirements share the same degree, return the highest normalized GPA."""
    values: list[float] = []
    for req in requirements or []:
        if normalize_degree_name(req.get("degree", "")) != degree_name:
            continue
        gpa = normalize_gpa(req.get("grade", ""), degree_name, uni_key=uni_key)
        if gpa != "":
            values.append(float(gpa))
    if not values:
        return ""
    return max(values)


def _closest_threshold(pct, table):
    eligible = [k for k in table if k <= pct]
    if not eligible:
        return 0.00
    return round(table[max(eligible)], 2)


def _uk_class_to_gpa(pct):
    for threshold, gpa in UK_DEGREE_CLASS_SCALE:
        if pct >= threshold:
            return gpa
    return 0.00


def normalize_gpa(raw_text, degree_level, uni_key=None):
    """
    raw_text: the raw grade string, e.g. "60%", "GPA 3.5", "70% GPA 3.5",
              "CGPA 2.75/4.0", "BBB", "Upper Second (2:1)", "Grade 6"
    degree_level: "HSC" | "Diploma" | "BA" | "BSc" | "BBA" | "BEng" |
                  "BCom" | "MA" | "MSc" | "MBA" | "PhD"
    uni_key: optional key into UNI_SPECIFIC_SCALES for HSC-level lookups

    Priority order:
      1. Ignore filler words (minimum/at least/overall/or above/equivalent)
      2. Explicit GPA/CGPA stated anywhere in the string -> use it as-is
      3. A-Level letter grade -> ALEVEL_TO_HSC_EQUIVALENT (treated as HSC)
      4. UK degree classification wording -> UK_DEGREE_CLASS_SCALE
      5. Bare percentage:
           - HSC/Diploma -> uni-specific table if available, else BD_OFFICIAL_5_SCALE
           - UG/PG        -> UNIVERSITY_4_SCALE
      6. If multiple scores present, return the MINIMUM required GPA
    """
    if not raw_text:
        return ""

    text = raw_text.strip()
    text_upper = text.upper()

    # Strip filler words
    for filler in ["MINIMUM", "AT LEAST", "OVERALL", "OR ABOVE", "EQUIVALENT", "NORMALLY"]:
        text_upper = text_upper.replace(filler, "")

    # --- A-Level letter grade check (exact token match, e.g. "BBB") ---
    alevel_match = re.search(r"\b(AAA|AAB|ABB|BBB|BBC|BCC|CCC|CCD|CDD|DDD)\b", text_upper)

    # --- Explicit GPA/CGPA stated ---
    gpa_match = re.search(r"(?:GPA|CGPA)\s*[:\-]?\s*([\d.]+)", text_upper)

    # --- UK degree classification wording ---
    uk_class_match = re.search(r"FIRST CLASS|UPPER SECOND|2:1|LOWER SECOND|2:2|THIRD CLASS", text_upper)

    # --- Bare percentage ---
    pct_match = re.search(r"([\d.]+)\s*%", text_upper)

    results = []

    if gpa_match:
        results.append(round(float(gpa_match.group(1)), 2))

    if alevel_match and not gpa_match:
        mapped = ALEVEL_TO_HSC_EQUIVALENT.get(alevel_match.group(1))
        if mapped != "":
            results.append(mapped)

    # --- UCAS tariff points -> A-Level combo -> HSC GPA ---
    if not gpa_match and not alevel_match:
        ucas_points = parse_ucas_points(text_upper)
        if ucas_points:
            combo = parse_alevel_combo(text_upper) or ucas_points_to_alevel_combo(ucas_points)
            mapped = alevel_combo_to_hsc_gpa(combo)
            if mapped != "":
                results.append(float(mapped))

    if uk_class_match and not gpa_match:
        pct_guess_map = {"FIRST CLASS": 70, "UPPER SECOND": 60, "2:1": 60,
                          "LOWER SECOND": 50, "2:2": 50, "THIRD CLASS": 40}
        for key, pct in pct_guess_map.items():
            if key in uk_class_match.group(0):
                results.append(_uk_class_to_gpa(pct))
                break

    if pct_match and not gpa_match and not alevel_match and not uk_class_match:
        pct = float(pct_match.group(1))
        if degree_level in ("HSC", "Diploma"):
            if uni_key and uni_key in UNI_SPECIFIC_SCALES:
                results.append(_closest_threshold(pct, UNI_SPECIFIC_SCALES[uni_key]))
            else:
                results.append(_closest_threshold(pct, BD_OFFICIAL_5_SCALE))  # DEFAULT
        else:
            results.append(_closest_threshold(pct, UNIVERSITY_4_SCALE))

    if not results:
        return ""

    return min(results)  # rule 7: if multiple scores present, return minimum


# ============================================================
# 3. ENGLISH TEST SCORES
# ============================================================

ENGLISH_SCORE_KEYS = (
    "ieltsMinOverall",
    "ieltsMinSection",
    "toeflMinOverall",
    "toeflMinSection",
    "pteMinOverall",
    "pteMinSection",
)


def collect_english_text_blocks(raw: dict) -> list[str]:
    blocks: list[str] = []
    for item in raw.get("englishRequirementText") or []:
        if item:
            blocks.append(str(item))

    meta = raw.get("academicRequirementsMetaData") or raw.get("AcademicRequirementsMetaData") or []
    for item in meta:
        subtitle = str(item.get("subtitle", "")).strip().lower()
        if "english" not in subtitle:
            continue
        for desc in item.get("description") or []:
            if desc:
                blocks.append(str(desc))
    return blocks


def extract_english_scores(text_blocks):
    """
    text_blocks: list of strings that may contain IELTS/TOEFL/PTE requirements
    Returns dict with ielts/toefl/pte overall + section minimums.
    """
    combined = " ".join(text_blocks or [])
    result = {
        "ieltsMinOverall": "", "ieltsMinSection": "",
        "toeflMinOverall": "", "toeflMinSection": "",
        "pteMinOverall": "", "pteMinSection": "",
    }

    ielts = re.search(
        r"IELTS[^0-9]*(\d+\.?\d*)[^0-9]*(?:with\s+)?(?:no\s+(?:less\s+than|element|individual)\s+|no.*?below|min(?:imum)?\s+(?:of\s+)?|at\s+least\s+)[^0-9]*(\d+\.?\d*)",
        combined,
        re.IGNORECASE,
    )
    if ielts:
        result["ieltsMinOverall"] = ielts.group(1)
        result["ieltsMinSection"] = ielts.group(2)
    else:
        ielts_overall = re.search(r"IELTS[^0-9]*(\d+\.?\d*)", combined, re.IGNORECASE)
        if ielts_overall:
            result["ieltsMinOverall"] = ielts_overall.group(1)

    toefl = re.search(
        r"TOEFL[^0-9]*(\d+\.?\d*)[^0-9]*(?:with\s+)?(?:a\s+)?(?:minimum\s+of\s+|min(?:imum)?\s+)[^0-9]*(\d+\.?\d*)",
        combined,
        re.IGNORECASE,
    )
    if toefl:
        result["toeflMinOverall"] = toefl.group(1)
        result["toeflMinSection"] = toefl.group(2)
    else:
        toefl_overall = re.search(r"TOEFL[^0-9]*(\d+\.?\d*)", combined, re.IGNORECASE)
        if toefl_overall:
            result["toeflMinOverall"] = toefl_overall.group(1)

    pte = re.search(
        r"PTE[^0-9]*(\d+\.?\d*)[^0-9]*(?:with\s+)?(?:a\s+)?(?:minimum\s+(?:score\s+)?of\s+|min(?:imum)?\s+)[^0-9]*(\d+\.?\d*)",
        combined,
        re.IGNORECASE,
    )
    if pte:
        result["pteMinOverall"] = pte.group(1)
        result["pteMinSection"] = pte.group(2)
    else:
        pte_overall = re.search(r"PTE[^0-9]*(\d+\.?\d*)", combined, re.IGNORECASE)
        if pte_overall:
            result["pteMinOverall"] = pte_overall.group(1)

    return result


# ============================================================
# 4. TUITION FEE / DEPOSIT / APPLICATION FEE
# ============================================================

def normalize_money(raw):
    """Strip currency symbols/commas, return numeric string only, or ''."""
    if raw is None or raw == "":
        return ""
    match = re.search(r"[\d,]+(?:\.\d+)?", str(raw))
    if not match:
        return ""
    return match.group(0).replace(",", "")


def normalize_tuition_fee(fee_candidates):
    """
    fee_candidates: list of dicts like {"label": "International", "amount": "£17,000"}
    Picks the INTERNATIONAL fee; if multiple international years exist,
    picks the highest.
    """
    intl_values = []
    for c in fee_candidates or []:
        label = c.get("label", "").upper()
        if "INTERNATIONAL" in label or "OVERSEAS" in label or "NON-UK" in label:
            val = normalize_money(c.get("amount", ""))
            if val:
                intl_values.append(float(val))
    if not intl_values:
        return ""
    return str(int(max(intl_values)) if max(intl_values).is_integer() else max(intl_values))


# Historic / current Stage 1 few-shot amounts — drop unless grounded in source or candidates.
_PROMPT_EXAMPLE_AUD_FEE = ("42500", "AUD")
_PROMPT_EXAMPLE_GBP_FEE = ("18570", "GBP")
_PROMPT_EXAMPLE_FEES = frozenset({_PROMPT_EXAMPLE_AUD_FEE, _PROMPT_EXAMPLE_GBP_FEE})

_INTERNATIONAL_FEE_UNAVAILABLE_RES = [
    re.compile(r"international students\s*\(\d{4}/\d{2}\)\s*:\s*\[", re.I),
    re.compile(r"find out more about the international student fee", re.I),
    re.compile(r"fee not available", re.I),
    re.compile(r"fees.{0,40}not confirmed", re.I),
    re.compile(r"available to uk students only", re.I),
]


def _flatten_fees_metadata_text(fees_meta) -> str:
    lines: list[str] = []
    for block in fees_meta or []:
        if not isinstance(block, dict):
            continue
        desc = block.get("description") or []
        if isinstance(desc, list):
            lines.extend(str(item) for item in desc if item)
        elif desc:
            lines.append(str(desc))
    return "\n".join(lines)


def _fee_amount_in_text(amount: str, text: str) -> bool:
    amount = str(amount or "").strip()
    if not amount or not text:
        return False
    if amount in text:
        return True
    if amount.isdigit():
        try:
            with_commas = f"{int(amount):,}"
            if with_commas in text:
                return True
        except ValueError:
            pass
    return False


def _metadata_has_gbp_fee_amount(text: str) -> bool:
    return bool(re.search(r"£[\d,]+", text or ""))


def _extract_gbp_fee_from_metadata(
    text: str,
    *,
    require_explicit_label: bool = False,
) -> tuple[str, str]:
    explicit = re.search(
        r"(?:international|tuition fee)[^.\n]{0,40}£([\d,]+)",
        text or "",
        re.I,
    )
    if explicit:
        amount = normalize_money(explicit.group(1))
        return (amount, "GBP") if amount else ("", "")
    if require_explicit_label:
        return "", ""
    match = re.search(r"£([\d,]+)", text or "")
    if not match:
        return "", ""
    amount = normalize_money(match.group(1))
    return (amount, "GBP") if amount else ("", "")


def _metadata_has_prompt_hallucination(meta_text: str) -> bool:
    text = meta_text or ""
    return bool(
        re.search(r"\bAUD\s*42,?500\b", text, re.I)
        or re.search(r"\b18,?570\b", text)
        or "example.com" in text.lower()
    )


def _international_fee_unavailable(meta_text: str) -> bool:
    if not meta_text:
        return False
    if any(pattern.search(meta_text) for pattern in _INTERNATIONAL_FEE_UNAVAILABLE_RES):
        return True
    fee_lines = [line.strip() for line in meta_text.splitlines() if line.strip()]
    if len(fee_lines) == 1 and re.fullmatch(
        r"International students\s*\(\d{4}/\d{2}\)",
        fee_lines[0],
        re.I,
    ):
        return True
    return False


def sanitize_international_tuition_fee(
    record: dict,
    *,
    fee_from_candidates: bool = False,
    source_text: str = "",
) -> None:
    """Drop hallucinated or unsupported international fees; recover GBP from metadata when possible."""
    tuition_fee = str(record.get("tuitionFee") or "").strip()
    currency = str(record.get("currency") or "").strip().upper()
    meta_text = _flatten_fees_metadata_text(record.get("feesMetaData") or [])
    grounded = bool(
        fee_from_candidates
        or _fee_amount_in_text(tuition_fee, source_text)
        or _fee_amount_in_text(tuition_fee, meta_text)
    )

    if not tuition_fee and not currency:
        return

    should_clear = False
    if (tuition_fee, currency) in _PROMPT_EXAMPLE_FEES and not grounded:
        should_clear = True
    elif currency == "AUD" and not grounded:
        should_clear = True
    elif _international_fee_unavailable(meta_text) and not grounded:
        should_clear = True
    elif (
        _metadata_has_prompt_hallucination(meta_text)
        and tuition_fee
        and not grounded
        and not re.search(
            r"(?:international|tuition fee)[^.\n]{0,40}£[\d,]+",
            meta_text,
            re.I,
        )
    ):
        should_clear = True
    elif tuition_fee and not grounded:
        should_clear = True

    if not should_clear:
        return

    record["tuitionFee"] = ""
    record["currency"] = ""

    if _international_fee_unavailable(meta_text):
        return

    recovered_fee, recovered_currency = _extract_gbp_fee_from_metadata(
        meta_text,
        require_explicit_label=_metadata_has_prompt_hallucination(meta_text),
    )
    if recovered_fee:
        record["tuitionFee"] = recovered_fee
        record["currency"] = recovered_currency


# ============================================================
# 5. INTAKE INFO / APPLICATION DEADLINES
# ============================================================

MONTH_TO_NUM = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

DATE_TOKEN_RE = re.compile(
    r"^(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"(?:\s+((?:19|20)\d{2}))?$",
    re.IGNORECASE,
)


def _split_date_tokens(value):
    if not value:
        return []
    if isinstance(value, list):
        tokens = value
    else:
        tokens = re.split(r",\s*", str(value))
    return [token.strip() for token in tokens if token and token.strip()]


def _format_date_token(day, month_name, year):
    month_title = month_name[:1].upper() + month_name[1:].lower()
    if day:
        return f"{int(day)} {month_title} {year}"
    return f"{month_title} {year}"


def normalize_date_token(token, reference=None):
    """
    Normalize one intake/deadline token.

    - Month only -> add current year; if that month already passed, use next year.
    - Day + month -> add year using the same past/future rule on the full date.
    - Explicit year (e.g. '30 September 2026') -> keep as given.
    """
    reference = reference or date.today()
    token = (token or "").strip()
    if not token:
        return ""

    match = DATE_TOKEN_RE.fullmatch(token)
    if not match:
        return token

    day_raw, month_name, year_raw = match.groups()
    month_num = MONTH_TO_NUM[month_name.lower()]
    if year_raw:
        return _format_date_token(day_raw, month_name, int(year_raw))

    year = reference.year
    if day_raw:
        day = int(day_raw)
        try:
            candidate = date(year, month_num, day)
        except ValueError:
            return token
        if candidate < reference:
            year += 1
    elif month_num < reference.month:
        year += 1

    return _format_date_token(day_raw, month_name, year)


def normalize_date_list(value, reference=None):
    """Normalize comma-separated month/date tokens and join with ', '."""
    reference = reference or date.today()
    normalized = [
        normalize_date_token(token, reference=reference)
        for token in _split_date_tokens(value)
    ]
    return ", ".join(part for part in normalized if part)


def normalize_intake(intake_list):
    return normalize_date_list(intake_list)


def normalize_application_deadline(value):
    return normalize_date_list(value)


# ============================================================
# 6. COURSE DURATION -> MONTHS
# ============================================================

def normalize_duration(raw):
    """'1 year' -> '12', '2 years' -> '24', '12 months' -> '12', '18' -> '18'."""
    if not raw:
        return ""
    text = str(raw).lower()

    year_match = re.search(r"([\d.]+)\s*year", text)
    if year_match:
        years = float(year_match.group(1))
        return str(int(years * 12))

    month_match = re.search(r"([\d.]+)\s*month", text)
    if month_match:
        return str(int(float(month_match.group(1))))

    number_only = re.search(r"^\s*([\d.]+)\s*$", text)
    if number_only:
        return str(int(float(number_only.group(1))))

    return ""


# ============================================================
# 7. SCHOLARSHIP NORMALIZATION
# ============================================================

def normalize_scholarships(scholarship_list):
    """
    scholarship_list: list of dicts like
      {"name": "...", "amount": "£7,000", "type": "Amount"|"Percentage", "details": [...]}

    Returns (scholarshipName, scholarshipAmount, scholarshipType, scholarshipMetaData)
    Picks the single highest-value scholarship for the top-level fields;
    ALL scholarships go into one metadata object.
    """
    if not scholarship_list:
        return "", "", "", []

    best = None
    best_value = -1
    for s in scholarship_list:
        raw_amount = normalize_money(s.get("amount", ""))
        value = float(raw_amount) if raw_amount else -1
        if value > best_value:
            best_value = value
            best = s

    scholarship_name = best.get("name", "") if best else ""
    scholarship_amount = normalize_money(best.get("amount", "")) if best else ""
    scholarship_type = best.get("type", "") if best else ""

    all_descriptions = []
    for s in scholarship_list:
        if s.get("name"):
            all_descriptions.append(s["name"])
        for line in s.get("details", []):
            if line:
                all_descriptions.append(line)

    scholarship_meta = [{
        "subtitle": "Scholarships",
        "description": all_descriptions
    }] if all_descriptions else []

    return scholarship_name, scholarship_amount, scholarship_type, scholarship_meta


# ============================================================
# 8. METADATA STRUCTURE ENFORCEMENT
# ============================================================

def enforce_metadata_structure(meta):
    """Ensure metadata is always [{'subtitle': str, 'description': [str,...]}], never null/object."""
    if not meta:
        return []
    if isinstance(meta, dict):
        meta = [meta]
    cleaned = []
    for block in meta:
        subtitle = block.get("subtitle", "")
        desc = block.get("description", [])
        if isinstance(desc, str):
            desc = [desc]
        cleaned.append({"subtitle": subtitle, "description": [d for d in desc if d]})
    return cleaned


# ============================================================
# 9. FULL PIPELINE
# ============================================================

FINAL_SCHEMA_KEYS = [
    "courseName", "courseUrl", "minDegreeName", "minGpa", "higherDegreeName",
    "higherGpa", "AcademicRequirementsMetaData", "intakeInfo", "courseDuration",
    "tuitionFee", "currency", "initialDeposit", "applicationFee", "feesMetaData",
    "applicationDeadline", "ieltsMinOverall", "ieltsMinSection", "toeflMinOverall",
    "toeflMinSection", "pteMinOverall", "pteMinSection", "scholarshipName",
    "scholarshipAmount", "scholarshipType", "scholarshipMetaData",
]


def process_record(raw):
    """
    raw: dict of loosely-structured extracted data (whatever shape the
    model/scraper produced). This function pulls out and normalizes
    every field into the strict production schema.

    Expected optional raw keys (adapt extraction step if your scraper
    uses different key names):
      courseName, courseUrl, requirements (list of {degree, grade}),
      academicRequirementsMetaData, intakeInfo (list or str),
      courseDuration (raw string), tuitionFeeCandidates (list),
      currency, initialDeposit, applicationFee, feesMetaData,
      applicationDeadline, englishRequirementText (list of strings),
      scholarships (list), uni_key (optional, for GPA overrides)
    """
    out = {k: "" for k in FINAL_SCHEMA_KEYS}
    out["AcademicRequirementsMetaData"] = []
    out["feesMetaData"] = []
    out["scholarshipMetaData"] = []

    out["courseName"] = raw.get("courseName", "")
    out["courseUrl"] = raw.get("courseUrl", "")

    uni_key = raw.get("uni_key")

    # --- Degrees + GPA ---
    min_deg, min_grade_raw, higher_deg, higher_grade_raw = pick_min_and_higher_degree(
        raw.get("requirements", [])
    )
    out["minDegreeName"] = min_deg
    out["higherDegreeName"] = higher_deg
    if min_deg:
        min_gpa = max_gpa_for_degree(raw.get("requirements", []), min_deg, uni_key=uni_key)
        if min_gpa == "":
            min_gpa = normalize_gpa(min_grade_raw, min_deg, uni_key=uni_key)
        out["minGpa"] = min_gpa
    else:
        out["minGpa"] = ""
    out["higherGpa"] = normalize_gpa(higher_grade_raw, higher_deg, uni_key=uni_key) if higher_deg else ""
    # convert numeric GPA back to string for schema consistency (matches example: "2.75")
    if isinstance(out["minGpa"], float):
        out["minGpa"] = f"{out['minGpa']:.2f}".rstrip("0").rstrip(".") if out["minGpa"] % 1 else str(out["minGpa"])
    if isinstance(out["higherGpa"], float):
        out["higherGpa"] = f"{out['higherGpa']:.2f}".rstrip("0").rstrip(".") if out["higherGpa"] % 1 else str(out["higherGpa"])

    out["AcademicRequirementsMetaData"] = enforce_metadata_structure(
        raw.get("academicRequirementsMetaData") or raw.get("AcademicRequirementsMetaData") or []
    )

    # --- Intake / Duration ---
    out["intakeInfo"] = normalize_intake(raw.get("intakeInfo", ""))
    out["courseDuration"] = normalize_duration(raw.get("courseDuration", ""))

    # --- Fees ---
    tuition_fee = normalize_tuition_fee(raw.get("tuitionFeeCandidates", []))
    fee_from_candidates = bool(tuition_fee)
    if not tuition_fee and raw.get("tuitionFee"):
        tuition_fee = normalize_money(raw.get("tuitionFee"))
    out["tuitionFee"] = tuition_fee
    out["currency"] = raw.get("currency", "")
    out["initialDeposit"] = normalize_money(raw.get("initialDeposit", ""))
    out["applicationFee"] = normalize_money(raw.get("applicationFee", ""))
    out["feesMetaData"] = enforce_metadata_structure(raw.get("feesMetaData", []))
    sanitize_international_tuition_fee(out, fee_from_candidates=fee_from_candidates)
    out["applicationDeadline"] = normalize_application_deadline(raw.get("applicationDeadline", ""))

    # --- English scores ---
    english = extract_english_scores(collect_english_text_blocks(raw))
    for key in ENGLISH_SCORE_KEYS:
        existing = str(raw.get(key) or "").strip()
        out[key] = existing if existing else english.get(key, "")

    # --- Scholarships ---
    scholarship_list = raw.get("scholarships") or []
    if scholarship_list:
        (out["scholarshipName"], out["scholarshipAmount"],
         out["scholarshipType"], out["scholarshipMetaData"]) = normalize_scholarships(
            scholarship_list
        )
    else:
        out["scholarshipName"] = str(raw.get("scholarshipName") or "")
        out["scholarshipAmount"] = normalize_money(raw.get("scholarshipAmount", ""))
        out["scholarshipType"] = str(raw.get("scholarshipType") or "")
        out["scholarshipMetaData"] = enforce_metadata_structure(
            raw.get("scholarshipMetaData") or []
        )

    return out


def normalize_extracted_courses(
    code_dir: Path,
    *,
    limit: int | None = None,
) -> list[Path]:
    from uni_paths import resolve_code_dir, resolve_output_dir

    code_dir = resolve_code_dir(code_dir)
    output_dir = resolve_output_dir(code_dir)
    extracted_dir = output_dir / "extracted"
    if not extracted_dir.is_dir():
        raise FileNotFoundError(f"{extracted_dir} not found")

    from study_level import iter_extracted_json

    output_paths = iter_extracted_json(extracted_dir, "output.json")
    if limit is not None:
        output_paths = output_paths[:limit]
    if not output_paths:
        raise FileNotFoundError(f"No output.json files found under {extracted_dir}")

    written: list[Path] = []
    for output_path in output_paths:
        raw = json.loads(output_path.read_text(encoding="utf-8"))
        normalized = process_record(raw)
        target = output_path.parent / "normalized.json"
        target.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(target)
    return written


# ============================================================
# EXAMPLE USAGE
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Normalize extracted course output.json into normalized.json"
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        default=".",
        help="University code/ directory (default: cwd)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Normalize only the first N extracted courses",
    )
    parser.add_argument(
        "--example",
        action="store_true",
        help="Run the built-in example record instead of batch normalization",
    )
    args = parser.parse_args()

    if args.example:
        example_raw = {
            "courseName": "Accounting and Finance",
            "courseUrl": "https://aru-sc104-prod-uksouth-cd.azurewebsites.net/study/postgraduate/accounting-and-finance",
            "uni_key": None,  # set to a slug if this uni publishes its own HSC table
            "requirements": [
                {"degree": "HSC", "grade": "GPA 3.00"},
                {"degree": "BA", "grade": "60%"},
                {"degree": "BSc", "grade": "60%"},
                {"degree": "MSc", "grade": "60%"},
                {"degree": "4 year Bachelor degree from BUET", "grade": "55% (CGPA 2.75) or above"},
            ],
            "academicRequirementsMetaData": [
                {"subtitle": "Entry Requirements",
                 "description": ["A Level: ABB (120 UCAS Tariff points)", "BTEC: DDM"]},
            ],
            "intakeInfo": ["January 2027", "September 2026"],
            "courseDuration": "12 months",
            "tuitionFeeCandidates": [
                {"label": "UK", "amount": "£9,000"},
                {"label": "International", "amount": "£21,500"},
            ],
            "currency": "GBP",
            "initialDeposit": "£500",
            "applicationFee": "£50",
            "feesMetaData": [
                {"subtitle": "Fees", "description": ["Tuition fees are subject to change."]},
            ],
            "applicationDeadline": "31st January, 30th September",
            "englishRequirementText": [
                "IELTS 6.5 overall with no individual band below 6.0.",
                "TOEFL iBT 72 overall with a minimum of 17 in each component.",
            ],
            "scholarships": [
                {"name": "International Undergraduate Scholarship", "amount": "£7,000",
                 "type": "Amount", "details": ["Awarded automatically if eligibility criteria are met."]},
                {"name": "Alumni Scholarship", "amount": "£1,000",
                 "type": "Amount", "details": ["For eligible international alumni progressing to PG study."]},
            ],
        }

        result = process_record(example_raw)
        print(json.dumps(result, indent=2))
    else:
        try:
            written = normalize_extracted_courses(Path(args.code_dir), limit=args.limit)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            raise SystemExit(1) from exc
        for path in written:
            print(f"Wrote {path}")
