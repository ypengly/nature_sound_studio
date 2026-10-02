"""Where NatureSound Studio keeps its files.

Everything lives in ~/NatureSoundStudio by default. Set the environment
variable NATURESOUND_HOME to use a different folder.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "NatureSound Studio"
DATA_DIR = Path(os.environ.get("NATURESOUND_HOME", Path.home() / "NatureSoundStudio"))
SUBFOLDERS = ("Projects", "Generated", "Presets", "SourceSounds", "Exports", "Previews")


def ensure_dirs() -> dict[str, Path]:
    """Create the folder tree (if missing) and return {name: path}."""
    dirs: dict[str, Path] = {}
    for name in SUBFOLDERS:
        path = DATA_DIR / name
        path.mkdir(parents=True, exist_ok=True)
        dirs[name] = path
    return dirs
