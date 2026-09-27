"""Pin university + shared folders and sync code/.env from ENV.MD."""

from __future__ import annotations

import shutil
from pathlib import Path


def sync_env_from_env_md(code_dir: Path) -> tuple[bool, str]:
    """Copy ENV.MD → .env (tracked source of truth for listing config)."""
    env_md = code_dir / "ENV.MD"
    dot_env = code_dir / ".env"
    if not env_md.is_file():
        return False, f"Missing {env_md}"
    shutil.copy2(env_md, dot_env)
    return True, f"Wrote {dot_env.name} from ENV.MD"
