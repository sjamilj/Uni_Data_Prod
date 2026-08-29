"""HTML fragment to markdown conversion (shared by download + engines)."""

from __future__ import annotations

import re
from html import unescape

from bs4 import BeautifulSoup, NavigableString, Tag

MAIN_SELECTORS = (
    "main",
    "article",
    '[role="main"]',
    "#content",
    "#main-content",
    ".main-content",
    ".whole-content",
    ".page-content",
    ".field-body",
)

REMOVE_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "svg",
        "iframe",
        "link",
        "meta",
        "nav",
        "header",
        "footer",
        "form",
        "button",
        "input",
        "select",
        "textarea",
        "head",
    }
)


class Utils:
    @staticmethod
    def slug_from_filename(stem: str) -> str:
        slug = re.sub(r"[^\w\-]+", "-", stem).strip("-").lower()
        return slug[:160] or "page"

    @staticmethod
    def normalise_text(text: str) -> str:
        text = unescape(text)
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class MarkdownConverter:
    """HTML fragment → markdown."""

    @staticmethod
    def strip_attributes(root: Tag) -> None:
        for tag in root.find_all(True):
            keep = {}
            if tag.attrs:
                if tag.name == "a" and tag.get("href"):
                    keep["href"] = tag["href"]
                if tag.name in {"td", "th"}:
                    if tag.get("colspan"):
                        keep["colspan"] = tag["colspan"]
                    if tag.get("rowspan"):
                        keep["rowspan"] = tag["rowspan"]
            tag.attrs = keep

    @staticmethod
    def inline_text(node: Tag | NavigableString) -> str:
        if isinstance(node, NavigableString):
            return str(node)
        if node.name == "a":
            label = node.get_text(" ", strip=True)
            href = node.get("href", "").strip()
            if label and href and not href.startswith(("#", "javascript:")):
                return f"[{label}]({href})"
            return label
        if node.name == "br":
            return "\n"
        return node.get_text(" ", strip=True)

    @classmethod
    def table_to_markdown(cls, table: Tag) -> str:
        rows: list[list[str]] = []
        for tr in table.find_all("tr"):
            cells = [
                re.sub(r"\s+", " ", td.get_text(" ", strip=True))
                for td in tr.find_all(["th", "td"])
            ]
            if any(cells):
                rows.append(cells)
        if not rows:
            return ""

        width = max(len(row) for row in rows)
        lines = []
        header = rows[0] + [""] * (width - len(rows[0]))
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * width) + " |")
        for row in rows[1:]:
            padded = row + [""] * (width - len(row))
            lines.append("| " + " | ".join(padded[:width]) + " |")
        return "\n".join(lines)

    @classmethod
    def node_to_markdown(cls, node: Tag | NavigableString, list_depth: int = 0) -> str:
        if isinstance(node, NavigableString):
            text = re.sub(r"\s+", " ", str(node))
            return text.strip()

        if not isinstance(node, Tag):
            return ""

        name = node.name.lower()
        if name in REMOVE_TAGS:
            return ""

        if name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(name[1])
            text = node.get_text(" ", strip=True)
            return f"\n\n{'#' * level} {text}\n\n" if text else ""

        if name == "p":
            text = "".join(cls.inline_text(child) for child in node.children).strip()
            return f"\n\n{text}\n\n" if text else ""

        if name in {"ul", "ol"}:
            lines = []
            for li in node.find_all("li", recursive=False):
                item = cls.node_to_markdown(li, list_depth + 1).strip()
                if item:
                    prefix = f"{'  ' * list_depth}- "
                    item = re.sub(r"\n+", "\n" + " " * len(prefix), item)
                    lines.append(prefix + item)
            return "\n".join(lines) + "\n" if lines else ""

        if name == "li":
            return " ".join(
                cls.node_to_markdown(child, list_depth).strip() for child in node.children
            ).strip()

        if name == "table":
            return f"\n\n{cls.table_to_markdown(node)}\n\n"

        if name in {"strong", "b"}:
            text = node.get_text(" ", strip=True)
            return f"**{text}**" if text else ""

        if name in {"em", "i"}:
            text = node.get_text(" ", strip=True)
            return f"*{text}*" if text else ""

        if name == "blockquote":
            text = node.get_text("\n", strip=True)
            if not text:
                return ""
            return "\n\n" + "\n".join(f"> {line}" for line in text.splitlines()) + "\n\n"

        if name == "br":
            return "\n"

        if name == "dl":
            lines: list[str] = []
            pending_label: str | None = None
            for child in node.find_all(["dt", "dd"], recursive=False):
                text = re.sub(r"\s+", " ", child.get_text(" ", strip=True)).strip()
                if not text:
                    continue
                if child.name == "dt":
                    if pending_label:
                        lines.append(f"- **{pending_label}**")
                    pending_label = text
                else:
                    if pending_label:
                        lines.append(f"- **{pending_label}:** {text}")
                        pending_label = None
                    else:
                        lines.append(f"- {text}")
            if pending_label:
                lines.append(f"- **{pending_label}**")
            return ("\n\n" + "\n".join(lines) + "\n\n") if lines else ""

        parts = [cls.node_to_markdown(child, list_depth) for child in node.children]
        joined = " ".join(part for part in parts if part)
        joined = re.sub(r" +\n", "\n", joined)
        joined = re.sub(r"\n +", "\n", joined)
        if name in {"div", "section", "article", "main", "span", "tbody", "thead", "tr", "td", "th"}:
            return joined
        return joined

    @classmethod
    def tag_to_markdown(cls, tag: Tag) -> str:
        clone = BeautifulSoup(str(tag), "html.parser")
        root = clone.find(True) or clone
        for remove_tag in REMOVE_TAGS:
            for node in root.find_all(remove_tag):
                node.decompose()
        cls.strip_attributes(root)
        markdown = cls.node_to_markdown(root)
        return Utils.normalise_text(markdown)

    @staticmethod
    def extract_main_content(soup: BeautifulSoup) -> Tag:
        for selector in MAIN_SELECTORS:
            node = soup.select_one(selector)
            if node and len(node.get_text(strip=True)) > 200:
                return node

        body = soup.body or soup
        best: Tag | None = None
        best_len = 0
        for div in body.find_all(["main", "article", "section", "div"]):
            text_len = len(div.get_text(strip=True))
            if text_len > best_len:
                best = div
                best_len = text_len
        return best or body

    @staticmethod
    def page_title_from_soup(soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1")
        if h1:
            return h1.get_text(" ", strip=True)
        title = soup.select_one("title")
        if title:
            return title.get_text(" ", strip=True)
        return ""
