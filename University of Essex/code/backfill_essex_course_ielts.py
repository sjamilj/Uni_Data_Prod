#!/usr/bin/env python3
"""Backfill missing English/IELTS sections in Essex course markdown files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from html import unescape
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
_UNI_DIR = _CODE_DIR.parent
_REPO = _CODE_DIR.parents[1]

from bs4 import BeautifulSoup

_SHARED = _REPO / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from course_markdown_cleanup import CourseMarkdownCleaner, parse_uni_json_payload  # noqa: E402
from llm_extract import (  # noqa: E402
    ExtractionPathConfig,
    Stage2Enricher,
    load_uni_section,
    resolve_english_course_group,
    select_english_json_program,
)
from uni_pages import split_frontmatter  # noqa: E402

USER_AGENT = "Mozilla/5.0 (compatible; UniDataProd/1.0; +https://example.com/bot)"
FEE_HEADING_RE = re.compile(
    r"^###\s+(?:International fee|Home/UK fee|Scholarships and financial support)\s*$",
    re.M | re.I,
)
ENGLISH_HEADING_RE = re.compile(
    r"^###\s*English language requirements\s*\n.*?(?=^###\s|\Z)",
    re.M | re.I | re.S,
)
POSTGRADUATE_LEVELS = {"postgraduate", "postgraduate_research"}
MANUAL_GROUP_BY_LABEL = {
    "psychoanalytic psychotherapy": "Group 7",
    "psychodynamic psychotherapy": "Group 3",
    "social care education": "Group 3",
    "nursing studies": "Group 3",
}


def fetch_html(url: str, timeout: int = 45) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def html_to_text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return unescape(node.strip())
    parts: list[str] = []
    for child in node.children:
        if getattr(child, "name", None) in {"script", "style", "noscript"}:
            continue
        if getattr(child, "name", None) == "a":
            href = child.get("href", "")
            label = child.get_text(" ", strip=True)
            if href and label:
                parts.append(f"[{label}]({href})")
            elif label:
                parts.append(label)
            continue
        if getattr(child, "name", None) == "br":
            parts.append("")
            continue
        text = html_to_text(child)
        if text:
            parts.append(text)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def extract_english_section_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for heading in soup.find_all(re.compile(r"^h[23]$", re.I)):
        title = heading.get_text(" ", strip=True)
        if "english language requirements" not in title.casefold():
            continue
        blocks: list[str] = []
        for sibling in heading.next_siblings:
            if getattr(sibling, "name", None) in {"h2", "h3", "h4"}:
                break
            if getattr(sibling, "name", None) in {"p", "div", "ul", "ol", "li"}:
                text = html_to_text(sibling)
                if text:
                    blocks.append(text)
            elif isinstance(sibling, str):
                text = sibling.strip()
                if text:
                    blocks.append(text)
        return "\n\n".join(blocks).strip()
    return ""


def build_english_markdown(section_text: str) -> str:
    section_text = section_text.strip()
    if not section_text:
        return ""
    return f"### English language requirements\n\n{section_text}\n"


def insert_or_replace_english_section(body: str, english_md: str) -> str:
    if not english_md:
        return body
    if ENGLISH_HEADING_RE.search(body):
        return ENGLISH_HEADING_RE.sub(english_md, body, count=1)
    match = FEE_HEADING_RE.search(body)
    if match:
        return body[: match.start()] + english_md + "\n" + body[match.start() :]
    return body.rstrip() + "\n\n" + english_md


def course_label(body: str) -> str:
    match = re.search(r"\*\*Course:\*\*\s*(.+)", body, re.I)
    return match.group(1).strip() if match else ""


def course_h1(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, re.M)
    return match.group(1).strip() if match else ""


def resolve_group_name(
    *,
    body: str,
    course_name: str,
    course_level: str,
    groups: list[dict],
    english_programs: list[dict],
) -> str:
    if course_level not in POSTGRADUATE_LEVELS:
        return ""
    group = resolve_english_course_group(
        groups,
        course_name=course_name,
        course_body=body,
        course_level=course_level,
        english_programs=english_programs,
    )
    if group:
        return group
    label = Stage2Enricher.normalize_english_lookup_name(course_label(body))
    return MANUAL_GROUP_BY_LABEL.get(label, "")


def ielts_text_from_group(
    group_name: str,
    english_programs: list[dict],
) -> str:
    if not group_name:
        return ""
    program = select_english_json_program(
        english_programs,
        course_level="postgraduate",
        course_name="",
        course_body=f"English language test group: {group_name}",
    )
    overall, section = Stage2Enricher.get_ielts_from_english_program(program or {})
    return Stage2Enricher.build_course_ielts_requirement_text(overall, section)


def iter_courses_missing_ielts(courses_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for md_path in sorted(courses_dir.rglob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        fm, body = split_frontmatter(raw)
        profile = Stage2Enricher.extract_course_ielts_profile(body)
        if profile.get("overall"):
            continue
        level = (fm.get("study_level") or md_path.parent.name).strip().lower()
        rows.append(
            {
                "file": str(md_path.relative_to(courses_dir.parent)).replace("\\", "/"),
                "md_path": md_path,
                "course_url": fm.get("course_url", ""),
                "course_name": course_h1(body),
                "level": level,
                "body": body,
                "frontmatter": fm,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uni-dir", type=Path, default=_UNI_DIR)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-url-fetch", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()

    output_dir = args.uni_dir / "output"
    courses_dir = output_dir / "clean" / "courses"
    groups = ExtractionPathConfig.load_english_course_groups(output_dir)
    english_programs = parse_uni_json_payload(
        load_uni_section(output_dir, "english-requirements.md"),
        "english-requirements",
    ) or []

    rows = iter_courses_missing_ielts(courses_dir)
    if args.limit:
        rows = rows[: args.limit]

    results: list[dict] = []
    updated = 0

    for row in rows:
        url = row.get("course_url", "")
        md_path = row["md_path"]
        body = row["body"]
        fm = row["frontmatter"]
        course_level = (
            "postgraduate_research"
            if row["level"] == "postgraduate_research"
            else row["level"]
        )
        result = {
            "file": row["file"],
            "course_url": url,
            "course_name": row["course_name"],
            "status": "pending",
            "source": "",
            "english_text": "",
            "group": "",
            "profile": {},
            "error": "",
        }

        english_text = ""
        source = ""

        if url and not args.skip_url_fetch:
            try:
                html = fetch_html(url)
                english_text = extract_english_section_from_html(html)
                if english_text:
                    source = "url"
                    result["status"] = "url_fetched"
                time.sleep(args.delay)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                result["error"] = str(exc)

        if english_text:
            profile = Stage2Enricher.extract_course_ielts_profile(
                insert_or_replace_english_section(body, build_english_markdown(english_text))
            )
            if not profile.get("overall"):
                result["status"] = "url_unparsed"
        elif course_level in POSTGRADUATE_LEVELS:
            group_name = resolve_group_name(
                body=body,
                course_name=row["course_name"],
                course_level=course_level,
                groups=groups,
                english_programs=english_programs,
            )
            result["group"] = group_name
            if group_name:
                english_text = ielts_text_from_group(group_name, english_programs)
                if english_text:
                    source = "group"
                    result["status"] = "group_mapped"

        result["source"] = source
        result["english_text"] = english_text

        if not english_text:
            result["status"] = result["status"] if result["status"] != "pending" else "unresolved"
            results.append(result)
            continue

        english_md = build_english_markdown(english_text)
        new_body = insert_or_replace_english_section(body, english_md)
        profile = Stage2Enricher.extract_course_ielts_profile(new_body)
        result["profile"] = profile

        if not profile.get("overall"):
            result["status"] = "injected_unparsed"
        elif source == "group":
            result["status"] = "group_injected"
        elif source == "url":
            result["status"] = "url_injected"

        if not args.dry_run and new_body != body:
            md_path.write_text(
                CourseMarkdownCleaner.format_frontmatter(fm) + new_body.rstrip() + "\n",
                encoding="utf-8",
            )
            updated += 1

        results.append(result)

    print("=== Backfill Essex course IELTS ===")
    print(f"Missing IELTS before: {len(rows)}")
    print(f"Markdown files updated: {updated}" if not args.dry_run else "Dry run — no files updated")
    print()
    for status, count in Counter(r["status"] for r in results).most_common():
        print(f"  {status}: {count}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
