#!/usr/bin/env python3
"""Backfill tuitionFee/currency on existing extractions without re-running LLM."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from llm_extract import enrich_stage1_from_markdown, normalize_duration_months
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


def _load_response_json(course_dir: Path, filename: str) -> dict:
    response_path = course_dir / filename
    if not response_path.is_file():
        return {}
    try:
        payload = json.loads(response_path.read_text(encoding="utf-8"))
        content = payload.get("message", {}).get("content", "")
        parsed = json.loads(content) if isinstance(content, str) and content.strip() else {}
        return parsed if isinstance(parsed, dict) else {}
    except (OSError, json.JSONDecodeError, AttributeError):
        return {}


def _load_clean_scholarship(course_dir: Path) -> dict:
    """Read the structured university scholarship record as a response fallback."""
    output_dir = next((parent for parent in course_dir.parents if parent.name == "output"), None)
    if output_dir is None:
        return {}
    path = output_dir / "clean" / "uni" / "scholarships.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^\s*\[\s*$", text)
    if not match:
        return {}
    try:
        payload, _ = json.JSONDecoder().raw_decode(text, text.index("[", match.start()))
    except json.JSONDecodeError:
        return {}
    return payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else {}


def _backfill_scholarship(course_dir: Path, output: dict) -> None:
    """Repair scholarship fields from saved responses or clean uni data, without an LLM call."""
    response = _load_response_json(course_dir, "scholarship_response.json")
    clean_record = _load_clean_scholarship(course_dir)
    raw_amount = response.get("scholarshipAmount") or clean_record.get("Amount") or ""
    amount = re.sub(r"[^\d.]", "", str(raw_amount))
    if amount:
        try:
            numeric = float(amount)
            amount = str(int(numeric)) if numeric.is_integer() else str(numeric)
        except ValueError:
            amount = ""
    if not amount:
        return

    name = str(
        output.get("scholarshipName")
        or response.get("scholarshipName")
        or clean_record.get("scholarshipName")
        or ""
    ).strip()
    currency = str(output.get("currency") or "").strip()
    symbol = "NZ$" if currency == "NZD" else "£" if currency == "GBP" else ""
    amount_display = f"{symbol}{float(amount):,.0f}" if symbol else amount

    response_meta = response.get("scholarshipMetaData")
    if clean_record:
        clean_descriptions = []
        eligibility = str(clean_record.get("Eligibility") or "").strip()
        if eligibility:
            clean_descriptions.append(eligibility)
        raw_descriptions = clean_record.get("description", [])
        if isinstance(raw_descriptions, str):
            raw_descriptions = [raw_descriptions]
        if isinstance(raw_descriptions, list):
            clean_descriptions.extend(
                str(item).strip() for item in raw_descriptions if str(item).strip()
            )
        response_meta = [{"subtitle": "Scholarships", "description": clean_descriptions}]
    if isinstance(response_meta, dict):
        response_meta = [response_meta]
    descriptions: list[str] = []
    if isinstance(response_meta, list):
        for block in response_meta:
            if not isinstance(block, dict):
                continue
            raw_description = block.get("description", [])
            if isinstance(raw_description, str):
                raw_description = [raw_description]
            if isinstance(raw_description, list):
                descriptions.extend(
                    str(item).strip()
                    for item in raw_description
                    if isinstance(item, str) and item.strip()
                )
    award_line = f"{name}: {amount_display}." if name and symbol else f"Award amount: {amount_display}."
    descriptions = [award_line] + [item for item in dict.fromkeys(descriptions) if item != award_line]
    scholarship = {
        "scholarshipName": name,
        "scholarshipAmount": amount,
        "scholarshipType": str(
            response.get("scholarshipType")
            or clean_record.get("scholarshipType")
            or output.get("scholarshipType")
            or "Amount"
        ).strip(),
        "scholarshipMetaData": [{"subtitle": "Scholarships", "description": descriptions}],
    }
    scholarship_path = course_dir / "scholarship_parsed.json"
    scholarship_path.write_text(json.dumps(scholarship, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    output.update(scholarship)


def _resolve_clean_md(output_dir: Path, study_level: str, slug: str) -> Path | None:
    candidates = [study_level]
    if study_level == "postgraduate":
        candidates.append("postgraduate_research")
    elif study_level == "postgraduate_research":
        candidates.append("postgraduate")
    for level in candidates:
        path = output_dir / "clean" / "courses" / level / f"{slug}.md"
        if path.is_file():
            return path
        pre_setup_path = output_dir / "clean" / "pre_setup_course" / level / f"{slug}.md"
        if pre_setup_path.is_file():
            return pre_setup_path
    return None


def _extraction_level_and_slug(output_dir: Path, course_dir: Path) -> tuple[str, str] | None:
    """Support regular extracts and the pre-setup sample extraction tree."""
    parts = course_dir.relative_to(output_dir / "extracted").parts
    if parts and parts[0] == "pre_setup_course_extracted":
        return (parts[1], parts[2]) if len(parts) >= 3 else None
    return (parts[0], parts[1]) if len(parts) >= 2 else None


def backfill_course_dir(output_dir: Path, course_dir: Path) -> bool:
    output_path = course_dir / "output.json"
    if not output_path.is_file():
        return False

    location = _extraction_level_and_slug(output_dir, course_dir)
    if not location:
        return False
    study_level, slug = location

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
    new_intake = str(enriched.get("intakeInfo") or "").strip()
    new_duration = normalize_duration_months(str(enriched.get("courseDuration") or ""))
    old_fee = str(output.get("tuitionFee") or "").strip()
    old_intake = str(output.get("intakeInfo") or "").strip()
    old_duration = str(output.get("courseDuration") or "").strip()

    stage1_parsed_path = course_dir / "stage1_parsed.json"
    stage1_parsed = json.loads(stage1_parsed_path.read_text(encoding="utf-8")) if stage1_parsed_path.is_file() else {}
    if not isinstance(stage1_parsed, dict):
        stage1_parsed = {}
    if new_fee:
        stage1_parsed["tuitionFee"] = new_fee
    if new_currency:
        stage1_parsed["currency"] = new_currency
    if new_intake:
        stage1_parsed["intakeInfo"] = new_intake
    if new_duration:
        stage1_parsed["courseDuration"] = new_duration
    if new_fee:
        stage1_parsed["initialDeposit"] = new_fee
    stage1_parsed_path.write_text(
        json.dumps(stage1_parsed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if new_fee:
        output["tuitionFee"] = new_fee
    if new_currency:
        output["currency"] = new_currency
    if new_fee:
        output["initialDeposit"] = new_fee
    if new_intake:
        output["intakeInfo"] = new_intake
    if new_duration:
        output["courseDuration"] = new_duration
    if new_fee and new_currency:
        output["tuitionFeeCandidates"] = [
            {"label": "INTERNATIONAL", "amount": new_fee, "currency": new_currency}
        ]
    _backfill_scholarship(course_dir, output)
    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    if new_fee != old_fee or new_intake != old_intake or new_duration != old_duration:
        rel = course_dir.relative_to(output_dir)
        print(
            f"Updated {rel}: "
            f"tuitionFee {old_fee or '(empty)'} -> {new_fee or '(empty)'}; "
            f"intakeInfo {old_intake or '(empty)'} -> {new_intake or '(empty)'}; "
            f"courseDuration {old_duration or '(empty)'} -> {new_duration or '(empty)'}"
        )
        return True
    return False


def backfill_university(code_dir: Path, *, study_levels: set[str] | None = None) -> tuple[int, int]:
    output_dir = resolve_output_dir(code_dir)
    extracted = output_dir / "extracted"
    if not extracted.is_dir():
        raise FileNotFoundError(f"No extracted/ directory under {output_dir}")

    updated = 0
    total = 0
    for output_path in sorted(extracted.rglob("output.json")):
        if study_levels:
            location = _extraction_level_and_slug(output_dir, output_path.parent)
            if not location or location[0] not in study_levels:
                continue
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
    parser.add_argument(
        "--study-level",
        action="append",
        default=[],
        metavar="LEVEL",
        help="Restrict to extracted/{level}/ (repeatable)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    code_dir = resolve_code_dir(Path(args.code_dir))
    study_levels = set(args.study_level) if args.study_level else None
    updated, total = backfill_university(code_dir, study_levels=study_levels)
    scope = f" [{', '.join(sorted(study_levels))}]" if study_levels else ""
    print(f"Backfilled stage-1 fields on {updated} / {total} extraction(s){scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
