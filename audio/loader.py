"""Load audio files into float32 stereo NumPy arrays."""
from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from .errors import InvalidAudioError

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac"}
MIN_SECONDS = 0.5      # shorter files can't be crossfaded sensibly
TARGET_RMS = 0.1       # every source is loudness-matched to this level


def _read_with_pydub(path: Path) -> tuple[np.ndarray, int]:
    from pydub import AudioSegment  # imported lazily: needs FFmpeg

    seg = AudioSegment.from_file(str(path))
    scale = float(1 << (8 * seg.sample_width - 1))
    data = np.asarray(seg.get_array_of_samples(), dtype=np.float32) / scale
    return data.reshape(-1, seg.channels), seg.frame_rate


def _read(path: Path) -> tuple[np.ndarray, int]:
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return data, sr
    except Exception:
        pass  # fall back to pydub/FFmpeg (older libsndfile can't read MP3)
    try:
        return _read_with_pydub(path)
    except Exception as exc:
        raise InvalidAudioError(
            f"'{path.name}' could not be read. It may be corrupted or in an "
            "unsupported format."
        ) from exc


def probe_duration(path: str | Path) -> float:
    """Return duration in seconds, or raise InvalidAudioError."""
    path = Path(path)
    seconds = 0.0
    try:
        info = sf.info(str(path))
        if info.frames > 0 and info.samplerate > 0:
            seconds = info.frames / info.samplerate
    except Exception:
        pass
    if seconds == 0.0:
        try:
            from pydub import AudioSegment

            seconds = len(AudioSegment.from_file(str(path))) / 1000.0
        except Exception as exc:
            raise InvalidAudioError(
                f"'{path.name}' is not a valid audio file (or is corrupted)."
            ) from exc
    if seconds < MIN_SECONDS:
        raise InvalidAudioError(f"'{path.name}' is too short (minimum {MIN_SECONDS} s).")
    return seconds


def load_audio(path: str | Path, sample_rate: int) -> np.ndarray:
    """Load a file as float32 stereo at `sample_rate`, DC-removed and RMS-matched."""
    path = Path(path)
    if not path.exists():
        raise InvalidAudioError(f"'{path.name}' no longer exists on disk.")
    data, sr = _read(path)
    if data.shape[0] < sr * MIN_SECONDS:
        raise InvalidAudioError(f"'{path.name}' is too short (minimum {MIN_SECONDS} s).")

    data = np.nan_to_num(data)
    data = np.repeat(data, 2, axis=1) if data.shape[1] == 1 else data[:, :2]
    if sr != sample_rate:
        g = gcd(sr, sample_rate)
        data = resample_poly(data, sample_rate // g, sr // g, axis=0).astype(np.float32)
    data = data - data.mean(axis=0, keepdims=True)  # remove DC offset (avoids clicks)

    rms = float(np.sqrt(np.mean(np.square(data))))
    if rms < 1e-5:
        raise InvalidAudioError(f"'{path.name}' is silent.")
    data *= np.float32(TARGET_RMS / rms)
    return np.ascontiguousarray(data, dtype=np.float32)
