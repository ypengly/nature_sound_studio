"""MainWindow: assembles the header, preset bar, and the three panels."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QTabWidget,
    QVBoxLayout, QWidget,
)

from config import ensure_dirs
from ui.export_panel import ExportPanel
from ui.library_model import SoundLibrary
from ui.library_panel import LibraryPanel
from ui.mixer_panel import MixerPanel
from ui.style import DARK_STYLE

PRESETS_FILE = Path(__file__).resolve().parent.parent / "presets" / "presets.json"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NatureSound Studio")
        self.resize(1180, 780)
        self.setStyleSheet(DARK_STYLE)

        self.dirs = ensure_dirs()
        self.library = SoundLibrary.load(self.dirs["SourceSounds"], self.dirs["Projects"] / "library.json")

        self._preview_player = QMediaPlayer(self)
        self._preview_audio_out = QAudioOutput(self)
        self._preview_player.setAudioOutput(self._preview_audio_out)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        root.addLayout(self._build_header())
        root.addLayout(self._build_preset_bar())

        self.library_panel = LibraryPanel(self.library)
        self.mixer_panel = MixerPanel()
        self.export_panel = ExportPanel(self.dirs["Exports"], self.dirs["Previews"])
        self.export_panel.set_layers_provider(lambda: self.mixer_panel.layers)

        self.library_panel.add_to_mixer.connect(self.mixer_panel.add_sound)
        self.library_panel.play_preview.connect(self._play_source_preview)

        tabs = QTabWidget()
        tabs.addTab(self.library_panel, "🎧 Library")
        tabs.addTab(self.mixer_panel, "🎚️ Mixer")
        tabs.addTab(self.export_panel, "📤 Export")
        root.addWidget(tabs, stretch=1)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        text_col = QVBoxLayout()
        title = QLabel("NatureSound Studio")
        title.setObjectName("Header")
        subtitle = QLabel("Create relaxing ambient sounds in minutes.")
        subtitle.setObjectName("SubHeader")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        row.addLayout(text_col)
        row.addStretch()
        return row

    def _build_preset_bar(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(QLabel("Presets:"))
        try:
            self.presets = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.presets = {}
        for name in self.presets:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _checked, n=name: self._apply_preset(n))
            row.addWidget(btn)
        row.addStretch()
        return row

    def _apply_preset(self, name: str) -> None:
        volumes = self.presets.get(name, {})
        missing = self.mixer_panel.apply_preset(volumes, self.library)
        if missing:
            QMessageBox.information(
                self, "Preset partially applied",
                "No sound is in your library yet for: " + ", ".join(missing) +
                ".\nImport a sound and set its category to add that layer.",
            )

    def _play_source_preview(self, path: str) -> None:
        self._preview_player.setSource(path)
        self._preview_player.play()

    def closeEvent(self, event) -> None:
        self._preview_player.stop()
        self.export_panel._player.stop()
        super().closeEvent(event)
