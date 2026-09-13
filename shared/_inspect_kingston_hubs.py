"""Inspect Kingston hub foundation pages vs linked course URLs in CSVs."""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "Kingston University" / "output"
_BASE = "https://www.kingston.ac.uk"

# Route-selector / integrated foundation year hub pages
HUB_PATH_RES = (
    re.compile(r"^/study/foundation/foundation-year-in-", re.I),
    re.compile(r"^/study/undergraduate/(?:midwifery|nursing|science)-foundation-year", re.I),
)

FILES = {
    "course_urls": _OUT / "course_urls.csv",
    "foundation": _OUT / "foundation_course_urls.csv",
    "undergraduate": _OUT / "undergraduate_course_urls.csv",
    "postgraduate": _OUT / "postgraduate_course_urls.csv",
    "postgraduate_research": _OUT / "postgraduate_research_course_urls.csv",
}


def load_urls(path: Path) -> list[str]:
    urls: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            url = (row.get("course_url") or row.get("url") or "").strip()
            if url:
                urls.append(url)
    return urls


def path_key(url: str) -> str:
    return urlparse(url).path.rstrip("/").lower()


def is_hub(url: str) -> bool:
    path = urlparse(url).path.rstrip("/")
    return any(p.search(path) for p in HUB_PATH_RES)


def extract_linked_paths(html: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    paths: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        resolved = urljoin(_BASE, href)
        parsed = urlparse(resolved)
        if parsed.netloc.replace("www.", "") != "kingston.ac.uk":
            continue
        path = parsed.path.rstrip("/")
        if re.search(
            r"^/study/(?:undergraduate|postgraduate|foundation|degree-apprenticeship)/",
            path,
            re.I,
        ):
            paths.add(path.lower())
    return paths


def find_html_for_url(url: str) -> Path | None:
    slug = path_key(url).replace("/study/", "").replace("/", "_")
    pages_dir = _OUT / "course_pages"
    if not pages_dir.is_dir():
        return None
    candidates = list(pages_dir.glob(f"*{slug}*.html"))
    if candidates:
        return candidates[0]
    # Title-based saves e.g. "Foundation Year in Engineering _ Kingston..."
    fragment = urlparse(url).path.rsplit("/", 1)[-1].replace("-", " ")
    for path in pages_dir.glob("*.html"):
        if fragment.lower() in path.stem.lower():
            return path
    return None


def main() -> int:
    all_urls: set[str] = set()
    by_file: dict[str, list[str]] = {}
    for name, path in FILES.items():
        if not path.is_file():
            print(f"Missing: {path}", file=sys.stderr)
            return 1
        urls = load_urls(path)
        by_file[name] = urls
        all_urls.update(urls)

    all_paths = {path_key(u) for u in all_urls}
    hubs = sorted(u for u in all_urls if is_hub(u))

    print("=== Kingston hub page inventory ===")
    print(f"Unique URLs (course_urls.csv): {len(by_file['course_urls'])}")
    for name, urls in by_file.items():
        hub_in_file = [u for u in urls if is_hub(u)]
        print(f"  {name}: {len(urls)} total, {len(hub_in_file)} hub pages")
    print(f"\nUnique hub pages (pattern): {len(hubs)}")
    for hub in hubs:
        print(f"  {hub}")

    print("\n=== Linked courses from hub HTML (fees / route sections) ===")
    total_linked = 0
    total_missing = 0
    total_already = 0
    no_html = 0

    for hub in hubs:
        html_path = find_html_for_url(hub)
        if html_path is None:
            print(f"\n{hub}")
            print("  HTML: not on disk — skip link extraction")
            no_html += 1
            continue

        html = html_path.read_text(encoding="utf-8", errors="replace")
        if "just a moment" in html_path.stem.lower() or "cf-challenge" in html[:5000].lower():
            print(f"\n{hub}")
            print(f"  HTML: {html_path.name} (Cloudflare — skip)")
            no_html += 1
            continue

        linked = extract_linked_paths(html)
        # Drop self-references and other hub pages
        hub_path = path_key(hub)
        linked = {
            p
            for p in linked
            if p != hub_path and not is_hub(f"{_BASE}{p}")
        }
        missing = sorted(p for p in linked if p not in all_paths)
        present = sorted(p for p in linked if p in all_paths)

        print(f"\n{hub}")
        print(f"  HTML: {html_path.name}")
        print(f"  Linked course paths found: {len(linked)}")
        print(f"  Already in CSV: {len(present)}")
        print(f"  NOT in CSV: {len(missing)}")
        if missing:
            for p in missing[:15]:
                print(f"    MISSING  {_BASE}{p}")
            if len(missing) > 15:
                print(f"    ... +{len(missing) - 15} more")
        total_linked += len(linked)
        total_missing += len(missing)
        total_already += len(present)

    print("\n=== Summary ===")
    print(f"Hub pages: {len(hubs)}")
    print(f"Hubs with usable HTML: {len(hubs) - no_html}")
    print(f"Linked paths extracted: {total_linked}")
    print(f"Already in catalogue: {total_already}")
    print(f"Missing from catalogue: {total_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
