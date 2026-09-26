#!/usr/bin/env python3
"""Convert ULaw country entry-requirements HTML → bangladesh-entry.md + english-requirements.md JSON.

The saved page (Bangladesh selected) uses accordions: subject (h3) → programme (h4) + duration
(span) → English + Entry columns. Each programme becomes one JSON row with ``duration`` and
``subjectArea`` for later course.md backfill.

Example::

    python convert_country_entry_html.py
    python convert_country_entry_html.py --html "../uni_req/International Entry Requirements _ University of Law.html"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup

_CODE_DIR = Path(__file__).resolve().parent
_UNI_ROOT = _CODE_DIR.parent
_SHARED = _UNI_ROOT.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from entry_requirements_mapping import parse_ielts_bands

DEFAULT_HTML = _UNI_ROOT / "uni_req" / "International Entry Requirements _ University of Law.html"
DEFAULT_OUT = _UNI_ROOT / "output" / "clean" / "uni"
DEFAULT_SOURCE_URL = (
    "https://www.law.ac.uk/students/international/the-application-process/entry-requirements/"
)

IELTS_TEST_NAME = "IELTS Academic (or equivalent per ULaw accepted qualifications PDF)"


def _load_university_name(code_dir: Path) -> str:
    for name in (".env", "ENV.MD"):
        path = code_dir / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("UNIVERSITY_NAME="):
                return line.split("=", 1)[1].strip()
    return "University of Law"


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text or "")).strip()


def _html_block_to_text(element) -> str:
    if element is None:
        return ""
    for tag in element.find_all(["script", "style"]):
        tag.decompose()
    for br in element.find_all("br"):
        br.replace_with("\n")
    for li in element.find_all("li"):
        li.insert_before("• ")
        li.insert_after("\n")
    text = element.get_text("\n", strip=True)
    lines = [_normalize_ws(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _infer_duration(header_span: str, title: str) -> str:
    bits: list[str] = []
    if header_span:
        bits.append(_normalize_ws(header_span))
    combined = " ".join(bits)
    if not combined and "foundation year" in title.lower():
        combined = "4 years with foundation year"
    return combined


def _program_label(subject: str, title: str) -> str:
    subject = subject.strip()
    title = title.strip()
    if subject and title:
        return f"{subject}: {title}"
    return title or subject


def _parse_english_tests(english_text: str) -> list[dict[str, str]]:
    text = _normalize_ws(english_text)
    if not text:
        return []
    if re.search(r"contact our", text, re.I):
        return []

    tests: list[dict[str, str]] = []
    overall, section = parse_ielts_bands(text)
    if overall:
        tests.append(
            {
                "TestName": IELTS_TEST_NAME,
                "ieltsMinOverall": overall,
                "ieltsMinSection": section,
            }
        )
    pearson = re.search(r"Pearson\s+level\s+(\d+)", text, re.I)
    if pearson:
        score = pearson.group(1)
        tests.append(
            {
                "TestName": "Pearson PTE Academic",
                "pteMinOverall": score,
                "pteMinSection": score,
            }
        )
    return tests


def _entry_requirements_from_text(entry_text: str, *, study_level: str) -> list[dict[str, str]]:
    """Best-effort structured rows; full text always kept in description."""
    text = _normalize_ws(entry_text)
    if not text:
        return []
    if re.search(r"contact our.*?admissions", text, re.I):
        return []

    has_bangladesh = bool(
        re.search(
            r"Bangladesh|Higher Secondary|Intermediate Certificate",
            text,
            re.I,
        )
    )
    uk_only = bool(
        re.search(r"UK Qualifying Law|pass at the PGDL|\bPGDL\b|\b2:[12]\b", text, re.I)
    )

    requirements: list[dict[str, str]] = []

    hsc = re.search(
        r"Higher Secondary School Certificate or Intermediate Certificate:\s*([^<\n]+)",
        text,
        re.I,
    )
    if hsc:
        requirements.append({"degree": "HSC", "grade": _normalize_ws(hsc.group(1))})

    if re.search(r"4\s*year\s*Bachelor'?s?\s+degree\s+from\s+Bangladesh", text, re.I):
        m = re.search(
            r"4\s*year\s*Bachelor'?s?\s+degree\s+from\s+Bangladesh\s*[–-]\s*([^,]+)",
            text,
            re.I,
        )
        grade = _normalize_ws(m.group(1)) if m else ""
        requirements.append({"degree": "BSc", "grade": grade or "see description"})

    if re.search(r"Master'?s?\s+degree\s+from\s+Bangladesh", text, re.I):
        m = re.search(
            r"Master'?s?\s+degree\s+from\s+Bangladesh[^–-]*[–-]\s*([^,]+)",
            text,
            re.I,
        )
        grade = _normalize_ws(m.group(1)) if m else ""
        requirements.append({"degree": "MSc", "grade": grade or "see description"})

    if re.search(r"Bachelor'?s?\s+degree\s*\(BUET only\)", text, re.I):
        m = re.search(
            r"Bachelor'?s?\s+degree\s*\(BUET only\)[^–-]*[–-]\s*([^,]+)",
            text,
            re.I,
        )
        grade = _normalize_ws(m.group(1)) if m else ""
        requirements.append({"degree": "BEng", "grade": grade or "see description"})

    if re.search(r"\bHND\b|Qualifi\s+Level\s+5|Level\s+5\s+HND", text, re.I):
        if study_level != "Postgraduate":
            requirements.append(
                {"degree": "Diploma", "grade": "Level 5 HND or equivalent (see description)"}
            )

    if uk_only and not has_bangladesh and not requirements:
        return []

    if has_bangladesh and re.search(r"\b2:1\b", text):
        requirements.append({"degree": "BA", "grade": "UK Qualifying Law degree 2:1 or above"})
    elif has_bangladesh and re.search(r"\b2:2\b", text):
        requirements.append({"degree": "BSc", "grade": "UK degree 2:2 or above"})

    return requirements


def _classify_study_level(section: str, programme_title: str) -> str:
    title_l = programme_title.lower()
    if "international foundation programme" in title_l:
        return "Foundation"
    if section.lower().startswith("undergraduate"):
        return "Undergraduate"
    return "Postgraduate"


def _extract_programmes_from_section(section_soup: BeautifulSoup, section_name: str) -> list[dict]:
    programmes: list[dict] = []
    for accordion in section_soup.find_all("div", class_=re.compile(r"\baccordion\b")):
        subject_h3 = accordion.find("h3")
        if not subject_h3:
            continue
        subject = _normalize_ws(subject_h3.get_text())
        for item in accordion.find_all("div", class_="accordion__item"):
            header = item.find("div", class_="accordion__header")
            body = item.find("div", class_="accordion__body")
            if not header or not body:
                continue
            h4 = header.find("h4")
            if not h4:
                continue
            title = _normalize_ws(h4.get_text())
            span = header.find("span")
            header_span = _normalize_ws(span.get_text()) if span else ""
            duration = _infer_duration(header_span, title)

            english_p = None
            entry_node = None
            for p in body.find_all("p"):
                strong = p.find("strong")
                if not strong:
                    continue
                label = _normalize_ws(strong.get_text()).lower()
                if label.startswith("english language"):
                    english_p = p
                elif label.startswith("entry requirements"):
                    entry_node = p.find("span") or p

            english_text = ""
            if english_p:
                strong = english_p.find("strong")
                if strong:
                    strong.extract()
                english_text = _html_block_to_text(english_p)

            entry_text = _html_block_to_text(entry_node) if entry_node else ""
            if entry_text.lower().startswith("entry requirements"):
                entry_text = entry_text.split("entry requirements", 1)[-1].strip(" :")

            if not entry_text:
                for col in body.find_all("div", class_=re.compile(r"col-sm-12")):
                    if col.find("strong", string=re.compile(r"entry requirements", re.I)):
                        continue
                    candidate = _html_block_to_text(col)
                    if candidate and re.search(r"contact our|admissions team", candidate, re.I):
                        entry_text = candidate
                        break

            study_level = _classify_study_level(section_name, title)
            program_name = _program_label(subject, title)
            requirements = (
                _entry_requirements_from_text(entry_text, study_level=study_level)
                if entry_text
                else []
            )
            description: list[str] = []
            if entry_text:
                description.append(_normalize_ws(entry_text))
            contact_only = bool(
                re.search(r"contact our|admissions team", entry_text, re.I)
                and not requirements
            )
            if contact_only:
                description.append("Contact Admissions team for portfolio review.")

            programmes.append(
                {
                    "studyLevel": study_level,
                    "subjectArea": subject,
                    "program": program_name,
                    "duration": duration,
                    "requirements": requirements,
                    "description": description,
                    "englishText": english_text,
                    "section": section_name,
                }
            )
    return programmes


def parse_country_entry_html(html: str) -> tuple[list[dict], list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    raw_programmes: list[dict] = []

    for h2 in soup.find_all("h2", class_="heading"):
        heading = _normalize_ws(h2.get_text())
        if "undergraduate entry requirements" in heading.lower():
            section_name = "Undergraduate"
        elif "postgraduate entry requirements" in heading.lower():
            section_name = "Postgraduate"
        else:
            continue
        container = h2.find_parent("div", class_=re.compile(r"requirements"))
        if not container:
            container = h2.parent
        raw_programmes.extend(_extract_programmes_from_section(container, section_name))

    bangladesh: dict[str, dict] = {
        "Foundation": {"studyLevel": "Foundation", "programs": []},
        "Undergraduate": {"studyLevel": "Undergraduate", "programs": []},
        "Postgraduate": {"studyLevel": "Postgraduate", "programs": []},
    }
    english_rows: list[dict] = []

    for row in raw_programmes:
        level = row["studyLevel"]
        bangladesh[level]["programs"].append(
            {
                "program": row["program"],
                "subjectArea": row["subjectArea"],
                "duration": row["duration"],
                "requirements": row["requirements"],
                "description": row["description"],
            }
        )

        tests = _parse_english_tests(row["englishText"])
        desc = []
        if row["englishText"]:
            desc.append(row["englishText"])
        if row["duration"]:
            desc.append(f"Duration: {row['duration']}")

        english_rows.append(
            {
                "TestStudyLevel": level,
                "subjectArea": row["subjectArea"],
                "ProgramName": row["program"],
                "duration": row["duration"],
                "TestRequirements": tests,
                "description": desc,
            }
        )

    study_levels = [bangladesh[k] for k in ("Foundation", "Undergraduate", "Postgraduate")]
    study_levels = [sl for sl in study_levels if sl["programs"]]
    return study_levels, english_rows


def _frontmatter(
    *,
    source_html: str,
    source_url: str,
    university: str,
    cleaned_at: str,
) -> str:
    return (
        "---\n"
        f"source_html: {source_html}\n"
        f"source_url: {source_url}\n"
        "page_type: uni\n"
        f"university: {university}\n"
        f"cleaned_at: {cleaned_at}\n"
        "---\n"
    )


def write_outputs(
    *,
    study_levels: list[dict],
    english_rows: list[dict],
    out_dir: Path,
    source_html_rel: str,
    source_url: str,
    university: str,
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned_at = date.today().isoformat()

    bd_payload = {"studyLevels": study_levels}
    bd_path = out_dir / "bangladesh-entry.md"
    bd_body = (
        _frontmatter(
            source_html=source_html_rel,
            source_url=source_url,
            university=university,
            cleaned_at=cleaned_at,
        )
        + "## Academic Requirements\n\n"
        + json.dumps(bd_payload, indent=2, ensure_ascii=False)
        + "\n"
    )
    bd_path.write_text(bd_body, encoding="utf-8")

    en_path = out_dir / "english-requirements.md"
    en_body = (
        _frontmatter(
            source_html=source_html_rel,
            source_url=source_url,
            university=university,
            cleaned_at=cleaned_at,
        )
        + "# English Language Requirements\n\n"
        + json.dumps(english_rows, indent=2, ensure_ascii=False)
        + "\n"
    )
    en_path.write_text(en_body, encoding="utf-8")
    return bd_path, en_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert ULaw international entry HTML (country selected) to uni JSON markdown.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML,
        help="Saved entry requirements HTML (Bangladesh selected on site).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT,
        help="Directory for bangladesh-entry.md and english-requirements.md",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="Canonical live URL for frontmatter source_url",
    )
    parser.add_argument(
        "--source-html-rel",
        default="",
        help="Frontmatter source_html path (default: relative path from university root)",
    )
    parser.add_argument(
        "--university",
        default="",
        help="Override UNIVERSITY_NAME from code/.env or ENV.MD",
    )
    args = parser.parse_args(argv)

    html_path = args.html.resolve()
    if not html_path.is_file():
        print(f"HTML not found: {html_path}", file=sys.stderr)
        return 1

    university = args.university.strip() or _load_university_name(_CODE_DIR)
    rel_html = args.source_html_rel.strip()
    if not rel_html:
        try:
            rel_html = html_path.relative_to(_UNI_ROOT).as_posix()
        except ValueError:
            rel_html = html_path.name

    html = html_path.read_text(encoding="utf-8", errors="replace")
    study_levels, english_rows = parse_country_entry_html(html)
    if not study_levels:
        print("No programmes parsed — check HTML structure.", file=sys.stderr)
        return 1

    bd_path, en_path = write_outputs(
        study_levels=study_levels,
        english_rows=english_rows,
        out_dir=args.out_dir.resolve(),
        source_html_rel=rel_html,
        source_url=args.source_url.strip(),
        university=university,
    )
    n_prog = sum(len(sl["programs"]) for sl in study_levels)
    print(f"Wrote {bd_path} ({n_prog} programmes across {len(study_levels)} study levels)")
    print(f"Wrote {en_path} ({len(english_rows)} English rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
