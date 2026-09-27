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

from app.core.e2e_one_course import e2e_one_course_commands
from app.core.e2e_pins import get_pin_for_folder
from app.core.uni_activate import sync_env_from_env_md
from app.core.uni_registry import (
    checkout_command,
    load_registry_by_folder,
    should_run_registry_checkout,
)
from app.core.git_restore import (
    back_to_main_command_chain,
    load_shared_baseline_tag,
    restore_shared_command,
    university_folders_for_restore,
)
from app.core.status_loader import load_status
from app.core.task_runner import TaskRunner
from app.ui.terminal_widget import TerminalWidget

COLUMNS = [
    ("University", "name"),
    ("Setup", "setup"),
    ("URLs", "urls"),
    ("UniClean", "uni_clean"),
    ("Presetup download_and_clean", "presetup"),
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
    "scrape_presetup": "shared/scrape_course_urls.py",
    "scrape_urls": "shared/scrape_course_urls.py",
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
        self._shared_baseline_tag = load_shared_baseline_tag(
            self.repo_root,
            self.config.get("shared_baseline_tag") or None,
        )
        self._running_university = ""
        self._running_task_id = ""
        self._last_progress_key = ""
        self._git_follow_up: list[list[str]] = []
        self._command_chain: list[list[str]] = []
        self.registry_by_folder = load_registry_by_folder(self.repo_root)
        self._activate_on_select = _config_flag(self.config.get("activate_on_select"), default=True)
        self._last_activated_name = ""
        self._skip_registry_checkout_for = ""
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
        self.refresh_btn.setToolTip("Reload university status from files on disk (course_urls.csv, output/, etc.)")
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
        self.selected_label.setWordWrap(True)
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
            "Resume continues. Fresh rebuilds Presetup from scrape URLs or re-extracts Execute. Append is for scrape only."
        )
        self.mode_hint.setWordWrap(True)
        mode_row.addWidget(self.mode_hint, 1)
        layout.addLayout(mode_row)

        presetup_row = QHBoxLayout()
        general_row = QHBoxLayout()
        git_row = QHBoxLayout()
        self.btn_scrape_presetup = QPushButton("(2) Presetup Scrape")
        self.btn_scrape_presetup.setToolTip("course listings → presetup_urls.csv (5 URLs per study level)")
        self.btn_scrape = QPushButton("(1) Scrape URLs")
        self.btn_scrape.setToolTip(
            "course listings → course_urls.csv (+ per-level CSVs). "
            "Tick study levels below to scrape only those listings."
        )
        self.btn_presetup = QPushButton("(3) Presetup download_and_clean")
        self.btn_presetup.setToolTip(
            "presetup_urls.csv → download → clean (review HTML/markdown before Presetup LLM)"
        )
        self.btn_presetup_llm = QPushButton("(4) Presetup LLM")
        self.btn_presetup_llm.setToolTip("presetup sample → LLM → normalize → export (trial run on ~5 courses per level)")
        self.btn_execute = QPushButton("(6) Execute")
        self.btn_execute.setToolTip("download → clean → LLM → normalize → export")
        self.btn_e2e_one = QPushButton("(5) Run Full Pipeline with One Course")
        self.btn_e2e_one.setToolTip(
            "course_urls.csv → e2e_course_pins.json → download → clean → LLM → normalize → export (one course)"
        )
        self.btn_pick_shared = QPushButton(f"Pick Shared ({self._shared_baseline_tag})")
        self.btn_pick_shared.setToolTip(
            f"git restore shared/ from {self._shared_baseline_tag} (registry baseline; overwrites local shared changes)"
        )
        self.btn_back_main = QPushButton("Restore HEAD")
        self.btn_back_main.setToolTip(
            "git restore + clean: reset shared/ and university folders to branch HEAD; "
            "discard uncommitted and untracked changes there (undo checkout-uni pins)"
        )
        self.btn_folder = QPushButton("Open folder")
        self.btn_folder.setToolTip("Open the selected university folder in File Explorer")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setToolTip("Stop the running command")
        self.btn_scrape_presetup.clicked.connect(lambda: self._run_phase("scrape_presetup"))
        self.btn_scrape.clicked.connect(lambda: self._run_phase("scrape_urls"))
        self.btn_presetup.clicked.connect(lambda: self._run_phase("presetup"))
        self.btn_presetup_llm.clicked.connect(lambda: self._run_phase("presetup_llm"))
        self.btn_execute.clicked.connect(lambda: self._run_phase("execute"))
        self.btn_e2e_one.clicked.connect(self._run_e2e_one)
        self.btn_pick_shared.clicked.connect(self._pick_shared)
        self.btn_back_main.clicked.connect(self._back_to_main)
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_cancel.setEnabled(False)
        for button in (
            self.btn_scrape,
            self.btn_execute,
            self.btn_folder,
            self.btn_cancel,
        ):
            general_row.addWidget(button)
        general_row.addStretch(1)
        for button in (
            self.btn_scrape_presetup,
            self.btn_presetup,
            self.btn_presetup_llm,
            self.btn_e2e_one,
        ):
            presetup_row.addWidget(button)
        presetup_row.addStretch(1)
        for button in (self.btn_pick_shared, self.btn_back_main):
            git_row.addWidget(button)
        git_row.addStretch(1)
        layout.addLayout(general_row)
        layout.addLayout(presetup_row)
        layout.addLayout(git_row)

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
            "Presetup Scrape keeps 5 URLs per study level for a quick test run. "
            "Tick study levels before full Scrape URLs to scrape only those listings. "
            "After Presetup download_and_clean, review HTML and markdown, then edit .env / cleanup code before Presetup LLM. "
            "Execute downloads, cleans, and sends each course to the LLM one at a time. "
            "(5) Run Full Pipeline with One Course: updates the pin from course_urls.csv then runs download → clean → LLM → export for one course (after Scrape URLs). "
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
            self.btn_scrape_presetup,
            self.btn_scrape,
            self.btn_presetup,
            self.btn_presetup_llm,
            self.btn_execute,
            self.btn_e2e_one,
            self.btn_pick_shared,
            self.btn_back_main,
        )

    def refresh_status(self) -> None:
        self.registry_by_folder = load_registry_by_folder(self.repo_root)
        self._shared_baseline_tag = load_shared_baseline_tag(
            self.repo_root,
            self.config.get("shared_baseline_tag") or None,
        )
        self.btn_pick_shared.setText(f"Pick Shared ({self._shared_baseline_tag})")
        self.btn_pick_shared.setToolTip(
            f"git restore shared/ from {self._shared_baseline_tag} "
            "(registry baseline; overwrites local shared changes)"
        )
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

        if self._running_task_id in {"presetup_llm", "execute", "e2e_one"}:
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
                msg = f"Presetup download_and_clean: {min(downloaded, total)}/{total}"

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

    def _on_selection(self, *, skip_activate: bool = False) -> None:
        row = self._selected_row()
        running = self.runner is not None and self.runner.isRunning()
        self._sync_level_checks(row)
        if not row:
            self.selected_label.setText("Selected: (none)")
            for button in self._action_buttons():
                button.setEnabled(False)
            self.btn_folder.setEnabled(False)
            self.btn_e2e_one.setEnabled(False)
            self.btn_pick_shared.setEnabled(True)
            self.btn_back_main.setEnabled(True)
            return
        label = row["name"]
        if row.get("cloudflare"):
            label += "  [Cloudflare]"
        pin = get_pin_for_folder(self.repo_root, row["name"], self.config)
        if pin and pin.get("course_url"):
            url = str(pin["course_url"])
            if len(url) > 80:
                url = url[:77] + "..."
            label += f"\nE2E pin [{pin.get('study_level', '')}]: {url}"
            lv = pin.get("study_level")
            if lv in self.level_checks and self.level_checks[lv].isEnabled():
                for key, box in self.level_checks.items():
                    box.setChecked(key == lv)
        self.selected_label.setText(f"Selected: {label}")
        self.btn_folder.setEnabled(True)
        if running:
            return
        self.btn_scrape_presetup.setEnabled(True)
        self.btn_scrape.setEnabled(True)
        self.btn_e2e_one.setEnabled(row["urls"] == "done" or bool(row.get("url_count")))
        self.btn_pick_shared.setEnabled(True)
        self.btn_back_main.setEnabled(True)
        self.btn_presetup.setEnabled(row.get("can_presetup", False))
        self.btn_presetup_llm.setEnabled(row.get("can_presetup_llm", False))
        self.btn_execute.setEnabled(row.get("can_execute", False))
        if (
            not skip_activate
            and self._activate_on_select
            and row
            and not running
            and row["name"] != self._last_activated_name
        ):
            self._activate_university(row)

    def _activate_university(self, row: dict) -> None:
        name = row["name"]
        code_dir = Path(row["path"]) / "code"
        if self._skip_registry_checkout_for == "*":
            restored_for = getattr(self, "_back_to_main_uni", "") or ""
            if restored_for and name != restored_for:
                self._skip_registry_checkout_for = ""
        elif self._skip_registry_checkout_for and name != self._skip_registry_checkout_for:
            self._skip_registry_checkout_for = ""
        meta = self.registry_by_folder.get(name)

        skip_pin = self._skip_registry_checkout_for in (name, "*")
        if should_run_registry_checkout(meta) and not skip_pin:
            unit = meta["unit"]
            commit = meta["commit"]
            command = checkout_command(self.repo_root, unit, commit)
            self.terminal.append_info(f"Activate {name}: checkout {unit} @ {commit} (-IncludeShared)")
            self._pending_activate_code_dir = code_dir
            self._start_shell_command("activate", command, name, poll_progress=False)
            return

        if skip_pin:
            self.terminal.append_info(
                f"Activate {name}: skip registry checkout (restored to {self._back_to_main_source_label()})"
            )
            self._finish_activate(name, code_dir)
            return

        if meta and meta.get("slug") in ("aru", "aston"):
            reason = "aru/aston — study-level registry (skip checkout)"
        elif not meta:
            reason = "not in UNIVERSITIES_REGISTRY.md"
        else:
            reason = "no registry commit"
        self.terminal.append_info(f"Activate {name}: skip checkout ({reason})")
        self._finish_activate(name, code_dir)

    def _finish_activate(self, name: str, code_dir: Path) -> None:
        ok, msg = sync_env_from_env_md(code_dir)
        if ok:
            self.terminal.append_info(msg)
            self._last_activated_name = name
            self.statusBar().showMessage(f"Active: {name}")
        else:
            self.terminal.append_stderr(msg)

    def _set_running(self, running: bool) -> None:
        for button in (
            *self._action_buttons(),
            self.refresh_btn,
            self.mode_box,
        ):
            button.setEnabled(not running)
        self.btn_cancel.setEnabled(running)
        if not running:
            self._on_selection(skip_activate=True)

    def _run_phase(self, phase_id: str) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "Select a university", "Click a university row first.")
            return
        if phase_id == "presetup" and not row.get("can_presetup"):
            QMessageBox.warning(self, "Missing input", "Scrape URLs first (course_urls.csv).")
            return
        if phase_id == "presetup_llm" and not row.get("can_presetup_llm"):
            QMessageBox.warning(
                self,
                "Missing input",
                "Run Presetup download_and_clean first, then review HTML and markdown before Presetup LLM.",
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
        if mode == "fresh" and phase_id in {
            "scrape_presetup",
            "scrape_urls",
            "presetup",
            "presetup_llm",
            "execute",
        }:
            ok = QMessageBox.question(
                self,
                "Fresh run",
                "Fresh starts this step over and can overwrite saved progress.\nContinue?",
            )
            if ok != QMessageBox.StandardButton.Yes:
                return None
        if phase_id == "scrape_presetup":
            extra: list[str] = ["--presetup"]
            if mode == "fresh":
                extra.append("--fresh")
            for level in self._selected_levels():
                extra.extend(["--study-level", level])
            return extra
        if phase_id == "scrape_urls":
            extra = []
            if mode == "fresh":
                extra.append("--fresh")
            elif mode == "append":
                extra.append("--append-urls")
            for level in self._selected_levels():
                extra.extend(["--study-level", level])
            return extra
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

    def _precalc_e2e_command(self, uni_name: str) -> list[str]:
        py = sys.executable or "python"
        return [
            py,
            "-u",
            str(self.repo_root / "dashboard" / "precalc_e2e_pins.py"),
            "--uni",
            uni_name,
        ]

    def _run_e2e_one(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, "Select a university", "Click a university row first.")
            return
        if row["urls"] != "done" and not row.get("url_count"):
            QMessageBox.warning(
                self,
                "Scrape URLs first",
                "Step (5) needs output/course_urls.csv (or level CSVs). Run Scrape URLs first.",
            )
            return
        pin = get_pin_for_folder(self.repo_root, row["name"], self.config)
        levels = self._selected_levels()
        if pin and pin.get("study_level"):
            levels = [str(pin["study_level"]).strip().lower()]
        elif not levels:
            levels = ["undergraduate"]
        host = str(self.config.get("ollama_host") or "http://localhost:11434")
        if not _ollama_ok(host):
            QMessageBox.critical(
                self,
                "Ollama not running",
                f"Cannot reach {host}. Start Ollama, then try again.",
            )
            return
        fresh = self._run_mode() == "fresh"
        if fresh:
            ok = QMessageBox.question(
                self,
                "Fresh run",
                "Fresh re-downloads HTML for the one-course pipeline run.\nContinue?",
            )
            if ok != QMessageBox.StandardButton.Yes:
                return
        code_dir = str(Path(row["path"]) / "code")
        pins_file = str(self.config.get("e2e_course_pins_file") or "e2e_course_pins.json")
        e2e_cmd = e2e_one_course_commands(
            self.repo_root,
            code_dir,
            levels,
            fresh=fresh,
            pins_file=pins_file,
        )[0]
        self._command_chain = [e2e_cmd]
        self.terminal.append_info(
            f"(5) Run Full Pipeline with One Course for {row['name']}: precalc pin → download/clean → LLM → normalize → export"
        )
        self._start_shell_command(
            "precalc_e2e",
            self._precalc_e2e_command(row["name"]),
            row["name"],
            poll_progress=False,
        )

    def _phase_command(self, phase_id: str, university: str, extra: list[str]) -> list[str]:
        code_dir = str(self.repo_root / university / "code")
        script = PHASES[phase_id]
        python = sys.executable or "python"
        if phase_id in PHASES:
            return [python, "-u", str(self.repo_root / script), "--code-dir", code_dir, *extra]
        raise ValueError(f"Unknown phase: {phase_id}")

    def _back_to_main_source_label(self) -> str:
        return str(self.config.get("back_to_main_source") or "HEAD").strip() or "HEAD"

    def _pick_shared(self) -> None:
        tag = self._shared_baseline_tag
        ok = QMessageBox.question(
            self,
            "Pick Shared",
            f"Restore shared/ from {tag}?\n\nUncommitted changes under shared/ will be lost.",
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        command = restore_shared_command(self.repo_root, tag)
        self._start_git_task("pick_shared", command, university="")

    def _back_to_main(self) -> None:
        row = self._selected_row()
        uni_name = row["name"] if row else None
        source = self._back_to_main_source_label()
        restore_all = _config_flag(self.config.get("back_to_main_restore_all_unis"), default=True)
        if restore_all:
            n = len(university_folders_for_restore(self.repo_root))
            detail = f"shared/ and all {n} university folders (undo every checkout-uni pin)"
        elif uni_name:
            detail = f"shared/ and:\n  {uni_name}"
        else:
            detail = "shared/ only\n\n(Set back_to_main_restore_all_unis or select a university.)"
        ok = QMessageBox.question(
            self,
            "Restore HEAD",
            f"Restore working tree from `{source}` (current branch tip):\n  {detail}\n\n"
            "Discards uncommitted changes (staged and unstaged) and removes untracked files "
            "under those paths. Ignored files (e.g. most output/) are kept.\n"
            "Undoes checkout-uni pins. You stay on branch main.\n"
            "dashboard/ and other paths are not changed.",
        )
        if ok != QMessageBox.StandardButton.Yes:
            return
        fetch = _config_flag(self.config.get("back_to_main_fetch_origin"), default=False)
        steps = back_to_main_command_chain(
            self.repo_root,
            uni_name,
            fetch_origin=fetch,
            source=source,
            all_universities=restore_all,
        )
        self._git_follow_up = steps[1:]
        self._back_to_main_uni = uni_name or ""
        command = steps[0]
        self._start_git_task("back_to_main", command, university=uni_name or "")

    def _start_git_task(self, task_id: str, command: list[str], university: str) -> None:
        if self.runner and self.runner.isRunning():
            return
        self.terminal.append_info(f"Starting {task_id}")
        self.terminal.append_info(" ".join(command))
        self._running_university = university
        self._running_task_id = task_id
        self._last_progress_key = ""
        self.runner = TaskRunner(task_id, command, self.repo_root)
        self.runner.stdout_ready.connect(self.terminal.append_stdout)
        self.runner.stderr_ready.connect(self.terminal.append_stderr)
        self.runner.finished.connect(self._on_git_finished)
        self.runner.failed.connect(self._on_failed)
        self.runner.start()
        self._set_running(True)
        self.statusBar().showMessage(f"Running {task_id}")

    def _on_git_finished(self, task_id: str, exit_code: int, duration: float) -> None:
        follow_up = getattr(self, "_git_follow_up", None)
        if task_id == "back_to_main" and exit_code == 0 and follow_up:
            next_cmd = follow_up.pop(0)
            self.terminal.append_info(f"back_to_main step 2 ({duration:.0f}s)")
            self.terminal.append_info(" ".join(next_cmd))
            self.runner = TaskRunner("back_to_main", next_cmd, self.repo_root)
            self.runner.stdout_ready.connect(self.terminal.append_stdout)
            self.runner.stderr_ready.connect(self.terminal.append_stderr)
            self.runner.finished.connect(self._on_git_finished)
            self.runner.failed.connect(self._on_failed)
            self.runner.start()
            return
        self._git_follow_up = []
        if task_id == "back_to_main" and exit_code == 0:
            uni = getattr(self, "_back_to_main_uni", "") or ""
            restore_all = _config_flag(self.config.get("back_to_main_restore_all_unis"), default=True)
            if restore_all:
                self._skip_registry_checkout_for = "*"
                if uni:
                    self._last_activated_name = uni
            else:
                self._skip_registry_checkout_for = uni if uni else "*"
                if uni:
                    self._last_activated_name = uni
            self.terminal.append_info(
                f"Restored to {self._back_to_main_source_label()}. "
                "Registry checkout paused (select another university to pin again)."
            )
        self.terminal.append_info(f"{task_id} finished in {duration:.0f}s (exit {exit_code})")
        self._job_done("Ready" if exit_code == 0 else f"Failed: {task_id}")

    def _start_command(self, task_id: str, university: str, extra: list[str]) -> None:
        if self.runner and self.runner.isRunning():
            return
        command = self._phase_command(task_id, university, extra)
        self.terminal.append_info(f"Starting {task_id} for {university}")
        self._start_shell_command(task_id, command, university, poll_progress=True)

    def _start_shell_command(
        self,
        task_id: str,
        command: list[str],
        university: str,
        *,
        poll_progress: bool = False,
    ) -> None:
        if self.runner and self.runner.isRunning():
            return
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
        if poll_progress:
            self.refresh_timer.setInterval(2000)
            self.refresh_timer.start()

    def _on_finished(self, task_id: str, exit_code: int, duration: float) -> None:
        if task_id == "activate":
            code_dir = getattr(self, "_pending_activate_code_dir", None)
            name = self._running_university
            if exit_code == 0 and code_dir is not None:
                self._finish_activate(name, code_dir)
            elif exit_code != 0:
                self.terminal.append_stderr(f"Activate checkout failed (exit {exit_code})")
                if code_dir is not None:
                    ok, msg = sync_env_from_env_md(code_dir)
                    if ok:
                        self.terminal.append_info(f"{msg} (checkout failed)")
            self.terminal.append_info(f"activate finished in {duration:.0f}s (exit {exit_code})")
            self._job_done("Ready" if exit_code == 0 else "Activate failed")
            return
        if task_id == "precalc_e2e" and exit_code == 0 and self._command_chain:
            next_cmd = self._command_chain.pop(0)
            self.terminal.append_info(f"E2E pin updated ({duration:.0f}s); starting pipeline for one course")
            self.refresh_status()
            self._start_shell_command("e2e_one", next_cmd, self._running_university, poll_progress=True)
            return
        if task_id == "e2e_one" and exit_code == 0 and self._command_chain:
            next_cmd = self._command_chain.pop(0)
            self.terminal.append_info(f"e2e_one step 1 done ({duration:.0f}s); starting execute pipeline")
            self._start_shell_command("e2e_one", next_cmd, self._running_university, poll_progress=True)
            return
        self._command_chain = []
        self.terminal.append_info(f"{task_id} finished in {duration:.0f}s (exit {exit_code})")
        self._job_done("Ready" if exit_code == 0 else f"Failed: {task_id}")

    def _on_failed(self, task_id: str, message: str, exit_code: int) -> None:
        if task_id in {"e2e_one", "precalc_e2e"}:
            self._command_chain = []
        if task_id == "activate":
            code_dir = getattr(self, "_pending_activate_code_dir", None)
            if code_dir is not None:
                ok, msg = sync_env_from_env_md(code_dir)
                if ok:
                    self.terminal.append_info(f"{msg} (after activate error)")
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


def _config_flag(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("", "default"):
        return default
    return text in ("1", "true", "yes", "on")


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
