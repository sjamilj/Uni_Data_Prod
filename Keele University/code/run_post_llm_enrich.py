#!/usr/bin/env python3
"""Keele post-LLM entry enrichers.

Called manually after LLM extract finishes:
  python run_post_llm_enrich.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_CODE_DIR = Path(__file__).resolve().parent
if str(_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(_CODE_DIR))

from derive_entry_requirements import apply_enrichments  # noqa: E402


def main() -> int:
    code_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else _CODE_DIR
    print("==> Post-LLM enrich: Keele entry requirements")
    count = apply_enrichments(code_dir, re_normalize=True, dry_run=False)
    print(f"Post-LLM enrich complete: patched={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
