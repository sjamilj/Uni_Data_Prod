#!/usr/bin/env python3
"""Backfill tuitionFee/currency on existing extractions without re-running LLM."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from llm_extract import enrich_stage1_from_markdown
from uni_pages import split_frontmatter
from uni_paths import resolve_code_dir, resolve_output_dir


def _load_stage1_llm_json(course_dir: Path) -> dict:
    response_path = course_dir / "stage1_response.json"
    if response_path.is_file():
        payload = json.loads(response_path.read_text(encoding="utf-8"))
        content = payload.get("message", {}).get("content", "")
        if isinstance(content, str) and content.strip():
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
    parsed_path = course_dir / "stage1_parsed.json"
    if parsed_path.is_file():
        parsed = json.loads(parsed_path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            return parsed
    return {}


def _resolve_clean_md(output_dir: Path, study_level: str, slug: str) -> Path | None:
    path = output_dir / "clean" / "courses" / study_level / f"{slug}.md"
    return path if path.is_file() else None


def backfill_course_dir(output_dir: Path, course_dir: Path) -> bool:
    output_path = course_dir / "output.json"
    if not output_path.is_file():
        return False

    parts = course_dir.relative_to(output_dir / "extracted").parts
    if len(parts) < 2:
        return False
    study_level, slug = parts[0], parts[1]

    md_path = _resolve_clean_md(output_dir, study_level, slug)
    if not md_path:
        print(f"SKIP no markdown: {course_dir.relative_to(output_dir)}", file=sys.stderr)
        return False

    meta, course_body = split_frontmatter(md_path.read_text(encoding="utf-8"))
    output = json.loads(output_path.read_text(encoding="utf-8"))
    course_name = str(output.get("courseName") or "").strip()
    course_url = str(output.get("courseUrl") or output.get("courseUrlExternal") or "").strip()
    if not course_url:
        course_url = str(meta.get("course_url", "") or meta.get("source_url", "")).strip()

    stage1_llm = _load_stage1_llm_json(course_dir)
    enriched = enrich_stage1_from_markdown(
        stage1_llm,
        course_body=course_body,
        course_name=course_name,
        course_url=course_url,
    )

    new_fee = str(enriched.get("tuitionFee") or "").strip()
    new_currency = str(enriched.get("currency") or "").strip()
    old_fee = str(output.get("tuitionFee") or "").strip()

    stage1_parsed_path = course_dir / "stage1_parsed.json"
    stage1_parsed = json.loads(stage1_parsed_path.read_text(encoding="utf-8")) if stage1_parsed_path.is_file() else {}
    if not isinstance(stage1_parsed, dict):
        stage1_parsed = {}
    stage1_parsed.update(
        {
            "tuitionFee": new_fee,
            "currency": new_currency,
            "feesMetaData": enriched.get("feesMetaData", stage1_parsed.get("feesMetaData", [])),
            "intakeInfo": enriched.get("intakeInfo", stage1_parsed.get("intakeInfo", "")),
            "courseDuration": enriched.get("courseDuration", stage1_parsed.get("courseDuration", "")),
        }
    )
    stage1_parsed_path.write_text(
        json.dumps(stage1_parsed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    output["tuitionFee"] = new_fee
    output["currency"] = new_currency
    if new_fee and new_currency:
        output["tuitionFeeCandidates"] = [
            {"label": "INTERNATIONAL", "amount": new_fee, "currency": new_currency}
        ]
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    if new_fee != old_fee:
        rel = course_dir.relative_to(output_dir)
        print(f"Updated {rel}: tuitionFee {old_fee or '(empty)'} -> {new_fee}")
        return True
    return False


def backfill_university(code_dir: Path) -> tuple[int, int]:
    output_dir = resolve_output_dir(code_dir)
    extracted = output_dir / "extracted"
    if not extracted.is_dir():
        raise FileNotFoundError(f"No extracted/ directory under {output_dir}")

    updated = 0
    total = 0
    for output_path in sorted(extracted.rglob("output.json")):
        total += 1
        if backfill_course_dir(output_dir, output_path.parent):
            updated += 1
    return updated, total


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill tuitionFee/currency from markdown + stage1_response feesMetaData."
    )
    parser.add_argument(
        "code_dir",
        nargs="?",
        default=".",
        help="University code/ directory (default: cwd)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    code_dir = resolve_code_dir(Path(args.code_dir))
    updated, total = backfill_university(code_dir)
    print(f"Backfilled tuitionFee on {updated} / {total} extraction(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
