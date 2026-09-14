#!/usr/bin/env python3
"""Dry-run: map Essex foundation-year courses to Kaplan International College pathways."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

DEFAULT_PDF = Path(
    r"E:/Project Next/UK UNIVERSITIES/University-of-Essex-International-College-Summary-Sheet-Spring-2027.pdf"
)
DEFAULT_FOUND_DIR = (
    _UNI_DIR / "output"
    / "clean"
    / "courses"
    / "foundation"
)

# Degrees explicitly listed on kaplanpathways.com/courses progression lists.
OFFICIAL_PROGRESSIONS: dict[str, list[str]] = {
    "Foundation Certificate for Humanities": [
        "american studies",
        "drama",
        "film studies",
        "global studies",
        "hospitality management",
        "journalism and politics",
        "law",
        "llb",
        "social change",
    ],
    "Foundation Certificate for Science and Health": [
        "artificial intelligence",
        "biological sciences",
        "computer games",
        "economics and mathematics",
        "electronic engineering",
        "genetics",
        "psychology",
        "robotic engineering",
    ],
    "Foundation Certificate for Social Sciences": [
        "accounting",
        "business management",
        "criminology",
        "international business and finance",
        "marketing",
        "media and digital culture",
        "politics",
        "sociology",
    ],
    "International Year One in Business": [
        "accounting",
        "banking and finance",
        "business administration",
        "business management",
        "finance",
        "international business and entrepreneurship",
        "management and marketing",
        "marketing",
    ],
    "International Year One in Computer Science": [
        "artificial intelligence",
        "computer games",
        "computer science",
    ],
    "International Year One in Economics": [
        "business economics",
        "economics",
        "financial economics",
        "international economics",
        "management economics",
    ],
    "International Year One in Law": ["law", "llb"],
    "International Year One in Life Sciences": [
        "biochemistry",
        "biomedical science",
        "genetics",
        "human biology",
    ],
    "International Year One in Politics and International Relations": [
        "international development",
        "international relations",
        "politics",
        "politics and international relations",
    ],
    "International Year One in Psychology": [
        "psychology",
        "psychology with cognitive neuroscience",
    ],
}

# Broader subject-area inference for Essex foundation-year degrees not named on Kaplan lists.
INFERRED_KEYWORDS: dict[str, list[str]] = {
    "Foundation Certificate for Humanities": [
        "art history",
        "english literature",
        "english language and linguistics",
        "linguistics",
        "history",
        "philosophy",
        "liberal arts",
    ],
    "Foundation Certificate for Science and Health": [
        "biomedical science",
        "marine biology",
        "mathematics",
        "sports and exercise science",
        "sport coaching",
        "cyber security",
    ],
    "Foundation Certificate for Social Sciences": [
        "accounting and finance",
        "marketing management",
        "social sciences",
        "childhood studies",
        "psychosocial and psychoanalytic studies",
        "economics",
    ],
    "International Year One in Business": [
        "accounting and finance",
        "marketing management",
    ],
    "International Year One in Computer Science": ["cyber security"],
    "International Year One in Economics": ["accounting and finance"],
    "International Year One in Life Sciences": ["biological sciences", "marine biology"],
    "International Year One in Politics and International Relations": [
        "criminology",
        "social sciences",
        "liberal arts",
    ],
    "International Year One in Psychology": ["psychosocial and psychoanalytic studies"],
}

PATHWAYS = {
    pathway: sorted(set(OFFICIAL_PROGRESSIONS.get(pathway, []) + INFERRED_KEYWORDS.get(pathway, [])))
    for pathway in OFFICIAL_PROGRESSIONS
}

# UKVI IELTS for 2-term Spring 2027 intakes (Summary Sheet PDF).
PATHWAY_IELTS_2TERM: dict[str, tuple[str, str]] = {
    "Foundation Certificate for Humanities": ("5.5", "4.5"),
    "Foundation Certificate for Science and Health": ("5.5", "4.5"),
    "Foundation Certificate for Social Sciences": ("5.5", "4.5"),
    "International Year One in Business": ("5.5", "5.0"),
    "International Year One in Computer Science": ("5.5", "5.0"),
    "International Year One in Economics": ("5.5", "5.0"),
    "International Year One in Law": ("5.5", "5.0"),
    "International Year One in Life Sciences": ("5.5", "5.0"),
    "International Year One in Politics and International Relations": ("5.5", "5.0"),
    "International Year One in Psychology": ("5.5", "5.0"),
}

KAPLAN_IELTS_SOURCE = (
    "University of Essex International College Summary Sheet Spring 2027 (2-term, UKVI IELTS)"
)

TITLE_RE = re.compile(r"^#\s+(?:BSc|BA|BEng|LLB)\s+\(Hons\)\s+(.+)$", re.M)


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def course_title(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    match = TITLE_RE.search(text)
    if match:
        return match.group(1).strip()
    meta = re.search(r"\*\*Course:\*\*\s*(.+)", text)
    return meta.group(1).strip() if meta else md_path.stem


def match_pathways(title: str) -> tuple[list[str], list[str], list[str]]:
    normalized = normalize(title)
    official: list[str] = []
    inferred: list[str] = []
    for pathway, keywords in OFFICIAL_PROGRESSIONS.items():
        for keyword in sorted(keywords, key=len, reverse=True):
            if keyword in normalized:
                official.append(pathway)
                break
    for pathway, keywords in INFERRED_KEYWORDS.items():
        if pathway in official:
            continue
        for keyword in sorted(keywords, key=len, reverse=True):
            if keyword in normalized:
                inferred.append(pathway)
                break
    return official + inferred, official, inferred


def primary_pathway(pathways: list[str]) -> str:
    if not pathways:
        return ""
    for prefix in (
        "International Year One",
        "Foundation Certificate",
    ):
        for pathway in pathways:
            if pathway.startswith(prefix):
                return pathway
    return pathways[0]


def ielts_pathway_for_foundation_course(pathways: list[str]) -> str:
    """Prefer Foundation Certificate IELTS for foundation study-level courses."""
    for pathway in pathways:
        if pathway.startswith("Foundation Certificate"):
            return pathway
    for pathway in pathways:
        if pathway.startswith("International Year One"):
            return pathway
    return pathways[0] if pathways else ""


def kaplan_ielts_for_pathway(pathway: str) -> tuple[str, str] | None:
    return PATHWAY_IELTS_2TERM.get(pathway)


def format_kaplan_ielts_prose(overall: str, min_section: str) -> str:
    return (
        f"IELTS {overall} overall with a minimum of {min_section} in each component "
        f"(UKVI IELTS, {KAPLAN_IELTS_SOURCE})"
    )


def format_kaplan_ielts_bullet(overall: str, min_section: str) -> str:
    return f"IELTS {overall} overall with no element below {min_section} (UKVI IELTS, Kaplan Spring 2027, 2-term)"


def run_dry(foundation_dir: Path, pdf_path: Path, report_path: Path | None) -> int:
    rows: list[dict] = []
    for md_path in sorted(foundation_dir.glob("*.md")):
        title = course_title(md_path)
        pathways, official, inferred = match_pathways(title)
        rows.append(
            {
                "file": md_path.name,
                "title": title,
                "pathways": pathways,
                "officialPathways": official,
                "inferredPathways": inferred,
                "primaryPathway": primary_pathway(pathways),
                "mapped": bool(pathways),
                "officialOnly": bool(official),
            }
        )

    mapped = [row for row in rows if row["mapped"]]
    unmapped = [row for row in rows if not row["mapped"]]
    official_only = [row for row in rows if row["officialOnly"]]
    inferred_only = [row for row in rows if row["mapped"] and not row["officialOnly"]]

    print("=== Essex foundation -> International College dry run ===")
    print(f"PDF: {pdf_path} (exists={pdf_path.exists()})")
    print(
        f"Courses: {len(rows)} | mapped: {len(mapped)} | unmapped: {len(unmapped)} | "
        f"official Kaplan list: {len(official_only)} | inferred only: {len(inferred_only)}"
    )
    print()

    if unmapped:
        print("UNMAPPED:")
        for row in unmapped:
            print(f"  - {row['file']} | {row['title']}")
        print()

    if inferred_only:
        print("INFERRED ONLY (not on official Kaplan progression list):")
        for row in inferred_only:
            pathways = "; ".join(row["inferredPathways"])
            print(f"  - {row['file']} | {row['title']} | {pathways}")
        print()

    print("ALL:")
    for row in rows:
        if not row["mapped"]:
            status = "MISS"
        elif row["officialOnly"]:
            status = "OK"
        else:
            status = "INF"
        pathways = "; ".join(row["pathways"]) if row["pathways"] else "-"
        print(f"{status:4} | {row['file']} | {row['title']} | {pathways}")

    payload = {
        "pdf": str(pdf_path),
        "pdfExists": pdf_path.exists(),
        "total": len(rows),
        "mapped": len(mapped),
        "unmapped": len(unmapped),
        "officialKaplan": len(official_only),
        "inferredOnly": len(inferred_only),
        "courses": rows,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print()
        print(f"Wrote report: {report_path}")

    return 0 if not unmapped else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foundation-dir", type=Path, default=DEFAULT_FOUND_DIR)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument(
        "--report",
        type=Path,
        default=_UNI_DIR / "output"
        / "foundation_pathway_map_report.json",
    )
    args = parser.parse_args()
    return run_dry(args.foundation_dir, args.pdf, args.report)


if __name__ == "__main__":
    raise SystemExit(main())
