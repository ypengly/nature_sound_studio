"""Small DSP helpers. Audio is float32 with shape (frames, channels)."""
from __future__ import annotations

import numpy as np


def db_to_lin(db: float) -> float:
    return float(10 ** (db / 20.0))


def pan_stereo(x: np.ndarray, pan: float) -> np.ndarray:
    """Constant-power balance. pan: -1 = left, 0 = centre (unchanged), +1 = right."""
    if abs(pan) < 1e-4:
        return x
    theta = (float(np.clip(pan, -1, 1)) + 1.0) * np.pi / 4.0
    out = x.copy()
    out[:, 0] *= np.float32(np.cos(theta) * np.sqrt(2))
    out[:, 1] *= np.float32(np.sin(theta) * np.sqrt(2))
    return out


def edge_fade(chunk: np.ndarray, start: int, total: int, fade_len: int) -> np.ndarray:
    """Equal-power fade-in / fade-out on the first/last `fade_len` frames of a track.

    `chunk` covers frames [start, start + len(chunk)) of a `total`-frame track.
    Works in place and returns the chunk.
    """
    n = len(chunk)
    if fade_len <= 0 or (start >= fade_len and start + n <= total - fade_len):
        return chunk
    idx = np.arange(start, start + n, dtype=np.float64)
    g = np.minimum(np.clip(idx / fade_len, 0, 1), np.clip((total - idx) / fade_len, 0, 1))
    chunk *= np.sin(g * np.pi / 2).astype(np.float32)[:, None]
    return chunk
