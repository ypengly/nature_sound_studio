"""Mixer panel: one row per layer, with volume, pan, mute, solo, enable, remove."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

from audio.mixer import Layer
from ui.library_model import CATEGORY_ICONS


class LayerRow(QFrame):
    changed = Signal()
    removed = Signal(object)

    def __init__(self, layer: Layer, icon: str, parent=None) -> None:
        super().__init__(parent)
        self.layer = layer
        self.setObjectName("Card")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)

        top = QHBoxLayout()
        top.addWidget(QLabel(f"{icon} {layer.name}", styleSheet="font-weight: 600;"))
        top.addStretch()

        self.enable_btn = self._toggle("On", layer.enabled)
        self.mute_btn = self._toggle("Mute", layer.mute)
        self.solo_btn = self._toggle("Solo", layer.solo)
        for b in (self.enable_btn, self.mute_btn, self.solo_btn):
            top.addWidget(b)

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("Icon")
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        top.addWidget(remove_btn)
        root.addLayout(top)

        vol_row = QHBoxLayout()
        vol_row.addWidget(QLabel("Volume"))
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(int(layer.volume * 100))
        self.vol_label = QLabel(f"{int(layer.volume * 100)}%")
        self.vol_slider.valueChanged.connect(self._on_volume)
        vol_row.addWidget(self.vol_slider, stretch=1)
        vol_row.addWidget(self.vol_label)
        root.addLayout(vol_row)

        pan_row = QHBoxLayout()
        pan_row.addWidget(QLabel("Pan"))
        self.pan_slider = QSlider(Qt.Horizontal)
        self.pan_slider.setRange(-100, 100)
        self.pan_slider.setValue(int(layer.pan * 100))
        self.pan_label = QLabel("Centre")
        self.pan_slider.valueChanged.connect(self._on_pan)
        pan_row.addWidget(self.pan_slider, stretch=1)
        pan_row.addWidget(self.pan_label)
        root.addLayout(pan_row)

    def _toggle(self, text: str, checked: bool) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("Toggle")
        b.setCheckable(True)
        b.setChecked(checked)
        b.toggled.connect(self._on_toggles)
        return b

    def _on_toggles(self) -> None:
        self.layer.enabled = self.enable_btn.isChecked()
        self.layer.mute = self.mute_btn.isChecked()
        self.layer.solo = self.solo_btn.isChecked()
        self.changed.emit()

    def _on_volume(self, value: int) -> None:
        self.layer.volume = value / 100.0
        self.vol_label.setText(f"{value}%")
        self.changed.emit()

    def _on_pan(self, value: int) -> None:
        self.layer.pan = value / 100.0
        self.pan_label.setText("Centre" if value == 0 else (f"L{-value}" if value < 0 else f"R{value}"))
        self.changed.emit()


class MixerPanel(QWidget):
    layers_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.layers: list[Layer] = []
        self._rows: dict[str, LayerRow] = {}

        outer = QVBoxLayout(self)
        title = QLabel("Mixer")
        title.setObjectName("SectionTitle")
        outer.addWidget(title)

        self.hint = QLabel("Add sounds from the library to build your mix.")
        self.hint.setStyleSheet("color: #9ba1ad;")
        outer.addWidget(self.hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self.rows_layout = QVBoxLayout(host)
        self.rows_layout.addStretch()
        scroll.setWidget(host)
        outer.addWidget(scroll)

    def add_sound(self, item) -> None:
        layer = Layer(sound_id=item.id, name=item.name, path=item.path)
        self.layers.append(layer)
        row = LayerRow(layer, CATEGORY_ICONS.get(item.category, "🎵"))
        row.changed.connect(self.layers_changed.emit)
        row.removed.connect(self._remove_row)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self._rows[id(layer)] = row
        self.hint.setVisible(False)
        self.layers_changed.emit()

    def _remove_row(self, row: LayerRow) -> None:
        self.layers.remove(row.layer)
        self._rows.pop(id(row.layer), None)
        row.setParent(None)
        row.deleteLater()
        self.hint.setVisible(not self.layers)
        self.layers_changed.emit()

    def clear(self) -> None:
        for layer in list(self.layers):
            row = self._rows.get(id(layer))
            if row:
                self._remove_row(row)

    def apply_preset(self, volumes: dict[str, float], library) -> list[str]:
        """Add layers for a preset {category: volume 0..1}. Returns categories with no source sound."""
        self.clear()
        missing = []
        for category, volume in volumes.items():
            candidates = library.by_category(category)
            if not candidates:
                missing.append(category)
                continue
            self.add_sound(candidates[0])
            self.layers[-1].volume = volume
            self._rows[id(self.layers[-1])].vol_slider.setValue(int(volume * 100))
        return missing
