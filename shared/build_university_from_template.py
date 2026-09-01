#!/usr/bin/env python3
"""Build university code/.env and variant CSV from Template.csv.

Reads _university_template/Template.csv (or a copy in the university folder),
detects catalogue strategy, and writes:
  - {University}/code/.env (and optionally ENV.MD)
  - {University}/{Variant}.csv at university root

Phase 1: env + variant CSV only — HTML remains manual browser-save.

Examples:
  python shared/build_university_from_template.py --university "New Uni - NU"
  python shared/build_university_from_template.py --template-csv "path/Template.csv"
  python shared/build_university_from_template.py --university "New Uni - NU" --bootstrap
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
_REPO_ROOT = _SHARED.parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from bootstrap_university import UniversityBootstrapper  # noqa: E402

STRATEGY_ALL_COURSE = "ALL_COURSE"
STRATEGY_PAGINATED = "DEGREE_SCOPED_PAGINATED"

VARIANT_FILES = frozenset(
    {
        "ALL_COURSE.csv",
        "Paginated.csv",
        "DegreeScopedALLCourse.csv",
        "DegreeScopedPaginated.csv",
    }
)

PROGRAMME_ROWS = ("All", "Foundation", "Undergraduate", "Postgraduate", "Postgraduate Research")

SCOPE_BY_PROGRAMME = {
    "Foundation": "FOUNDATION",
    "Undergraduate": "UNDERGRADUATE",
    "Postgraduate": "POSTGRADUATE",
    "Postgraduate Research": "POSTGRADUATE_RESEARCH",
}

CATALOGUE_HTML_BY_SCOPE = {
    "FOUNDATION": "../course_listing/foundation.html",
    "UNDERGRADUATE": "../course_listing/undergraduate.html",
    "POSTGRADUATE": "../course_listing/postgraduate.html",
    "POSTGRADUATE_RESEARCH": "../course_listing/postgraduate-research.html",
}

ALL_CATALOGUE_HTML = "../course_listing/all_course.html"

VARIANT_CSV_HEADER = [
    "uniName",
    "LISTING_PROGRAMME",
    "Course_listing_Link",
    "COURSE_LISTING_PAGE_1",
    "COURSE_LISTING_PAGE_2",
    "Course Detail page",
    "Bangladesh Req Link",
    "EnglishRequirementLink",
    "ScholarshipLink",
    "Comment",
]

TEMPLATE_COL_PROGRAMME = "Programme"
TEMPLATE_COL_ALL_LISTING = "ALL Course Listing URL"
TEMPLATE_COL_PAGE_1 = "Paginated Course Listing URL - Page 1"
TEMPLATE_COL_PAGE_2 = "Paginated Course Listing URL - Page 2"
TEMPLATE_COL_DETAIL = "Course Detail Page URL"
TEMPLATE_COL_BANGLADESH = "Bangladesh Entry Requirements URL"
TEMPLATE_COL_ENGLISH = "English Language Requirements URL"
TEMPLATE_COL_SCHOLARSHIP = "Scholarship Information URL"
TEMPLATE_COL_DEPOSIT = "Deposit Information URL"
TEMPLATE_COL_COMMENTS = "Comments"


@dataclass
class ProgrammeRow:
    programme: str
    all_listing_url: str = ""
    page_1_url: str = ""
    page_2_url: str = ""
    course_detail_url: str = ""
    bangladesh_url: str = ""
    english_url: str = ""
    scholarship_url: str = ""
    deposit_url: str = ""
    comments: str = ""

    def has_paginated_urls(self) -> bool:
        return bool(self.page_1_url.strip() or self.page_2_url.strip())

    def has_catalogue_url(self) -> bool:
        return bool(self.all_listing_url.strip())

    def has_any_listing(self) -> bool:
        return self.has_catalogue_url() or self.has_paginated_urls()


@dataclass
class UniversityTemplateConfig:
    explicit_variant: str = ""
    university_name: str = ""
    university_base_url: str = ""
    programmes: dict[str, ProgrammeRow] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def all_row(self) -> ProgrammeRow | None:
        return self.programmes.get("All")

    @property
    def degree_rows(self) -> list[ProgrammeRow]:
        return [
            self.programmes[name]
            for name in PROGRAMME_ROWS[1:]
            if name in self.programmes and self.programmes[name].has_any_listing()
        ]

    def uni_req_urls(self) -> dict[str, str]:
        for row in [self.all_row, *self.degree_rows]:
            if row is None:
                continue
            urls = {
                "bangladesh-entry": row.bangladesh_url.strip(),
                "english-requirements": row.english_url.strip(),
                "scholarships": row.scholarship_url.strip(),
                "deposit": row.deposit_url.strip(),
            }
            if any(urls.values()):
                return urls
        return {
            "bangladesh-entry": "",
            "english-requirements": "",
            "scholarships": "",
            "deposit": "",
        }


class TemplateCsvParser:
    """Parse Template.csv into UniversityTemplateConfig."""

    @staticmethod
    def _cell(row: dict[str, str], key: str) -> str:
        return (row.get(key) or "").strip()

    @classmethod
    def parse_file(cls, path: Path) -> UniversityTemplateConfig:
        text = path.read_text(encoding="utf-8-sig")
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 5:
            raise ValueError(f"{path}: expected at least 5 non-empty rows")

        meta_rows: list[list[str]] = []
        data_start = 0
        for index, line in enumerate(lines):
            if line.startswith("Programme,") or line.startswith('"Programme"'):
                data_start = index
                break
            meta_rows.append(list(csv.reader([line]))[0])
        else:
            raise ValueError(f"{path}: missing Programme header row")

        config = UniversityTemplateConfig()

        if meta_rows:
            for cell in meta_rows[0][1:]:
                token = cell.strip()
                if token in VARIANT_FILES:
                    config.explicit_variant = token
                    break

        for row_cells in meta_rows[1:]:
            if not row_cells:
                continue
            label = row_cells[0].strip().lower()
            value = row_cells[1].strip() if len(row_cells) > 1 else ""
            if label == "uni name":
                config.university_name = value
            elif label == "uni link":
                config.university_base_url = value

        reader = csv.DictReader(lines[data_start:])
        for raw in reader:
            programme = cls._cell(raw, TEMPLATE_COL_PROGRAMME)
            if not programme:
                continue
            config.programmes[programme] = ProgrammeRow(
                programme=programme,
                all_listing_url=cls._cell(raw, TEMPLATE_COL_ALL_LISTING),
                page_1_url=cls._cell(raw, TEMPLATE_COL_PAGE_1),
                page_2_url=cls._cell(raw, TEMPLATE_COL_PAGE_2),
                course_detail_url=cls._cell(raw, TEMPLATE_COL_DETAIL),
                bangladesh_url=cls._cell(raw, TEMPLATE_COL_BANGLADESH),
                english_url=cls._cell(raw, TEMPLATE_COL_ENGLISH),
                scholarship_url=cls._cell(raw, TEMPLATE_COL_SCHOLARSHIP),
                deposit_url=cls._cell(raw, TEMPLATE_COL_DEPOSIT),
                comments=cls._cell(raw, TEMPLATE_COL_COMMENTS),
            )

        if not config.university_name:
            raise ValueError(f"{path}: Uni Name (row 2) is required")
        if not config.university_base_url:
            raise ValueError(f"{path}: Uni Link (row 3) is required")

        return config


class StrategyResolver:
    """Resolve explicit + auto-detected variant CSV name."""

    @staticmethod
    def auto_detect(config: UniversityTemplateConfig) -> str:
        degree_rows = config.degree_rows
        all_row = config.all_row

        if degree_rows:
            uses_paginated = any(row.has_paginated_urls() for row in degree_rows)
            uses_catalogue = any(row.has_catalogue_url() for row in degree_rows)
            if uses_paginated and uses_catalogue:
                raise ValueError(
                    "Degree-scoped rows mix ALL Course Listing URL with Paginated URLs"
                )
            if uses_paginated:
                return "DegreeScopedPaginated.csv"
            if uses_catalogue:
                return "DegreeScopedALLCourse.csv"
            raise ValueError("Degree-scoped rows have no listing URLs filled")

        if all_row is None or not all_row.has_any_listing():
            raise ValueError("Fill row 'All' or programme rows (Foundation, Undergraduate, …)")

        if all_row.has_paginated_urls() and all_row.has_catalogue_url():
            raise ValueError("Row 'All' mixes ALL Course Listing URL with Paginated URLs")

        if all_row.has_paginated_urls():
            return "Paginated.csv"
        return "ALL_COURSE.csv"

    @classmethod
    def resolve(cls, config: UniversityTemplateConfig) -> str:
        auto = cls.auto_detect(config)
        explicit = config.explicit_variant
        if explicit and explicit != auto:
            config.warnings.append(
                f"Strategy cell says {explicit} but data suggests {auto}; using {explicit}"
            )
            return explicit
        if explicit:
            return explicit
        return auto

    @staticmethod
    def strategy_for_variant(variant: str) -> str:
        if variant in {"ALL_COURSE.csv", "DegreeScopedALLCourse.csv"}:
            return STRATEGY_ALL_COURSE
        if variant in {"Paginated.csv", "DegreeScopedPaginated.csv"}:
            return STRATEGY_PAGINATED
        raise ValueError(f"Unknown variant: {variant}")

    @staticmethod
    def is_degree_scoped(variant: str) -> bool:
        return variant in {"DegreeScopedALLCourse.csv", "DegreeScopedPaginated.csv"}


class EnvFilePatcher:
    """Apply Template.csv values to ENV.MD / .env text."""

    LISTING_KEY_RE = re.compile(
        r"^(?:[A-Z_]+_)?COURSE_(?:LISTING_PAGE_\d+|CATALOGUE_(?:URL|HTML))="
    )

    @classmethod
    def patch(cls, skeleton: str, config: UniversityTemplateConfig, variant: str) -> str:
        strategy = StrategyResolver.strategy_for_variant(variant)
        updates: dict[str, str] = {
            "UNIVERSITY_NAME": config.university_name,
            "UNIVERSITY_BASE_URL": config.university_base_url,
            "STRATEGY": strategy,
        }
        updates.update(cls._listing_updates(config, variant))

        lines = skeleton.splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped.startswith("UNI_REQ_SOURCE_URLS="):
                out.append('UNI_REQ_SOURCE_URLS="')
                for req_line in cls._format_uni_req(config.uni_req_urls()).splitlines():
                    out.append(req_line)
                out.append('"')
                i += 1
                while i < len(lines):
                    if lines[i].strip() == '"' and i > 0:
                        i += 1
                        break
                    i += 1
                continue

            match = re.match(r"^([A-Z0-9_]+)=(.*)$", stripped)
            if match:
                key = match.group(1)
                if cls.LISTING_KEY_RE.match(stripped):
                    i += 1
                    continue
                if key in updates:
                    out.append(f"{key}={updates[key]}")
                    i += 1
                    continue

            if stripped.startswith("# STRATEGY=ALL_COURSE") and strategy == STRATEGY_ALL_COURSE:
                out.append("STRATEGY=ALL_COURSE")
                i += 1
                continue

            out.append(line)
            i += 1

        existing_keys = {
            m.group(1)
            for line in out
            if (m := re.match(r"^([A-Z0-9_]+)=", line.strip()))
        }

        listing_lines = [
            f"{key}={value}"
            for key, value in updates.items()
            if key not in existing_keys
            and ("COURSE_LISTING" in key or "COURSE_CATALOGUE" in key)
        ]

        if listing_lines:
            insert_at = len(out)
            for idx, line in enumerate(out):
                if line.strip().startswith("UNIVERSITY_BASE_URL="):
                    insert_at = idx + 1
                    break
            out[insert_at:insert_at] = ["", "# --- Generated from Template.csv ---", *listing_lines, ""]

        return "\n".join(out).rstrip() + "\n"

    @classmethod
    def _listing_updates(cls, config: UniversityTemplateConfig, variant: str) -> dict[str, str]:
        updates: dict[str, str] = {}
        degree_scoped = StrategyResolver.is_degree_scoped(variant)
        is_paginated = strategy_is_paginated(variant)

        if degree_scoped:
            rows = config.degree_rows
            if not rows:
                raise ValueError(f"{variant} requires programme rows with URLs")
            for row in rows:
                scope = SCOPE_BY_PROGRAMME.get(row.programme)
                if not scope:
                    continue
                if is_paginated:
                    if row.page_1_url:
                        updates[f"{scope}_COURSE_LISTING_PAGE_1"] = row.page_1_url
                    if row.page_2_url:
                        updates[f"{scope}_COURSE_LISTING_PAGE_2"] = row.page_2_url
                else:
                    if row.all_listing_url:
                        updates[f"{scope}_COURSE_CATALOGUE_URL"] = row.all_listing_url
                    updates[f"{scope}_COURSE_CATALOGUE_HTML"] = CATALOGUE_HTML_BY_SCOPE[scope]
        else:
            all_row = config.all_row
            if all_row is None:
                raise ValueError(f"{variant} requires row 'All' with URLs")
            if is_paginated:
                if all_row.page_1_url:
                    updates["COURSE_LISTING_PAGE_1"] = all_row.page_1_url
                if all_row.page_2_url:
                    updates["COURSE_LISTING_PAGE_2"] = all_row.page_2_url
            else:
                if all_row.all_listing_url:
                    updates["COURSE_CATALOGUE_URL"] = all_row.all_listing_url
                updates["COURSE_CATALOGUE_HTML"] = ALL_CATALOGUE_HTML

        return updates

    @staticmethod
    def _format_uni_req(urls: dict[str, str]) -> str:
        lines = [f"{stem} :: {url}" for stem, url in urls.items() if url]
        if not lines:
            lines = [f"{stem} ::" for stem in urls]
        return "\n".join(lines)


def strategy_is_paginated(variant: str) -> bool:
    return variant in {"Paginated.csv", "DegreeScopedPaginated.csv"}


class VariantCsvWriter:
    """Write legacy variant CSV at university root."""

    @staticmethod
    def _listing_programme_label(programme: str) -> str:
        if programme == "Postgraduate Research":
            return "Postgraduate Research"
        if programme == "All":
            return ""
        return programme

    @classmethod
    def write(cls, path: Path, config: UniversityTemplateConfig, variant: str) -> None:
        degree_scoped = StrategyResolver.is_degree_scoped(variant)
        rows_to_export: list[ProgrammeRow] = []

        if degree_scoped:
            rows_to_export = config.degree_rows
        else:
            if config.all_row:
                rows_to_export = [config.all_row]

        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(VARIANT_CSV_HEADER)
            writer.writerow(["", "", "", "", "", "", "r.html", "e.html", "s.html", "pdf/ not found"])

            uni_req = config.uni_req_urls()
            for row in rows_to_export:
                writer.writerow(
                    [
                        config.university_name,
                        cls._listing_programme_label(row.programme),
                        row.all_listing_url,
                        row.page_1_url,
                        row.page_2_url,
                        row.course_detail_url,
                        row.bangladesh_url or uni_req.get("bangladesh-entry", ""),
                        row.english_url or uni_req.get("english-requirements", ""),
                        row.scholarship_url or uni_req.get("scholarships", ""),
                        row.comments,
                    ]
                )


class UniversityFromTemplateBuilder:
    """Orchestrate Template.csv → .env + variant CSV."""

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or _REPO_ROOT

    def resolve_paths(
        self,
        *,
        university: str | None,
        template_csv: Path | None,
    ) -> tuple[Path, Path]:
        if template_csv:
            csv_path = template_csv.resolve()
            uni_dir = csv_path.parent
        elif university:
            uni_dir = self.repo_root / university
            csv_path = uni_dir / "Template.csv"
        else:
            raise ValueError("Provide --university or --template-csv")

        if not csv_path.is_file():
            raise FileNotFoundError(f"Template.csv not found: {csv_path}")

        return uni_dir, csv_path

    def build(
        self,
        *,
        university: str | None = None,
        template_csv: Path | None = None,
        bootstrap: bool = False,
        write_env_md: bool = True,
        force: bool = False,
    ) -> dict[str, Path]:
        uni_dir, csv_path = self.resolve_paths(university=university, template_csv=template_csv)

        config = TemplateCsvParser.parse_file(csv_path)

        if bootstrap and not uni_dir.is_dir():
            UniversityBootstrapper(self.repo_root).bootstrap(config.university_name, force=force)

        if not uni_dir.is_dir():
            raise FileNotFoundError(
                f"University folder not found: {uni_dir}. Run with --bootstrap or copy _university_template."
            )

        variant = StrategyResolver.resolve(config)
        code_dir = uni_dir / "code"
        env_md_path = code_dir / "ENV.MD"
        dotenv_path = code_dir / ".env"

        if not env_md_path.is_file():
            template_env = self.repo_root / "_university_template" / "code" / "ENV.MD"
            if not template_env.is_file():
                raise FileNotFoundError(f"No ENV.MD in {code_dir} and no template at {template_env}")
            code_dir.mkdir(parents=True, exist_ok=True)
            env_md_path.write_text(template_env.read_text(encoding="utf-8"), encoding="utf-8")

        skeleton = env_md_path.read_text(encoding="utf-8")
        patched = EnvFilePatcher.patch(skeleton, config, variant)

        dotenv_path.write_text(patched, encoding="utf-8")
        if write_env_md:
            env_md_path.write_text(patched, encoding="utf-8")

        variant_path = uni_dir / variant
        VariantCsvWriter.write(variant_path, config, variant)

        for warning in config.warnings:
            print(f"Warning: {warning}", file=sys.stderr)

        print(f"Wrote {dotenv_path}")
        if write_env_md:
            print(f"Wrote {env_md_path}")
        print(f"Wrote {variant_path}")
        print(f"STRATEGY={StrategyResolver.strategy_for_variant(variant)} ({variant})")
        print()
        print("Next (manual):")
        print("  - Save uni_req/*.html from requirement URLs")
        print("  - Save course_listing/ HTML (all_course.html or per-programme files)")
        print("  - Save course_detail/ sample pages from Course Detail URLs")
        print("  - Tune COURSE_PATH_PATTERNS and COURSE_CLEAN_BLOCKS in .env")

        return {
            "university_dir": uni_dir,
            "dotenv": dotenv_path,
            "env_md": env_md_path,
            "variant_csv": variant_path,
        }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate code/.env and variant CSV from Template.csv"
    )
    parser.add_argument("--university", help="University folder name under repo root")
    parser.add_argument(
        "--template-csv",
        type=Path,
        help="Path to Template.csv (default: {University}/Template.csv)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Repo root (default: parent of shared/)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Create university folder from _university_template if missing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --bootstrap, replace existing university folder",
    )
    parser.add_argument(
        "--dotenv-only",
        action="store_true",
        help="Write .env only, not ENV.MD",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    builder = UniversityFromTemplateBuilder(args.repo_root)
    try:
        builder.build(
            university=args.university,
            template_csv=args.template_csv,
            bootstrap=args.bootstrap,
            write_env_md=not args.dotenv_only,
            force=args.force,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
