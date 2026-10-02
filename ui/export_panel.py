"""Export panel: pick duration/format/quality, generate, preview, save."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from audio.exporter import ExportSettings, RenderResult, export_track, render_preview
from ui.render_worker import RenderWorker

DURATION_PRESETS = {
    "5 minutes": 5 * 60, "10 minutes": 10 * 60, "30 minutes": 30 * 60,
    "1 hour": 60 * 60, "2 hours": 2 * 60 * 60, "8 hours": 8 * 60 * 60, "Custom…": None,
}
QUALITIES = {"128 kbps": 128, "192 kbps": 192, "256 kbps": 256, "320 kbps": 320}


class ExportPanel(QWidget):
    request_layers = Signal()   # main window connects this and calls back with layers

    def __init__(self, exports_dir: Path, previews_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.exports_dir = exports_dir
        self.previews_dir = previews_dir
        self._get_layers = None   # set by MainWindow: Callable[[], list[Layer]]
        self._worker: RenderWorker | None = None
        self._last_result: RenderResult | None = None

        outer = QVBoxLayout(self)
        title = QLabel("Export")
        title.setObjectName("SectionTitle")
        outer.addWidget(title)

        outer.addWidget(QLabel("Filename"))
        self.filename = QLineEdit("peaceful_rain_sleep_01")
        outer.addWidget(self.filename)

        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Duration"))
        self.duration_box = QComboBox()
        self.duration_box.addItems(DURATION_PRESETS.keys())
        self.duration_box.currentTextChanged.connect(self._on_duration_changed)
        col1.addWidget(self.duration_box)
        self.custom_duration = QLineEdit("15")
        self.custom_duration.setPlaceholderText("minutes")
        self.custom_duration.setVisible(False)
        col1.addWidget(self.custom_duration)
        row.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Format"))
        self.format_box = QComboBox()
        self.format_box.addItems(["MP3", "WAV", "FLAC"])
        self.format_box.currentTextChanged.connect(self._on_format_changed)
        col2.addWidget(self.format_box)
        row.addLayout(col2)

        col3 = QVBoxLayout()
        col3.addWidget(QLabel("Quality"))
        self.quality_box = QComboBox()
        self.quality_box.addItems(QUALITIES.keys())
        self.quality_box.setCurrentText("192 kbps")
        col3.addWidget(self.quality_box)
        row.addLayout(col3)
        outer.addLayout(row)

        row2 = QHBoxLayout()
        col4 = QVBoxLayout()
        col4.addWidget(QLabel("Sample rate"))
        self.rate_box = QComboBox()
        self.rate_box.addItems(["44.1 kHz", "48 kHz"])
        col4.addWidget(self.rate_box)
        row2.addLayout(col4)

        col5 = QVBoxLayout()
        col5.addWidget(QLabel("Channels"))
        self.channels_box = QComboBox()
        self.channels_box.addItems(["Stereo", "Mono"])
        col5.addWidget(self.channels_box)
        row2.addLayout(col5)
        outer.addLayout(row2)

        preview_row = QHBoxLayout()
        preview_btn = QPushButton("🎧 Preview Mix (3 min)")
        preview_btn.clicked.connect(self._make_preview)
        preview_row.addWidget(preview_btn)
        self.play_btn = QPushButton("▶")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._toggle_playback)
        preview_row.addWidget(self.play_btn)
        outer.addLayout(preview_row)

        self.status = QLabel("")
        self.status.setStyleSheet("color: #9ba1ad;")
        outer.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setVisible(False)
        outer.addWidget(self.progress)

        btn_row = QHBoxLayout()
        self.generate_btn = QPushButton("🎵 GENERATE AUDIO")
        self.generate_btn.setObjectName("Primary")
        self.generate_btn.clicked.connect(self._generate)
        btn_row.addWidget(self.generate_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.cancel_btn)
        outer.addLayout(btn_row)

        self.save_btn = QPushButton("⬇️ SAVE AUDIO AS…")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_as)
        outer.addWidget(self.save_btn)

        self._player = QMediaPlayer(self)
        self._audio_out = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_out)
        self._player.playbackStateChanged.connect(self._on_playback_state)

    # --- wiring from MainWindow -------------------------------------------------
    def set_layers_provider(self, fn) -> None:
        self._get_layers = fn

    # --- UI reactions ------------------------------------------------------------
    def _on_duration_changed(self, text: str) -> None:
        self.custom_duration.setVisible(DURATION_PRESETS[text] is None)

    def _on_format_changed(self, fmt: str) -> None:
        self.quality_box.setEnabled(fmt == "MP3")

    def duration_seconds(self) -> float:
        preset = DURATION_PRESETS[self.duration_box.currentText()]
        if preset is not None:
            return float(preset)
        try:
            minutes = float(self.custom_duration.text())
        except ValueError:
            minutes = 0.0
        return minutes * 60.0

    def _settings(self, output_path: Path) -> ExportSettings:
        fmt = self.format_box.currentText().lower()
        return ExportSettings(
            output_path=output_path,
            duration_s=self.duration_seconds(),
            fmt=fmt,
            sample_rate=48000 if self.rate_box.currentText().startswith("48") else 44100,
            channels=1 if self.channels_box.currentText() == "Mono" else 2,
            bitrate_kbps=QUALITIES[self.quality_box.currentText()],
        )

    def _layers(self):
        return self._get_layers() if self._get_layers else []

    def _busy(self, running: bool) -> None:
        self.generate_btn.setEnabled(not running)
        self.cancel_btn.setVisible(running)
        self.progress.setVisible(running)
        if not running:
            self.progress.setValue(0)

    # --- Generate (full export) ---------------------------------------------------
    def _generate(self) -> None:
        layers = self._layers()
        if not layers:
            QMessageBox.information(self, "Nothing to generate",
                                     "Add at least one sound to the mixer first.")
            return
        if self.duration_seconds() <= 0:
            QMessageBox.information(self, "Invalid duration", "Enter a duration greater than 0.")
            return
        name = self.filename.text().strip() or "nature_sound"
        fmt = self.format_box.currentText().lower()
        out_path = self.exports_dir / f"{name}.{fmt}"
        settings = self._settings(out_path)

        def do_render(progress_cb, cancel_cb):
            return export_track(layers, settings, progress_cb, cancel_cb)

        self._run(do_render, "Generating…")

    def _make_preview(self) -> None:
        layers = self._layers()
        if not layers:
            QMessageBox.information(self, "Nothing to preview",
                                     "Add at least one sound to the mixer first.")
            return
        out_path = self.previews_dir / "preview.wav"

        def do_render(progress_cb, cancel_cb):
            return render_preview(layers, out_path, 180.0, progress=progress_cb, is_cancelled=cancel_cb)

        self._run(do_render, "Building preview…", is_preview=True)

    def _run(self, render_fn, status_text: str, is_preview: bool = False) -> None:
        self._busy(True)
        self.status.setText(status_text)
        self._worker = RenderWorker(render_fn, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(lambda r: self._on_finished(r, is_preview))
        self._worker.failed.connect(self._on_failed)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _cancel(self) -> None:
        if self._worker:
            self._worker.request_cancel()
            self.status.setText("Cancelling…")

    def _on_progress(self, frac: float, eta: float) -> None:
        self.progress.setValue(int(frac * 100))
        m, s = divmod(max(0, int(eta)), 60)
        self.status.setText(f"Progress: {int(frac * 100)}%  •  Estimated remaining time: {m}:{s:02d}")

    def _on_finished(self, result: RenderResult, is_preview: bool) -> None:
        self._busy(False)
        if is_preview:
            self.status.setText("Preview ready.")
            self.play_btn.setEnabled(True)
            self._player.setSource(str(result.path))
        else:
            self.status.setText(f"Done — saved to {result.path}")
            self._last_result = result
            self.save_btn.setEnabled(True)
        if result.warnings:
            QMessageBox.warning(self, "Some layers were skipped", "\n".join(result.warnings))

    def _on_failed(self, message: str) -> None:
        self._busy(False)
        self.status.setText("Failed.")
        QMessageBox.critical(self, "Could not generate audio", message)

    def _on_cancelled(self) -> None:
        self._busy(False)
        self.status.setText("Cancelled.")

    def _toggle_playback(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_playback_state(self, state) -> None:
        self.play_btn.setText("⏸" if state == QMediaPlayer.PlayingState else "▶")

    def _save_as(self) -> None:
        if not self._last_result:
            return
        src = self._last_result.path
        dest, _ = QFileDialog.getSaveFileName(self, "Save audio as", src.name)
        if dest:
            import shutil
            shutil.copy2(src, dest)
            self.status.setText(f"Saved to {dest}")
