#!/usr/bin/env python3
"""Analyze a university catalogue HTML page and suggest .env match rules.

Works for any UK uni listing / search HTML (browser Save-As or Playwright dump).

Strategy:
  1) Group same-domain links by URL shape (path template)
  2) Keep the largest groups as COURSE_PATH_PATTERNS
  3) Find a CSS parent selector that best covers those course links
  4) Suggest EXCLUDED_* for hubs / chrome

Examples:
  python analyze_catalogue_html.py path/to/listing.html
  python analyze_catalogue_html.py path/to/listing.html --write-env path/to/.env
  python analyze_catalogue_html.py path/to/listing.html --min-group 8 --show 20
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

SAVED_URL_RE = re.compile(
    r"<!-- saved from url=\(\d*\)(https?://[^\s>]+)", re.I
)
CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', re.I
)
BASE_HREF_RE = re.compile(r'<base[^>]+href=["\']([^"\']+)["\']', re.I)

NOISE_FRAGMENTS = (
    "about",
    "alumni",
    "cookie",
    "contact",
    "events",
    "news",
    "newsroom",
    "research",
    "login",
    "account",
    "open-day",
    "open-days",
    "prospectus",
    "clearing-advantage",
    "privacy",
    "terms",
    "accessibility",
    "sitemap",
    "staff",
    "vacancy",
    "vacancies",
    "advice-",
    "campus-life",
    "current-students",
    "why-",
)

DEFAULT_EXCLUDED_PREFIXES = (
    "/bookmarked-courses",
    "/clearing/",
    "/international/",
    "/about/",
    "/about-us/",
    "/news/",
    "/events/",
    "/research/",
    "/our-research/",
    "/alumni",
    "/current-students/",
    "/student-life/",
    "/partners/",
    "/site-search",
    "/newsroom/",
)

COURSEISH_ROOTS = {
    "undergraduate",
    "postgraduate",
    "undergrad",
    "postgrad",
    "courses",
    "course",
    "online",
    "apprenticeships",
    "apprenticeship",
    "short-courses-cpd",
    "further-education",
    "programmes",
    "programs",
    "programme",
    "program",
    "ug",
    "pg",
    "mineral-products",
    "study",
}

WEAK_BROAD_ROOTS = {
    "study",
    "student-life",
    "your-career",
    "life",
    "about",
    "services",
}

LIST_ITEM_HINTS = (
    "result",
    "course",
    "programme",
    "program",
    "listing",
    "card",
    "teaser",
    "views-row",
    "a-z",
    "catalogue",
    "catalog",
    "item",
    "row",
)

MENU_HINTS = (
    "menu",
    "nav",
    "footer",
    "header",
    "breadcrumb",
    "social",
    "cookie",
)


@dataclass
class LinkInfo:
    href: str
    path: str
    text: str
    classes_chain: list[str] = field(default_factory=list)


def infer_base_url(html: str, html_path: Path | None = None) -> str:
    head = html[:12000]
    for pattern in (SAVED_URL_RE, CANONICAL_RE, BASE_HREF_RE):
        match = pattern.search(head)
        if match:
            raw = match.group(1).strip()
            parsed = urlparse(raw)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"

    soup = BeautifulSoup(html, "html.parser")
    domains: Counter[str] = Counter()
    schemes: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href.startswith("http"):
            continue
        parsed = urlparse(href)
        if parsed.netloc:
            host = parsed.netloc.lower()
            # Prefer primary www./apex academic hosts over portals/CDNs
            weight = 1
            if host.startswith("www."):
                weight = 3
            elif host.count(".") == 1 or host.endswith(".ac.uk"):
                weight = 2
            domains[host] += weight
            schemes.setdefault(host, parsed.scheme or "https")
    if domains:
        host = domains.most_common(1)[0][0]
        return f"{schemes.get(host, 'https')}://{host}"

    raise SystemExit(
        f"Could not infer university domain from {html_path}. "
        "Pass --base-url https://www.example.ac.uk/"
    )


def css_escape_ident(value: str) -> str:
    return re.sub(r"([^a-zA-Z0-9_-])", r"\\\1", value)


def ancestor_class_selectors(tag, limit: int = 8) -> list[str]:
    selectors: list[str] = []
    node = tag.parent
    depth = 0
    while node is not None and getattr(node, "name", None) and depth < limit:
        classes = [c for c in (node.get("class") or []) if c and len(c) < 80]
        for cls in classes:
            selectors.append(f".{css_escape_ident(cls)}")
        node = getattr(node, "parent", None)
        depth += 1
    return selectors


def normalize_path(path: str) -> str:
    path = (path or "").strip()
    if not path:
        return "/"
    return path.rstrip("/") or "/"


def path_depth(path: str) -> int:
    return len([p for p in normalize_path(path).split("/") if p])


def path_template(path: str) -> str | None:
    """ /a/b/course-slug -> ^/a/b/[^/]+$  (needs depth >= 3 for course pages). """
    parts = [p for p in normalize_path(path).split("/") if p]
    if len(parts) < 3:
        return None
    prefix = "/" + "/".join(parts[:-1])
    return f"^{re.escape(prefix)}/[^/]+$"


def broad_path_template(path: str) -> str | None:
    """ /undergraduate/nursing-courses/slug -> ^/undergraduate/[^/]+/[^/]+$ """
    parts = [p for p in normalize_path(path).split("/") if p]
    if len(parts) < 3:
        return None
    # Keep first segment; wildcard the rest of the folder chain except require final slug
    if len(parts) == 3:
        return f"^{re.escape('/' + parts[0])}/[^/]+/[^/]+$"
    # depth 4+: /further-education/courses/area/slug
    return f"^{re.escape('/' + parts[0])}/" + "/".join(["[^/]+"] * (len(parts) - 1)) + "$"


def is_noise_path(path: str) -> bool:
    lower = normalize_path(path).lower()
    if lower in {"/", "/courses", "/study", "/search", "/site-search"}:
        return True
    return any(frag in lower for frag in NOISE_FRAGMENTS)


def collect_links(html: str, base_url: str) -> list[LinkInfo]:
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(base_url).netloc.lower()
    links: list[LinkInfo] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:"):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.netloc.lower() != domain:
            continue
        path = normalize_path(parsed.path)
        key = f"{parsed.scheme}://{parsed.netloc}{path}"
        if key in seen:
            continue
        seen.add(key)
        links.append(
            LinkInfo(
                href=key,
                path=path,
                text=anchor.get_text(" ", strip=True)[:120],
                classes_chain=ancestor_class_selectors(anchor),
            )
        )
    return links


def suggest_path_patterns(
    links: list[LinkInfo],
    min_group: int,
) -> list[tuple[str, int, list[str]]]:
    specific_groups: dict[str, list[LinkInfo]] = defaultdict(list)
    broad_groups: dict[str, list[LinkInfo]] = defaultdict(list)

    for link in links:
        if is_noise_path(link.path):
            continue
        specific = path_template(link.path)
        broad = broad_path_template(link.path)
        if specific:
            specific_groups[specific].append(link)
        if broad:
            broad_groups[broad].append(link)

    def rank(groups: dict[str, list[LinkInfo]]) -> list[tuple[str, int, list[str]]]:
        ranked = sorted(
            (
                (
                    template,
                    len({item.path for item in items}),
                    [item.path for item in items[:5]],
                )
                for template, items in groups.items()
            ),
            key=lambda row: (-row[1], row[0]),
        )
        return [row for row in ranked if row[1] >= min_group]

    broad_ranked = rank(broad_groups)
    specific_ranked = rank(specific_groups)

    # Prefer a small set of broad patterns when they cover the page well
    selected: list[tuple[str, int, list[str]]] = []
    covered_paths: set[str] = set()

    for template, count, samples in broad_ranked:
        # Extract first path segment from ^/segment/...
        first = ""
        m = re.match(r"\^/([^/\\]+)", template.replace("\\", ""))
        if m:
            first = m.group(1).lower()
        if first in WEAK_BROAD_ROOTS and count < max(20, min_group * 4):
            continue
        if first and first not in COURSEISH_ROOTS and count < max(15, min_group * 3):
            continue

        rx = re.compile(template, re.I)
        new_paths = {
            link.path
            for link in links
            if rx.search(link.path) and not is_noise_path(link.path)
        }
        # If all matches share one middle folder, prefer the specific template
        middles = set()
        example_path = ""
        for path in new_paths:
            parts = [p for p in path.split("/") if p]
            if len(parts) >= 2:
                middles.add(parts[1])
                example_path = path
        if len(middles) == 1 and example_path:
            specific = path_template(example_path)
            if specific:
                specific_count = len(
                    {link.path for link in specific_groups.get(specific, [])}
                ) or len(new_paths)
                selected.append((specific, specific_count, samples))
                covered_paths |= new_paths
                if len(selected) >= 8:
                    break
                continue

        if len(new_paths - covered_paths) < min_group and selected:
            continue
        selected.append((template, count, samples))
        covered_paths |= new_paths
        if len(selected) >= 8:
            break

    # Add specific patterns only for leftovers not covered by broad ones
    if selected:
        compiled = [re.compile(t, re.I) for t, _, _ in selected]
        for template, count, samples in specific_ranked:
            if any(rx.search(samples[0]) for rx in compiled if samples):
                continue
            selected.append((template, count, samples))
            if len(selected) >= 10:
                break
        return selected

    if specific_ranked:
        return specific_ranked[:10]

    # Fallback: allow depth-2 templates if nothing deeper exists
    shallow: dict[str, list[LinkInfo]] = defaultdict(list)
    for link in links:
        if is_noise_path(link.path):
            continue
        parts = [p for p in link.path.split("/") if p]
        if len(parts) != 2:
            continue
        template = f"^{re.escape('/' + parts[0])}/[^/]+$"
        shallow[template].append(link)
    return rank(shallow)


def selector_quality(selector: str) -> float:
    lower = selector.lower()
    score = 1.0
    if any(h in lower for h in LIST_ITEM_HINTS):
        score += 2.0
    if any(h in lower for h in MENU_HINTS):
        score -= 3.0
    if "js-" in lower and "result" not in lower and "course" not in lower:
        score -= 0.5
    return score


def suggest_link_selector(
    links: list[LinkInfo],
    patterns: list[str],
    min_group: int,
) -> str | None:
    if not patterns:
        return None
    compiled = [re.compile(p, re.I) for p in patterns]
    course_links = [
        link for link in links if any(rx.search(link.path) for rx in compiled)
    ]
    if len(course_links) < max(2, min_group // 2):
        return None

    class_hits: Counter[str] = Counter()
    for link in course_links:
        for selector in link.classes_chain:
            class_hits[selector] += 1

    ranked: list[tuple[float, str, int]] = []
    total = len(course_links)
    for selector, hit_count in class_hits.most_common(100):
        if hit_count < max(2, min_group // 2):
            continue
        coverage = hit_count / total
        # Penalize selectors that also wrap lots of non-course links
        non_course = sum(
            1
            for link in links
            if selector in link.classes_chain
            and not any(rx.search(link.path) for rx in compiled)
        )
        purity = hit_count / max(1, hit_count + non_course)
        score = (
            hit_count * selector_quality(selector)
            + coverage * 20
            + purity * 30
        )
        ranked.append((score, selector, hit_count))

    if not ranked:
        return None
    ranked.sort(reverse=True)

    # Prefer item/row/card when coverage is still strong
    best = ranked[0][1]
    for score, selector, hit_count in ranked[:15]:
        lower = selector.lower()
        if any(x in lower for x in ("item", "row", "card", "result", "course", "teaser")):
            if hit_count >= max(2, int(total * 0.5)):
                best = selector
                break
    return f"{best} a[href]"


def suggest_exclusions(
    links: list[LinkInfo],
    patterns: list[str],
) -> tuple[list[str], list[str]]:
    compiled = [re.compile(p, re.I) for p in patterns]
    excluded_paths: set[str] = set()

    for pattern in patterns:
        match = re.match(r"\^(/[\w\-./]+)/\[\^/\]\+\$", pattern)
        if match:
            excluded_paths.add(match.group(1).rstrip("/"))

    path_counts = Counter(link.path for link in links)
    for path, count in path_counts.most_common(100):
        if any(rx.search(path) for rx in compiled):
            continue
        if path_depth(path) <= 3 and (count >= 2 or is_noise_path(path)):
            excluded_paths.add(path)

    for path in list(excluded_paths):
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            excluded_paths.add("/" + "/".join(parts[:2]))

    prefixes = list(DEFAULT_EXCLUDED_PREFIXES)
    for link in links:
        parts = [p for p in link.path.split("/") if p]
        if not parts:
            continue
        top = parts[0].lower()
        if top in {
            "about",
            "about-us",
            "about-uel",
            "news",
            "newsroom",
            "events",
            "research",
            "our-research",
            "partners",
            "international",
            "clearing",
            "student-life",
            "alumni",
            "your-career",
        }:
            prefixes.append(f"/{parts[0]}/")

    # Never exclude actual matched course paths
    excluded_paths = {
        p
        for p in excluded_paths
        if p
        and p != "/"
        and not any(rx.search(p) for rx in compiled)
    }

    excluded_sorted = sorted(excluded_paths, key=lambda s: (s.count("/"), s))[:35]
    prefix_sorted = sorted(set(prefixes), key=str.lower)
    return excluded_sorted, prefix_sorted


def format_env_block(
    base_url: str,
    selector: str | None,
    patterns: list[str],
    excluded_paths: list[str],
    excluded_prefixes: list[str],
) -> str:
    def multiline(key: str, values: list[str]) -> str:
        if not values:
            return f"#{key}=\n"
        inner = "\n".join(values)
        return f'{key}="\n{inner}\n"\n'

    lines = [
        f"UNIVERSITY_BASE_URL={base_url.rstrip('/')}/",
        "",
        "# Only scan these anchors (leave blank = all <a href>)",
        f"COURSE_LINK_SELECTOR={selector}" if selector else "#COURSE_LINK_SELECTOR=",
        "",
        "# Path regexes that identify a course page",
        multiline("COURSE_PATH_PATTERNS", patterns).rstrip(),
        "",
        "# Exact paths to skip (hub / utility pages)",
        multiline("EXCLUDED_COURSE_PATHS", excluded_paths).rstrip(),
        "",
        "# Path prefixes to skip",
        multiline("EXCLUDED_PATH_PREFIXES", excluded_prefixes).rstrip(),
        "",
    ]
    return "\n".join(lines) + "\n"


def merge_into_env(env_path: Path, block: str) -> None:
    keys = {
        "UNIVERSITY_BASE_URL",
        "COURSE_LINK_SELECTOR",
        "COURSE_PATH_PATTERNS",
        "EXCLUDED_COURSE_PATHS",
        "EXCLUDED_PATH_PREFIXES",
    }
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = original.splitlines(keepends=True)
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in keys:
                value = stripped.split("=", 1)[1].strip()
                if (value.startswith('"') and not (len(value) >= 2 and value.endswith('"'))) or (
                    value.startswith("'") and not (len(value) >= 2 and value.endswith("'"))
                ):
                    quote = value[0]
                    index += 1
                    while index < len(lines) and not lines[index].rstrip().endswith(quote):
                        index += 1
                index += 1
                continue
        kept.append(line)
        index += 1

    text = "".join(kept).rstrip() + "\n\n# --- auto-suggested match rules ---\n" + block
    env_path.write_text(text, encoding="utf-8")


def analyze(
    html_path: Path,
    base_url: str | None,
    min_group: int,
    show: int,
) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="replace")
    resolved_base = (base_url or infer_base_url(html, html_path)).rstrip("/") + "/"
    domain = urlparse(resolved_base).netloc.lower()
    links = collect_links(html, resolved_base)

    pattern_rows = suggest_path_patterns(links, min_group=min_group)
    patterns = [row[0] for row in pattern_rows[:8]]
    selector = suggest_link_selector(links, patterns, min_group=min_group)
    excluded_paths, excluded_prefixes = suggest_exclusions(links, patterns)
    block = format_env_block(
        resolved_base,
        selector,
        patterns,
        excluded_paths,
        excluded_prefixes,
    )

    compiled = [re.compile(p, re.I) for p in patterns]
    samples = [
        (link.path, link.text)
        for link in links
        if any(rx.search(link.path) for rx in compiled)
    ][:show]

    return {
        "html_path": str(html_path),
        "base_url": resolved_base,
        "domain": domain,
        "total_same_domain_links": len(links),
        "selector": selector,
        "pattern_rows": pattern_rows,
        "patterns": patterns,
        "excluded_paths": excluded_paths,
        "excluded_prefixes": excluded_prefixes,
        "block": block,
        "sample_links": samples,
    }


def print_report(result: dict, show: int) -> None:
    print(f"HTML: {result['html_path']}")
    print(f"Base URL: {result['base_url']}")
    print(f"Same-domain links: {result['total_same_domain_links']}")
    print()
    print("Suggested COURSE_LINK_SELECTOR:")
    print(f"  {result['selector'] or '(none — scan all anchors)'}")
    print()
    print("Suggested COURSE_PATH_PATTERNS (count = unique paths):")
    if not result["pattern_rows"]:
        print("  (none found — try --min-group 3, or re-save HTML after courses load)")
    for template, count, samples in result["pattern_rows"][:8]:
        print(f"  {count:4d}  {template}")
        for sample in samples[:3]:
            print(f"         e.g. {sample}")
    print()
    print("Sample matched course paths:")
    for path, text in result["sample_links"][:show]:
        label = f" — {text}" if text else ""
        print(f"  {path}{label}")
    print()
    print("=" * 60)
    print("Paste into your strategy .env:")
    print("=" * 60)
    print(result["block"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest COURSE_* .env match rules from a catalogue HTML page."
    )
    parser.add_argument("html", type=Path, help="Path to saved listing / search HTML")
    parser.add_argument(
        "--base-url",
        default="",
        help="University origin, e.g. https://www.uel.ac.uk/ (auto-detected if omitted)",
    )
    parser.add_argument(
        "--min-group",
        type=int,
        default=5,
        help="Minimum unique URLs for a path pattern group (default 5)",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=15,
        help="How many sample course links to print",
    )
    parser.add_argument(
        "--write-env",
        type=Path,
        default=None,
        help="Merge suggested keys into this .env file",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Also write the suggested block to a text file",
    )
    args = parser.parse_args()

    if not args.html.is_file():
        print(f"HTML not found: {args.html}", file=sys.stderr)
        return 1

    result = analyze(
        args.html,
        base_url=args.base_url.strip() or None,
        min_group=max(2, args.min_group),
        show=args.show,
    )
    print_report(result, show=args.show)

    if args.out:
        args.out.write_text(result["block"], encoding="utf-8")
        print(f"Wrote suggested block -> {args.out}")
    if args.write_env:
        merge_into_env(args.write_env, result["block"])
        print(f"Updated match rules in -> {args.write_env}")

    return 0 if result["patterns"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
