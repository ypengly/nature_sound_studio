"""SoundLibrary: the user's collection of source sounds, persisted as JSON."""
from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from audio.errors import InvalidAudioError
from audio.loader import SUPPORTED_EXTENSIONS, probe_duration

CATEGORIES = [
    "Rain", "Storm", "Ocean", "Forest", "Wind", "Fireplace", "Birds",
    "River", "Cafe", "Night", "Room", "Traffic", "Other",
]

CATEGORY_ICONS = {
    "Rain": "🌧️", "Storm": "⛈️", "Ocean": "🌊", "Forest": "🌲", "Wind": "💨",
    "Fireplace": "🔥", "Birds": "🐦", "River": "💧", "Cafe": "☕", "Night": "🌙",
    "Room": "🏠", "Traffic": "🚗", "Other": "🎵",
}


@dataclass
class SoundItem:
    id: str
    name: str
    path: str
    category: str = "Other"
    loopable: bool = True
    duration_s: float = 0.0


@dataclass
class SoundLibrary:
    sounds_dir: Path
    index_path: Path
    items: list[SoundItem] = field(default_factory=list)

    @classmethod
    def load(cls, sounds_dir: Path, index_path: Path) -> "SoundLibrary":
        lib = cls(sounds_dir=sounds_dir, index_path=index_path)
        if index_path.exists():
            try:
                raw = json.loads(index_path.read_text(encoding="utf-8"))
                lib.items = [SoundItem(**item) for item in raw]
            except (json.JSONDecodeError, TypeError):
                pass  # start with an empty library rather than crashing
        # Drop entries whose file has been deleted outside the app.
        lib.items = [i for i in lib.items if Path(i.path).exists()]
        return lib

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps([asdict(i) for i in self.items], indent=2), encoding="utf-8"
        )

    def import_file(self, src: str | Path, category: str = "Other") -> SoundItem:
        src = Path(src)
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise InvalidAudioError(
                f"'{src.name}' is not a supported format (use WAV, MP3 or FLAC)."
            )
        duration = probe_duration(src)  # raises InvalidAudioError if unreadable
        self.sounds_dir.mkdir(parents=True, exist_ok=True)
        dest = self.sounds_dir / src.name
        stem, suffix, n = src.stem, src.suffix, 1
        while dest.exists():
            dest = self.sounds_dir / f"{stem}_{n}{suffix}"
            n += 1
        shutil.copy2(src, dest)
        item = SoundItem(id=str(uuid.uuid4()), name=src.stem, path=str(dest),
                         category=category, duration_s=duration)
        self.items.append(item)
        self.save()
        return item

    def rename(self, item_id: str, new_name: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.name = new_name
        self.save()

    def set_category(self, item_id: str, category: str) -> None:
        for item in self.items:
            if item.id == item_id:
                item.category = category
        self.save()

    def set_loopable(self, item_id: str, loopable: bool) -> None:
        for item in self.items:
            if item.id == item_id:
                item.loopable = loopable
        self.save()

    def delete(self, item_id: str) -> None:
        item = next((i for i in self.items if i.id == item_id), None)
        if item is None:
            return
        Path(item.path).unlink(missing_ok=True)
        self.items.remove(item)
        self.save()

    def by_category(self, category: str) -> list[SoundItem]:
        return [i for i in self.items if i.category == category]
