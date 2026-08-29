"""Run one PowerShell pipeline script in a background thread."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class TaskRunner(QThread):
    started = Signal(str)
    finished = Signal(str, int, float)
    failed = Signal(str, str, int)
    stdout_ready = Signal(str)
    stderr_ready = Signal(str)

    def __init__(
        self,
        task_id: str,
        command: list[str],
        cwd: Path,
        timeout_seconds: int = 0,
    ):
        super().__init__()
        self.task_id = task_id
        self.command = command
        self.cwd = Path(cwd)
        self.timeout_seconds = timeout_seconds
        self.process: subprocess.Popen[str] | None = None
        self._should_stop = False
        self._start_time = 0.0

    def run(self) -> None:
        self._start_time = time.time()
        self.started.emit(self.task_id)
        try:
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            self.process = subprocess.Popen(
                self.command,
                cwd=str(self.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                env=env,
            )
            self._stream_output()
            if self.timeout_seconds > 0:
                exit_code = self.process.wait(timeout=self.timeout_seconds)
            else:
                exit_code = self.process.wait()
        except subprocess.TimeoutExpired:
            self.stop()
            self.failed.emit(self.task_id, "Timed out", -2)
            return
        except Exception as exc:
            self.failed.emit(self.task_id, str(exc), -3)
            return

        duration = time.time() - self._start_time
        if self._should_stop:
            self.failed.emit(self.task_id, "Cancelled", -1)
        elif exit_code == 0:
            self.finished.emit(self.task_id, exit_code, duration)
        else:
            self.failed.emit(self.task_id, f"Exit code {exit_code}", exit_code)

    def _stream_output(self) -> None:
        if not self.process:
            return

        def read_stdout() -> None:
            if self.process and self.process.stdout:
                for line in self.process.stdout:
                    if self._should_stop:
                        break
                    self.stdout_ready.emit(line.rstrip("\n"))

        def read_stderr() -> None:
            if self.process and self.process.stderr:
                for line in self.process.stderr:
                    if self._should_stop:
                        break
                    self.stderr_ready.emit(line.rstrip("\n"))

        stdout_thread = threading.Thread(target=read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()

    def stop(self) -> None:
        self._should_stop = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
