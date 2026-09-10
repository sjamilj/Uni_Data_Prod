#!/usr/bin/env python3
"""Brunel post-LLM entry enrichers (pathway + PG UK-class rules).

Called automatically by shared/post_llm_enrich.py after LLM extract finishes.
"""

from __future__ import annotations

import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from derive_pathway_entry_from_bangladesh_md import apply_enrichments as apply_pathway
from derive_ug_entry_from_bangladesh_md import apply_enrichments as apply_ug
from derive_pg_entry_from_uk_class import apply_enrichments as apply_pg


def main() -> int:
    code_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else _CODE_DIR
    print("==> Post-LLM enrich: Brunel pathway (bangladesh-entry.md)")
    pathway_count = apply_pathway(code_dir, re_normalize=False, dry_run=False)
    print("==> Post-LLM enrich: Brunel UG (A-level -> HSC GPA)")
    ug_count = apply_ug(code_dir, re_normalize=False, dry_run=False)
    print("==> Post-LLM enrich: Brunel UG/PG/PGR (UK class -> BSc GPA)")
    pg_count = apply_pg(code_dir, re_normalize=False, dry_run=False)
    print(f"Post-LLM enrich complete: pathway={pathway_count}, ug={ug_count}, pg={pg_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
