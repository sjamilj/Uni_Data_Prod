"""Main dashboard window: university status table and phase run buttons."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.status_loader import load_status
from app.core.task_runner import TaskRunner
from app.ui.terminal_widget import TerminalWidget

COLUMNS = [
    ("University", "name"),
    ("Setup", "setup"),
    ("URLs", "urls"),
    ("UniClean", "uni_clean"),
    ("Presetup", "presetup"),
    ("Download", "download"),
    ("LLM", "llm"),
    ("Norm", "normalize"),
    ("CSV", "csv"),
]

STATUS_COLORS = {
    "done": QColor(185, 230, 196),
    "in_progress": QColor(255, 230, 120),
    "partial": QColor(255, 230, 120),
    "not_started": QColor(220, 220, 220),
    "missing": QColor(220, 220, 220),
    "error": QColor(255, 190, 190),
}
STATUS_TEXT = QColor(20, 20, 20)
ERROR_TEXT = QColor(90, 0, 0)
NAME_BG = QColor(245, 245, 245)

PHASES = {
    "scrape_urls": "shared/scrape_course_urls.py",
    "uni_clean": "shared/download_and_clean_course_pages.py",
    "presetup": "shared/run_course_pipeline.py",
    "presetup_llm": "shared/run_course_pipeline.py",
    "execute": "shared/run_course_pipeline.py",
}

LEVEL_CHECKBOXES = (
    ("foundation", "Foundation"),
    ("undergraduate", "Undergraduate"),
    ("postgraduate", "Postgraduate"),
    ("postgraduate_research", "PGR"),
)

LLM_PHASES = frozenset({"presetup_llm", "execute"})


def _ollama_ok(host: str) -> bool:
    try:
        urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=2)
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class MainWindow(QMainWindow):
    def __init__(self, repo_root: Path, config: dict):
        super().__init__()
        self.repo_root = Path(repo_root)
        self.config = config
        self.rows: list[dict] = []
        self.runner: TaskRunner | None = None
        self._running_university = ""
        self._running_task_id = ""
        self._last_progress_key = ""
        self._set_window()
        self._build_ui()
        self.refresh_status()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh_status)

    def _set_window(self) -> None:
        self.setWindowTitle("University Data Pipeline Dashboard")
        self.resize(1320, 820)

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)

        top = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_status)
        self.filter_box = QComboBox()
        self.filter_box.addItems(["All", "URLs not started", "URLs done", "Incomplete"])
        self.filter_box.currentTextChanged.connect(self._fill_table)
        self.summary_label = QLabel("")
        self.job_progress_label = QLabel("")
        self.job_progress_label.setStyleSheet("color: #1a5fb4; font-weight: bold;")
        top.addWidget(self.refresh_btn)
        top.addWidget(QLabel("Filter:"))
        top.addWidget(self.filter_box)
        top.addWidget(self.summary_label, 1)
        top.addWidget(self.job_progress_label)
        layout.addLayout(top)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([col[0] for col in COLUMNS])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: #f4f4f4;
                color: #141414;
                gridline-color: #bdbdbd;
                selection-background-color: #2f6fed;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d30;
                color: #ffffff;
                padding: 6px;
                border: 1px solid #1e1e1e;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                color: #ffffff;
            }
            """
        )
        layout.addWidget(self.table, 2)

        self.selected_label = QLabel("Selected: (none)")
        layout.addWidget(self.selected_label)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Run mode:"))
        self.mode_box = QComboBox()
        self.mode_box.addItem("Resume — keep progress, skip finished work", "resume")
        self.mode_box.addItem("Fresh — start this step over", "fresh")
        self.mode_box.addItem("Append URLs — merge new course URLs into the list", "append")
        self.mode_box.setCurrentIndex(0)
        self.mode_box.setMinimumWidth(380)
        mode_row.addWidget(self.mode_box)
        self.mode_hint = QLabel(
            "Resume continues. Fresh resamples Presetup or re-extracts Execute. Append is for scrape only."
        )
        self.mode_hint.setWordWrap(True)
        mode_row.addWidget(self.mode_hint, 1)
        layout.addLayout(mode_row)

        buttons = QHBoxLayout()
        self.btn_scrape = QPushButton("1 Scrape URLs")
        self.btn_uni = QPushButton("2 Clean Uni Pages")
        self.btn_presetup = QPushButton("3 Presetup (10 mixed)")
        self.btn_presetup_llm = QPushButton("4 Presetup LLM")
        self.btn_execute = QPushButton("5 Execute")
        self.btn_remaining = QPushButton("Run remaining")
        self.btn_folder = QPushButton("Open folder")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_scrape.clicked.connect(lambda: self._run_phase("scrape_urls"))
        self.btn_uni.clicked.connect(lambda: self._run_phase("uni_clean"))
        self.btn_presetup.clicked.connect(lambda: self._run_phase("presetup"))
        self.btn_presetup_llm.clicked.connect(lambda: self._run_phase("presetup_llm"))
        self.btn_execute.clicked.connect(lambda: self._run_phase("execute"))
        self.btn_remaining.clicked.connect(self._run_remaining)
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_cancel.setEnabled(False)
        for button in (
            self.btn_scrape,
            self.btn_uni,
            self.btn_presetup,
            self.btn_presetup_llm,
            self.btn_execute,
            self.btn_remaining,
            self.btn_folder,
            self.btn_cancel,
        ):
            buttons.addWidget(button)
        layout.addLayout(buttons)

        execute_box = QGroupBox("Study levels (Scrape URLs and Execute) and how many courses")
        execute_layout = QVBoxLayout(execute_box)
        level_row = QHBoxLayout()
        self.level_checks: dict[str, QCheckBox] = {}
        for key, label in LEVEL_CHECKBOXES:
            box = QCheckBox(label)
            self.level_checks[key] = box
            level_row.addWidget(box)
        level_row.addStretch(1)
        execute_layout.addLayout(level_row)

        count_row = QHBoxLayout()
        self.radio_full = QRadioButton("Full catalogue")
        self.radio_number = QRadioButton("Number")
        self.radio_full.setChecked(True)
        self.count_group = QButtonGroup(self)
        self.count_group.addButton(self.radio_full)
        self.count_group.addButton(self.radio_number)
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 9999)
        self.limit_spin.setValue(10)
        self.limit_spin.setEnabled(False)
        self.radio_number.toggled.connect(self.limit_spin.setEnabled)
        count_row.addWidget(self.radio_full)
        count_row.addWidget(self.radio_number)
        count_row.addWidget(self.limit_spin)
        count_row.addStretch(1)
        execute_layout.addLayout(count_row)
        layout.addWidget(execute_box)

        self.note_label = QLabel(
            "Tick study levels before Scrape URLs to scrape only those listings; leave them unticked to scrape all. "
            "After Presetup, review HTML and markdown, then edit .env / cleanup code before Presetup LLM. "
            "Execute downloads, cleans, and sends each course to the LLM one at a time. "
            "Cloudflare unis (South Wales, UWTSD, West London) may need a headed scrape."
        )
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)

        self.terminal = TerminalWidget()
        layout.addWidget(QLabel("Terminal log"))
        layout.addWidget(self.terminal, 1)

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def _action_buttons(self) -> tuple[QPushButton, ...]:
        return (
            self.btn_scrape,
            self.btn_uni,
            self.btn_presetup,
            self.btn_presetup_llm,
            self.btn_execute,
            self.btn_remaining,
        )

    def refresh_status(self) -> None:
        self.rows, summary = load_status(self.repo_root)
        self.summary_label.setText(
            f"{summary['universities']} unis | "
            f"{summary['urls_done']} URL done | "
            f"{summary['download_done']} download done | "
            f"{summary['csv_done']} CSV done"
        )
        selected = self._selected_name()
        self._fill_table()
        if selected:
            for row in range(self.table.rowCount()):
                if self.table.item(row, 0) and self.table.item(row, 0).text() == selected:
                    self.table.selectRow(row)
                    break
        self._on_selection()
        self._update_job_progress()

    def _update_job_progress(self) -> None:
        if not self.runner or not self.runner.isRunning() or not self._running_university:
            self.job_progress_label.setText("")
            return

        output_dir = self.repo_root / self._running_university / "output"
        msg = f"Running {self._running_task_id}…"

        if self._running_task_id in {"presetup_llm", "execute"}:
            if self._running_task_id == "presetup_llm":
                progress_file = (
                    output_dir / "extracted" / "pre_setup_course_extracted" / "extraction_progress.json"
                )
            else:
                progress_file = output_dir / "extracted" / "extraction_progress.json"
            total = 0
            if self._running_task_id == "presetup_llm":
                sample = _read_json(output_dir / "presetup_sample.json")
                total = len(sample.get("courses") or [])
            else:
                selection = _read_json(output_dir / "execute_selection.json")
                total = len(selection.get("courses") or [])
            done = 0
            failed = 0
            if progress_file.is_file():
                try:
                    data = json.loads(progress_file.read_text(encoding="utf-8"))
                    done = len(data.get("completed") or [])
                    failed = len(data.get("failed") or [])
                except (OSError, json.JSONDecodeError):
                    pass
            if total:
                msg = f"LLM extract: {done}/{total} done"
                if failed:
                    msg += f", {failed} failed"
            progress_key = f"{done}/{total}/{failed}"
            if progress_key != self._last_progress_key:
                self._last_progress_key = progress_key
                self.terminal.append_info(msg)
        elif self._running_task_id == "presetup":
            sample = _read_json(output_dir / "presetup_sample.json")
            total = len(sample.get("courses") or [])
            progress_file = output_dir / "scrape_progress.json"
            downloaded = 0
            if progress_file.is_file():
                try:
                    data = json.loads(progress_file.read_text(encoding="utf-8"))
                    downloaded = len(data.get("downloaded_urls") or [])
                except (OSError, json.JSONDecodeError, TypeError, ValueError):
                    pass
            if total:
                msg = f"Presetup download: {min(downloaded, total)}/{total}"

        self.job_progress_label.setText(msg)
        self.statusBar().showMessage(msg)

    def _fill_table(self) -> None:
        mode = self.filter_box.currentText()
        visible = []
        for row in self.rows:
            if mode == "URLs not started" and row["urls"] != "not_started":
                continue
            if mode == "URLs done" and row["urls"] != "done":
                continue
            if mode == "Incomplete" and row["csv"] == "done":
                continue
            visible.append(row)

        self.table.setRowCount(len(visible))
        for i, row in enumerate(visible):
            presetup_text = row.get("presetup") or "not_started"
            if row.get("presetup_total"):
                presetup_text = f"{row.get('presetup_clean') or 0}/{row['presetup_total']}"
            values = [
                row["name"],
                row["setup"],
                str(row["url_count"]) if row["url_count"] else row["urls"],
                row["uni_clean"],
                presetup_text,
                f"{row['course_md']}/{row['url_count'] or '-'}",
                f"{row['llm_completed']}/{row['llm_total'] or '-'}",
                row["normalize"],
                row["csv"],
            ]
            statuses = [
                "name",
                row["setup"],
                row["urls"],
                row["uni_clean"],
                row.get("presetup") or "not_started",
                row["download"],
                row["llm"],
                row["normalize"],
                row["csv"],
            ]
            if row.get("scrape_error") and row["urls"] != "done":
                statuses[2] = "error"
            for col, (text, status) in enumerate(zip(values, statuses)):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, row["name"])
                    if row.get("cloudflare"):
                        item.setToolTip("Cloudflare: scrape may need a visible browser")
                    item.setBackground(QBrush(NAME_BG))
                    item.setForeground(QBrush(STATUS_TEXT))
                else:
                    bg = STATUS_COLORS.get(status, QColor(255, 255, 255))
                    fg = ERROR_TEXT if status == "error" else STATUS_TEXT
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))
                self.table.setItem(i, col, item)
        self.table.resizeColumnsToContents()

    def _selected_name(self) -> str:
        items = self.table.selectedItems()
        if not items:
            return ""
        return self.table.item(items[0].row(), 0).data(Qt.ItemDataRole.UserRole) or ""

    def _selected_row(self) -> dict | None:
        name = self._selected_name()
        for row in self.rows:
            if row["name"] == name:
                return row
        return None

    def _sync_level_checks(self, row: dict | None) -> None:
        counts = (row or {}).get("level_counts") or {}
        for key, box in self.level_checks.items():
            n = int(counts.get(key) or 0)
            box.setEnabled(bool(row) and n > 0)
            box.setText(f"{dict(LEVEL_CHECKBOXES)[key]} ({n})" if row else dict(LEVEL_CHECKBOXES)[key])
            if n == 0:
                box.setChecked(False)

    def _on_selection(self) -> None:
        row = self._selected_row()
        running = self.runner is not None and self.runner.isRunning()
        self._sync_level_checks(row)
        if not row:
            self.selected_label.setText("Selected: (none)")
            for button in self._action_buttons():
                button.setEnabled(False)
            self.btn_folder.setEnabled(False)
            return
        label = row["name"]
        if row.get("cloudflare"):
            label += "  [Cloudflare]"
        self.selected_label.setText(f"Selected: {label}")
        self.btn_folder.setEnabled(True)
        if running:
            return
        self.btn_scrape.setEnabled(True)
        self.btn_uni.setEnabled(row["can_uni_clean"])
        self.btn_presetup.setEnabled(row.get("can_presetup", False))
        self.btn_presetup_llm.setEnabled(row.get("can_presetup_llm", False))
        self.btn_execute.setEnabled(row.get("can_execute", False))
        self.btn_remaining.setEnabled(row["csv"] != "done")

    def _set_running(self, running: bool) -> None:
        for button in (
            *self._action_buttons(),
            self.refresh_btn,
            self.mode_box,
        ):
            button.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        if not running:
            self._on_selection()

    def _run_phase(self, phase_id: str) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "Select a university", "Click a university row first.")
            return
        if phase_id == "uni_clean" and not row["can_uni_clean"]:
            QMessageBox.warning(self, "Missing input", "Save uni_req HTML pages first.")
            return
        if phase_id == "presetup" and not row.get("can_presetup"):
            QMessageBox.warning(self, "Missing input", "Scrape URLs first (course_urls.csv).")
            return
        if phase_id == "presetup_llm" and not row.get("can_presetup_llm"):
            QMessageBox.warning(
                self,
                "Missing input",
                "Run Presetup first, then review HTML and markdown before Presetup LLM.",
            )
            return
        if phase_id == "execute" and not row.get("can_execute"):
            QMessageBox.warning(self, "Missing input", "Scrape URLs first.")
            return
        if phase_id in LLM_PHASES:
            host = str(self.config.get("ollama_host") or "http://localhost:11434")
            if not _ollama_ok(host):
                QMessageBox.critical(
                    self,
                    "Ollama not running",
                    f"Cannot reach {host}. Start Ollama, then try again.",
                )
                return
        extra = self._phase_args(phase_id)
        if extra is None:
            return
        self._start_command(phase_id, row["name"], extra)

    def _run_mode(self) -> str:
        return str(self.mode_box.currentData() or "resume")

    def _selected_levels(self) -> list[str]:
        return [key for key, box in self.level_checks.items() if box.isChecked() and box.isEnabled()]

    def _phase_args(self, phase_id: str) -> list[str] | None:
        mode = self._run_mode()
        if mode == "fresh" and phase_id in {"scrape_urls", "presetup", "presetup_llm", "execute"}:
            ok = QMessageBox.question(
                self,
                "Fresh run",
                "Fresh starts this step over and can overwrite saved progress.\nContinue?",
            )
            if ok != QMessageBox.StandardButton.Yes:
                return None
        if phase_id == "scrape_urls":
            extra: list[str] = []
            if mode == "fresh":
                extra.append("--fresh")
            elif mode == "append":
                extra.append("--append-urls")
            for level in self._selected_levels():
                extra.extend(["--study-level", level])
            return extra
        if phase_id == "uni_clean":
            return []
        if phase_id == "presetup":
            extra = ["--presetup"]
            if mode == "fresh":
                extra.append("--fresh")
            return extra
        if phase_id == "presetup_llm":
            extra = ["--presetup-llm"]
            if mode != "fresh":
                extra.append("--resume")
            return extra
        if phase_id == "execute":
            levels = self._selected_levels()
            if not levels:
                QMessageBox.warning(
                    self,
                    "Choose study levels",
                    "Tick at least one study level (Foundation, Undergraduate, Postgraduate, PGR).",
                )
                return None
            extra = ["--execute"]
            for level in levels:
                extra.extend(["--study-level", level])
            if self.radio_full.isChecked():
                extra.append("--all")
            else:
                extra.extend(["--limit", str(self.limit_spin.value())])
            if mode != "fresh":
                extra.append("--resume")
            return extra
        return []

    def _run_remaining(self) -> None:
        row = self._selected_row()
        if not row:
            return
        if row["urls"] != "done":
            self._run_phase("scrape_urls")
        elif row["uni_clean"] != "done":
            self._run_phase("uni_clean")
        elif row.get("presetup") != "done":
            self._run_phase("presetup")
        else:
            QMessageBox.information(
                self,
                "Presetup ready",
                "Review HTML and markdown, edit .env / cleanup if needed, then run Presetup LLM. "
                "After that, pick study levels and click Execute.",
            )

    def _phase_command(self, phase_id: str, university: str, extra: list[str]) -> list[str]:
        code_dir = str(self.repo_root / university / "code")
        script = PHASES[phase_id]
        python = sys.executable or "python"
        if phase_id == "uni_clean":
            extra = ["--clean-uni-only"]
        if phase_id in PHASES:
            return [python, "-u", str(self.repo_root / script), "--code-dir", code_dir, *extra]
        raise ValueError(f"Unknown phase: {phase_id}")

    def _start_command(self, task_id: str, university: str, extra: list[str]) -> None:
        if self.runner and self.runner.isRunning():
            return
        command = self._phase_command(task_id, university, extra)
        self.terminal.append_info(f"Starting {task_id} for {university}")
        self.terminal.append_info(" ".join(command))
        self._running_university = university
        self._running_task_id = task_id
        self._last_progress_key = ""
        self.runner = TaskRunner(task_id, command, self.repo_root)
        self.runner.stdout_ready.connect(self.terminal.append_stdout)
        self.runner.stderr_ready.connect(self.terminal.append_stderr)
        self.runner.finished.connect(self._on_finished)
        self.runner.failed.connect(self._on_failed)
        self.runner.start()
        self._set_running(True)
        self.statusBar().showMessage(f"Running {task_id}: {university}")
        self.refresh_timer.setInterval(2000)
        self.refresh_timer.start()

    def _on_finished(self, task_id: str, exit_code: int, duration: float) -> None:
        self.terminal.append_info(f"{task_id} finished in {duration:.0f}s (exit {exit_code})")
        self._job_done("Ready")

    def _on_failed(self, task_id: str, message: str, exit_code: int) -> None:
        self.terminal.append_stderr(f"{task_id} failed: {message} ({exit_code})")
        self._job_done(f"Failed: {message}")

    def _job_done(self, status: str) -> None:
        self.refresh_timer.stop()
        self.refresh_timer.setInterval(5000)
        self._running_university = ""
        self._running_task_id = ""
        self._last_progress_key = ""
        self.job_progress_label.setText("")
        self.runner = None
        self._set_running(False)
        self.refresh_status()
        self.statusBar().showMessage(status)

    def _cancel(self) -> None:
        if self.runner:
            self.runner.stop()
            self.terminal.append_info("Cancel requested")

    def _open_folder(self) -> None:
        row = self._selected_row()
        if not row:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(row["path"]))


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
