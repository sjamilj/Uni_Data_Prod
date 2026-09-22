#!/usr/bin/env python3
"""University of Suffolk post-LLM entry enrichers."""

from __future__ import annotations

import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

import suffolk_alevel_mapping  # noqa: F401 — UG/foundation A-Level → HSC
from derive_pg_entry_from_uk_class import apply_enrichments as apply_pg


def main() -> int:
    code_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else _CODE_DIR
    print("==> Post-LLM enrich: Suffolk PG (UK 2:1/2:2 -> BSc GPA)")
    pg_count = apply_pg(code_dir, re_normalize=False, dry_run=False)
    print(f"Post-LLM enrich complete: pg={pg_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
