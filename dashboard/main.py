"""F1 pipeline dashboard — status table and one-click phase runners."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_DIR.parent
sys.path.insert(0, str(DASHBOARD_DIR))
sys.path.insert(0, str(REPO_ROOT / "shared"))

from app.ui.main_window import MainWindow  # noqa: E402


def load_config() -> dict:
    path = DASHBOARD_DIR / "pipeline_config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("University Data Pipeline Dashboard")
    app.setStyle("Fusion")
    window = MainWindow(repo_root=REPO_ROOT, config=load_config())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
