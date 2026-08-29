#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! python3 -c "import PySide6" 2>/dev/null; then
  echo "Installing dashboard dependencies..."
  python3 -m pip install -r requirements.txt
fi
exec python3 main.py
