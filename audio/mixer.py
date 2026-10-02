"""Layers + Mixer: combine LayerStreams into the final track, chunk by chunk."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from .effects import edge_fade, pan_stereo
from .errors import EmptyMixError, StudioError
from .generator import LayerStream
from .loader import load_audio


@dataclass
class Layer:
    sound_id: str
    name: str
    path: str
    volume: float = 0.7      # 0.0 .. 1.0
    pan: float = 0.0         # -1.0 (left) .. +1.0 (right)
    mute: bool = False
    solo: bool = False
    enabled: bool = True


def audible_layers(layers: list[Layer]) -> list[Layer]:
    """Apply enable / mute / solo rules."""
    live = [l for l in layers if l.enabled and not l.mute and l.volume > 0]
    if any(l.solo for l in layers if l.enabled):
        return [l for l in live if l.solo]
    return live


class Mixer:
    """Reads audio from every audible layer and sums it.

    Sources are loudness-matched when loaded, so a layer's volume slider is a
    true relative level. The sum is scaled to a steady overall loudness and
    passed through a soft limiter so it can never clip.
    """

    def __init__(self, layers: list[Layer], sample_rate: int, channels: int, seed: int | None = None):
        self.sr = sample_rate
        self.channels = channels
        self.warnings: list[str] = []
        rng = np.random.default_rng(seed)
        cache: dict[str, np.ndarray] = {}   # same file used twice is loaded once
        self._parts: list[tuple[LayerStream, Layer]] = []

        for layer in audible_layers(layers):
            try:
                if layer.path not in cache:
                    cache[layer.path] = load_audio(layer.path, sample_rate)
            except Exception as exc:  # one bad file must never kill the render
                self.warnings.append(f"Skipped '{layer.name}': {exc}")
                continue
            stream_rng = np.random.default_rng(int(rng.integers(2**32)))
            self._parts.append((LayerStream(cache[layer.path], sample_rate, stream_rng), layer))

        if not self._parts:
            raise EmptyMixError(
                "There is nothing to play. Add at least one sound to the mixer "
                "(and make sure it is enabled, unmuted and above 0%)."
            )
        power = sum(l.volume ** 2 for _, l in self._parts)
        self.master = float(min(1.2 / np.sqrt(power), 4.0))

    def read(self, n: int) -> np.ndarray:
        mix = np.zeros((n, 2), dtype=np.float32)
        for stream, layer in self._parts:
            mix += pan_stereo(stream.read(n), layer.pan) * np.float32(layer.volume)
        mix *= np.float32(self.master)
        np.tanh(mix, out=mix)  # soft limiter
        if self.channels == 1:
            mix = mix.mean(axis=1, keepdims=True)
        return mix


def render_chunks(
    mixer: Mixer,
    duration_s: float,
    edge_fade_s: float = 1.5,
    chunk_seconds: float = 30.0,
) -> Iterator[tuple[np.ndarray, int, int]]:
    """Yield (chunk, frames_done, total_frames). Only one chunk is ever in memory."""
    sr = mixer.sr
    total = int(round(duration_s * sr))
    if total <= 0:
        raise StudioError("Duration must be greater than zero.")
    fade = min(int(edge_fade_s * sr), total // 2)
    chunk_frames = max(1, int(chunk_seconds * sr))
    pos = 0
    while pos < total:
        n = min(chunk_frames, total - pos)
        chunk = edge_fade(mixer.read(n), pos, total, fade)
        pos += n
        yield chunk, pos, total
