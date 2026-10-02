"""Library panel: browse sounds by category as cards; import/rename/delete/preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QGridLayout, QInputDialog, QLabel,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from audio.errors import StudioError
from ui.library_model import CATEGORIES, CATEGORY_ICONS, SoundItem, SoundLibrary


class SoundCard(QFrame):
    add_clicked = Signal(str)
    preview_clicked = Signal(str)
    delete_clicked = Signal(str)
    recategorize = Signal(str, str)

    def __init__(self, item: SoundItem, parent=None) -> None:
        super().__init__(parent)
        self.item = item
        self.setObjectName("Card")
        self.setFixedWidth(190)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)

        icon = QLabel(CATEGORY_ICONS.get(item.category, "🎵"))
        icon.setStyleSheet("font-size: 26px;")
        lay.addWidget(icon)

        name = QLabel(item.name)
        name.setWordWrap(True)
        name.setStyleSheet("font-weight: 600;")
        lay.addWidget(name)

        mins, secs = divmod(int(item.duration_s), 60)
        lay.addWidget(QLabel(f"{mins}:{secs:02d} • {'loopable' if item.loopable else 'one-shot'}"))

        cat = QComboBox()
        cat.addItems(CATEGORIES)
        cat.setCurrentText(item.category)
        cat.currentTextChanged.connect(lambda c: self.recategorize.emit(item.id, c))
        lay.addWidget(cat)

        row = QVBoxLayout()
        preview_btn = QPushButton("▶ Preview")
        preview_btn.clicked.connect(lambda: self.preview_clicked.emit(item.id))
        row.addWidget(preview_btn)

        add_btn = QPushButton("＋ Add to Mixer")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(lambda: self.add_clicked.emit(item.id))
        row.addWidget(add_btn)

        del_btn = QPushButton("Delete")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(item.id))
        row.addWidget(del_btn)
        lay.addLayout(row)


class LibraryPanel(QWidget):
    add_to_mixer = Signal(SoundItem)
    play_preview = Signal(str)   # file path

    def __init__(self, library: SoundLibrary, parent=None) -> None:
        super().__init__(parent)
        self.library = library

        outer = QVBoxLayout(self)
        title = QLabel("Sound Library")
        title.setObjectName("SectionTitle")
        outer.addWidget(title)

        note = QLabel("Only use audio you have permission to use.")
        note.setStyleSheet("color: #9ba1ad; font-style: italic;")
        outer.addWidget(note)

        import_btn = QPushButton("⬆ Import Sound Files")
        import_btn.setObjectName("Primary")
        import_btn.clicked.connect(self._import_files)
        outer.addWidget(import_btn, alignment=Qt.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self.grid = QGridLayout(self._grid_host)
        self.grid.setSpacing(12)
        scroll.setWidget(self._grid_host)
        outer.addWidget(scroll)

        self.refresh()

    def refresh(self) -> None:
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        if not self.library.items:
            empty = QLabel("No sounds yet. Import a WAV, MP3 or FLAC file to get started.")
            empty.setStyleSheet("color: #9ba1ad; padding: 20px;")
            self.grid.addWidget(empty, 0, 0)
            return
        cols = 4
        for idx, item in enumerate(self.library.items):
            card = SoundCard(item)
            card.add_clicked.connect(self._on_add)
            card.preview_clicked.connect(self._on_preview)
            card.delete_clicked.connect(self._on_delete)
            card.recategorize.connect(self._on_recategorize)
            self.grid.addWidget(card, idx // cols, idx % cols)

    def _import_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Import sound files", "", "Audio files (*.wav *.mp3 *.flac)"
        )
        if not paths:
            return
        category, ok = QInputDialog.getItem(
            self, "Category", "File category:", CATEGORIES, 0, False
        )
        if not ok:
            category = "Other"
        errors = []
        for p in paths:
            try:
                self.library.import_file(p, category)
            except StudioError as exc:
                errors.append(str(exc))
        self.refresh()
        if errors:
            QMessageBox.warning(self, "Some files were skipped", "\n".join(errors))

    def _on_add(self, item_id: str) -> None:
        item = next((i for i in self.library.items if i.id == item_id), None)
        if item:
            self.add_to_mixer.emit(item)

    def _on_preview(self, item_id: str) -> None:
        item = next((i for i in self.library.items if i.id == item_id), None)
        if item:
            self.play_preview.emit(item.path)

    def _on_delete(self, item_id: str) -> None:
        item = next((i for i in self.library.items if i.id == item_id), None)
        if not item:
            return
        if QMessageBox.question(self, "Delete sound", f"Delete '{item.name}'?") == QMessageBox.Yes:
            self.library.delete(item_id)
            self.refresh()

    def _on_recategorize(self, item_id: str, category: str) -> None:
        self.library.set_category(item_id, category)
