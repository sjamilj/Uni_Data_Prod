#!/usr/bin/env python3
"""Fetch missing English/IELTS sections from live Essex course URLs."""

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

from course_markdown_cleanup import CourseMarkdownCleaner  # noqa: E402
from llm_extract import Stage2Enricher  # noqa: E402
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


def load_missing_rows(report_path: Path) -> list[dict]:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return [row for row in data["rows"] if not row.get("ielts_snippet")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uni-dir", type=Path, default=_UNI_DIR)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--delay", type=float, default=0.4)
    args = parser.parse_args()

    output_dir = args.uni_dir / "output"
    report_path = args.report or output_dir / "english_ielts_variations.json"
    rows = load_missing_rows(report_path)
    if args.limit:
        rows = rows[: args.limit]

    results: list[dict] = []
    updated = 0
    fetched = 0
    parsed = 0

    for row in rows:
        url = row.get("course_url", "")
        rel = row["file"].replace("\\", "/")
        md_path = output_dir / rel
        result = {
            "file": rel,
            "course_url": url,
            "course_name": row.get("course_name", ""),
            "status": "pending",
            "english_text": "",
            "profile": {},
            "error": "",
        }
        if not url:
            result["status"] = "no_url"
            results.append(result)
            continue
        try:
            html = fetch_html(url)
            english_text = extract_english_section_from_html(html)
            result["english_text"] = english_text
            if not english_text:
                result["status"] = "no_english_on_page"
                results.append(result)
                time.sleep(args.delay)
                continue
            fetched += 1
            english_md = build_english_markdown(english_text)
            raw = md_path.read_text(encoding="utf-8")
            fm, body = split_frontmatter(raw)
            new_body = insert_or_replace_english_section(body, english_md)
            profile = Stage2Enricher.extract_course_ielts_profile(new_body)
            result["profile"] = profile
            if profile.get("overall"):
                parsed += 1
                result["status"] = "parsed"
            else:
                result["status"] = "english_found_unparsed"
            if not args.dry_run and new_body != body:
                md_path.write_text(
                    CourseMarkdownCleaner.format_frontmatter(fm) + new_body.rstrip() + "\n",
                    encoding="utf-8",
                )
                updated += 1
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            result["status"] = "fetch_error"
            result["error"] = str(exc)
        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)
        results.append(result)
        time.sleep(args.delay)

    print("=== Fetch missing IELTS from course URLs ===")
    print(f"Missing courses checked: {len(rows)}")
    print(f"English section fetched: {fetched}")
    print(f"IELTS parsed: {parsed}")
    print(f"Markdown files updated: {updated}" if not args.dry_run else "Dry run — no files updated")
    print()
    for status, count in Counter(r["status"] for r in results).most_common():
        print(f"  {status}: {count}")
    print()
    for result in results[:5]:
        if result.get("english_text"):
            print(f"- {result['course_name']}: {result['status']} -> {result.get('profile', {})}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nReport: {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
