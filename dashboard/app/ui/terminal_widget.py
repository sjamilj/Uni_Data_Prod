"""Simple live log panel."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit


class TerminalWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Consolas", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        self.setFont(font)
        self.setReadOnly(True)
        self.setStyleSheet(
            "QTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3e3e3e; }"
        )

    def append_stdout(self, line: str) -> None:
        self._append(line, QColor(212, 212, 212))

    def append_stderr(self, line: str) -> None:
        self._append(line, QColor(255, 100, 100))

    def append_info(self, line: str) -> None:
        self._append(line, QColor(120, 180, 255))

    def _append(self, line: str, color: QColor) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        cursor.insertText(f"[{stamp}] {line}\n", fmt)
        self.setTextCursor(cursor)
