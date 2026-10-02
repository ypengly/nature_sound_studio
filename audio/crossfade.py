"""Equal-power crossfading: the heart of the seamless looping."""
from __future__ import annotations

import numpy as np


def equal_power_curves(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (fade_out, fade_in) curves whose squares always sum to 1."""
    t = np.linspace(0.0, 1.0, n, dtype=np.float32)
    return np.cos(t * np.pi / 2), np.sin(t * np.pi / 2)


def crossfade(a: np.ndarray, b: np.ndarray, overlap: int) -> np.ndarray:
    """Join `a` and `b`, blending the last `overlap` frames of a with the first of b."""
    overlap = min(overlap, len(a), len(b))
    if overlap <= 0:
        return np.concatenate([a, b])
    fade_out, fade_in = equal_power_curves(overlap)
    middle = a[-overlap:] * fade_out[:, None] + b[:overlap] * fade_in[:, None]
    return np.concatenate([a[:-overlap], middle, b[overlap:]])
