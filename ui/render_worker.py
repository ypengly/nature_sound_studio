"""Runs export_track / render_preview on a background thread."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThread, Signal

from audio.errors import Cancelled, StudioError


class RenderWorker(QThread):
    progress = Signal(float, float)     # fraction 0..1, seconds remaining
    finished_ok = Signal(object)        # RenderResult
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, render_fn: Callable, parent=None) -> None:
        """`render_fn(progress_cb, cancel_cb) -> RenderResult`"""
        super().__init__(parent)
        self._render_fn = render_fn
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        try:
            result = self._render_fn(
                lambda frac, eta: self.progress.emit(frac, eta),
                lambda: self._cancel_requested,
            )
        except Cancelled:
            self.cancelled.emit()
        except StudioError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # last-resort net: never crash the app
            self.failed.emit(f"Unexpected error: {exc}")
        else:
            self.finished_ok.emit(result)
