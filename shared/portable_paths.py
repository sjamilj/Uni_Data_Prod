"""Resolve university HTML paths so .env files work on any machine.

Catalogue paths in .env should be repo-relative, e.g.:

    COURSE_CATALOGUE_HTML=../course_listing/all_course.html

Absolute paths from another PC are still accepted: if the file is missing,
the resolver keeps the ``course_listing/`` (or ``course_detail/``) suffix and
looks under this clone's university folder.
"""

from __future__ import annotations

from pathlib import Path


class PortableHtmlPathResolver:
    """Resolve portable HTML paths for university catalogue/detail pages."""

    MARKERS = ("course_listing", "course_detail", "uni_req")

    @staticmethod
    def _is_absolute_path(text: str) -> bool:
        raw = text.strip().strip('"').strip("'")
        if not raw:
            return False
        posix = raw.replace("\\", "/")
        if posix.startswith("/"):
            return True
        return len(raw) >= 3 and raw[1] == ":" and raw[2] in "\\/"

    @classmethod
    def relativize_html_value(cls, value: str, *, kind: str = "course_listing") -> str:
        """Turn an absolute or mixed path into ../course_listing/filename."""
        raw = (value or "").strip().strip('"').strip("'")
        if not raw:
            return value
        posix = raw.replace("\\", "/")
        parts = [part for part in posix.split("/") if part not in ("", ".")]
        for marker in cls.MARKERS:
            if marker in parts:
                idx = parts.index(marker)
                return "../" + "/".join(parts[idx:])
        if posix.startswith("../") or posix.startswith("./"):
            return posix
        if cls._is_absolute_path(raw):
            return f"../{kind}/{Path(raw).name}"
        if "/" not in posix:
            return f"../{kind}/{posix}"
        return posix

    @classmethod
    def resolve_university_html(
        cls,
        work_dir: Path,
        raw: str,
        *,
        kind: str = "course_listing",
        label: str = "COURSE_CATALOGUE_HTML",
    ) -> Path:
        text = (raw or "").strip().strip('"').strip("'")
        if not text:
            raise FileNotFoundError(f"{label} is empty")

        work_dir = work_dir.resolve()
        uni_root = work_dir.parent if work_dir.name.lower() == "code" else work_dir
        posix = text.replace("\\", "/")
        candidate = Path(text)
        tried: list[Path] = []

        def add(path: Path) -> None:
            tried.append(path)

        if cls._is_absolute_path(text):
            add(candidate)
            parts = candidate.parts
            for marker in cls.MARKERS:
                if marker in parts:
                    idx = parts.index(marker)
                    add(uni_root.joinpath(*parts[idx:]))
                    break
            else:
                add(uni_root / kind / candidate.name)
                add(uni_root / candidate.name)
        else:
            add(work_dir / posix)
            add(uni_root / posix)
            add(uni_root / kind / Path(posix).name)
            if posix.startswith("../"):
                add(work_dir / posix)

        seen: list[Path] = []
        for path in tried:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.append(resolved)
            if resolved.is_file():
                return resolved

        tried_txt = "\n".join(f"  {path}" for path in seen) or f"  {text}"
        raise FileNotFoundError(f"{label} not found: {text}\nTried:\n{tried_txt}")


MARKERS = PortableHtmlPathResolver.MARKERS
relativize_html_value = PortableHtmlPathResolver.relativize_html_value
resolve_university_html = PortableHtmlPathResolver.resolve_university_html
