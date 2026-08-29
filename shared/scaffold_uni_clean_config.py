#!/usr/bin/env python3
"""Apply per-university course clean profiles to code/.env and code/ENV.MD."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = Path(__file__).resolve().parent / "uni_clean_profiles.json"
TEMPLATE_CLEANUP = REPO_ROOT / "_university_template" / "code" / "course_markdown_cleanup.py"

CLEAN_KEYS = (
    "COURSE_PAGE_TITLE_SELECTOR",
    "COURSE_CLEAN_ENGINE",
    "COURSE_CLEAN_BLOCKS",
    "COURSE_CLEAN_STRIP_WITHIN",
    "COURSE_CLEAN_EXPAND_TABS",
    "COURSE_MARKDOWN_REMOVE_SECTIONS",
    "UNI_REQ_SOURCE_URLS",
)

STANDARD_MARKDOWN_REMOVE = """
2 :: Latest news
2 :: Be part of our community
2 :: Alumni services
2 :: *Read more news*
4 :: With placement
4 :: With foundation year
4 :: Important additional notes
4 :: *part-time*
3 :: UK students
3 :: Contextual offers
3 :: Living costs
5 :: UK students*
5 :: *part-time*
""".strip()

DEFAULT_STRIP = ["script", "noscript"]


def _load_profiles() -> dict:
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


def _strip_clean_keys(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        matched = False
        for key in CLEAN_KEYS:
            if re.match(rf"^{re.escape(key)}\s*=", line):
                matched = True
                index += 1
                if '="' in line or "='" in line:
                    quote = '"' if '="' in line else "'"
                    while index < len(lines) and quote not in lines[index - 1]:
                        index += 1
                break
        if not matched:
            out.append(line)
            index += 1
    trimmed = "\n".join(out).rstrip()
    trimmed = re.sub(
        r"\n# --- Course page cleaning.*$",
        "",
        trimmed,
        flags=re.DOTALL,
    )
    return trimmed.rstrip() + "\n"


def _quote_block(lines: list[str]) -> str:
    body = "\n".join(lines)
    return f'"\n{body}\n"'


def _uni_req_urls(uni_dir: Path) -> list[str]:
    urls: list[str] = []
    uni_md = uni_dir / "output" / "clean" / "uni"
    if not uni_md.is_dir():
        return urls
    for path in sorted(uni_md.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^source_url:\s*(\S+)", text, re.MULTILINE)
        if match:
            urls.append(f"{path.stem} :: {match.group(1)}")
    return urls


def _fix_paths(text: str, uni_dir: Path) -> str:
    from portable_paths import relativize_html_value

    _ = uni_dir
    key_re = re.compile(
        r"^(?P<pre>\s*#?\s*)(?P<key>[A-Z_]*COURSE_CATALOGUE_HTML)=(?P<val>.*)$"
    )

    def replace_line(match: re.Match[str]) -> str:
        raw = match.group("val").strip()
        if not raw or raw.startswith("http"):
            return match.group(0)
        return f"{match.group('pre')}{match.group('key')}={relativize_html_value(raw)}"

    return "\n".join(
        key_re.sub(replace_line, line) for line in text.splitlines()
    ) + ("\n" if text.endswith("\n") else "")


def _build_clean_section(profile: dict, uni_dir: Path) -> str:
    title = profile.get("title", "")
    expand = "true" if profile.get("expand_tabs", True) else "false"
    blocks = profile.get("blocks") or ["Course overview :: #main-content"]
    strip = list(dict.fromkeys([*DEFAULT_STRIP, *profile.get("strip", [])]))
    uni_req = _uni_req_urls(uni_dir)
    if not uni_req:
        uni_req = [
            "bangladesh-entry ::",
            "english-requirements ::",
            "scholarships ::",
            "deposit ::",
        ]

    lines = [
        "",
        "# --- Course page cleaning (download_and_clean_course_pages.py — course_detail/) ---",
        "",
        f"COURSE_PAGE_TITLE_SELECTOR={title}",
        "",
        "# generic (default) | utopian (ARU) | plugin | auto",
        "COURSE_CLEAN_ENGINE=generic",
        "",
        "# One CSS selector per line; optional heading with :: or |",
        f"COURSE_CLEAN_BLOCKS={_quote_block(blocks)}",
        "",
        "# Noise removed inside each matched block before markdown conversion",
        f"COURSE_CLEAN_STRIP_WITHIN={_quote_block(strip)}",
        "",
        f"COURSE_CLEAN_EXPAND_TABS={expand}",
        "",
        "# --- Course markdown cleanup (shared/course_markdown_cleanup.py) ---",
        f"COURSE_MARKDOWN_REMOVE_SECTIONS={_quote_block(STANDARD_MARKDOWN_REMOVE.splitlines())}",
        "",
        "UNI_REQ_SOURCE_URLS=" + _quote_block(uni_req),
        "",
    ]
    return "\n".join(lines)


def scaffold_university(uni_dir: Path, profiles: dict, *, dry_run: bool = False) -> str:
    name = uni_dir.name
    code_dir = uni_dir / "code"
    env_md = code_dir / "ENV.MD"
    env_file = code_dir / ".env"
    cleanup_py = code_dir / "course_markdown_cleanup.py"

    if not env_md.is_file():
        return "skip (no ENV.MD)"

    profile = profiles.get(name, {})
    if profile.get("skip"):
        if not env_file.is_file() and env_md.is_file():
            if not dry_run:
                env_file.write_text(_fix_paths(env_md.read_text(encoding="utf-8"), uni_dir), encoding="utf-8")
        if not cleanup_py.is_file() and not dry_run:
            shutil.copy2(TEMPLATE_CLEANUP, cleanup_py)
        return "skip (already configured)"

    base = _strip_clean_keys(_fix_paths(env_md.read_text(encoding="utf-8"), uni_dir))
    updated = base + _build_clean_section(profile, uni_dir)

    if not dry_run:
        env_md.write_text(updated, encoding="utf-8")
        env_file.write_text(updated, encoding="utf-8")
        if not cleanup_py.is_file():
            shutil.copy2(TEMPLATE_CLEANUP, cleanup_py)

    return "updated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--university", action="append", help="Limit to one or more university folders")
    args = parser.parse_args()

    profiles = _load_profiles()
    targets: list[Path] = []
    if args.university:
        for name in args.university:
            targets.append(REPO_ROOT / name)
    else:
        for path in sorted(REPO_ROOT.iterdir()):
            if path.is_dir() and (path / "code" / "ENV.MD").is_file():
                if path.name not in {"shared", "dashboard", "_university_template"}:
                    targets.append(path)

    updated = 0
    for uni_dir in targets:
        status = scaffold_university(uni_dir, profiles, dry_run=args.dry_run)
        print(f"{uni_dir.name}: {status}")
        if status == "updated":
            updated += 1

    print(f"\nDone: {updated} updated, {len(targets)} scanned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
