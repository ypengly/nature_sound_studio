"""LayerStream: turns one short source sound into an endless, non-repeating stream.

It repeatedly picks a random slice of the source (random start, random length),
nudges its volume and pan a little, and joins it to the previous slice with an
equal-power crossfade of random length. Because every slice is different, the
result has no obvious loop point.
"""
from __future__ import annotations

import numpy as np

from .crossfade import crossfade
from .effects import db_to_lin, pan_stereo


class LayerStream:
    def __init__(
        self,
        audio: np.ndarray,
        sample_rate: int,
        rng: np.random.Generator,
        clip_seconds: tuple[float, float] = (20.0, 45.0),
        overlap_seconds: float = 4.0,
    ) -> None:
        self.audio = audio
        self.sr = sample_rate
        self.rng = rng
        self.clip_range = clip_seconds
        n = len(audio)
        # Never let the crossfade exceed a third of the source.
        self.overlap = max(1, min(int(overlap_seconds * sample_rate), n // 3))
        self._buf = np.zeros((0, audio.shape[1]), dtype=np.float32)

    def _new_clip(self) -> np.ndarray:
        n = len(self.audio)
        wanted = int(self.rng.uniform(*self.clip_range) * self.sr)
        length = max(1, min(wanted, int(n * 0.9)))  # <90% so the start can vary
        start = int(self.rng.integers(0, n - length + 1))
        clip = self.audio[start:start + length] * np.float32(db_to_lin(self.rng.uniform(-1.5, 1.5)))
        return pan_stereo(clip, float(self.rng.uniform(-0.08, 0.08)))

    def _append(self, clip: np.ndarray) -> None:
        if len(self._buf) == 0:
            self._buf = clip
            return
        overlap = int(self.overlap * self.rng.uniform(0.6, 1.0))  # randomized fades
        overlap = max(1, min(overlap, len(clip) // 3, len(self._buf)))
        self._buf = crossfade(self._buf, clip, overlap)

    def read(self, n: int) -> np.ndarray:
        """Return the next `n` frames. The last `overlap` frames stay buffered
        because the next crossfade may still change them."""
        while len(self._buf) < n + self.overlap:
            self._append(self._new_clip())
        out, self._buf = self._buf[:n], self._buf[n:]
        return out
