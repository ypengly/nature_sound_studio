"""Export: render the mix in 30-second chunks and stream it into FFmpeg."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import soundfile as sf

from .errors import Cancelled, DiskSpaceError, ExportError, FFmpegMissingError, StudioError
from .mixer import Layer, Mixer, render_chunks

ProgressFn = Callable[[float, float], None]   # (fraction 0..1, seconds remaining)
CancelFn = Callable[[], bool]

MIN_DURATION_S = 5.0
MAX_DURATION_S = 24 * 3600.0
FORMATS = ("mp3", "wav", "flac")


@dataclass
class ExportSettings:
    output_path: Path
    duration_s: float
    fmt: str = "mp3"
    sample_rate: int = 44100
    channels: int = 2
    bitrate_kbps: int = 192
    seed: int | None = None


@dataclass
class RenderResult:
    path: Path
    warnings: list[str] = field(default_factory=list)


def find_ffmpeg() -> str:
    """Look on PATH, then next to the app (handy for a packaged .exe)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    folders = [Path(sys.executable).parent, Path(__file__).resolve().parent.parent]
    if hasattr(sys, "_MEIPASS"):
        folders.insert(0, Path(sys._MEIPASS))
    for folder in folders:
        for name in ("ffmpeg.exe", "ffmpeg"):
            if (folder / name).is_file():
                return str(folder / name)
    raise FFmpegMissingError(
        "FFmpeg was not found. Install FFmpeg and make sure the 'ffmpeg' command "
        "works in a terminal (see README.md, 'FFmpeg setup'), then try again."
    )


def validate_settings(s: ExportSettings) -> None:
    if not (MIN_DURATION_S <= s.duration_s <= MAX_DURATION_S):
        raise StudioError("Duration must be between 5 seconds and 24 hours.")
    if s.fmt not in FORMATS:
        raise StudioError(f"Unsupported format '{s.fmt}'. Choose MP3, WAV or FLAC.")
    if s.sample_rate not in (44100, 48000):
        raise StudioError("Sample rate must be 44.1 kHz or 48 kHz.")
    if s.channels not in (1, 2):
        raise StudioError("Channels must be mono or stereo.")


def estimate_size_bytes(s: ExportSettings) -> int:
    if s.fmt == "mp3":
        per_second = s.bitrate_kbps * 1000 / 8
    else:
        per_second = s.sample_rate * s.channels * 2 * (1.0 if s.fmt == "wav" else 0.7)
    return int(per_second * s.duration_s)


def check_disk_space(folder: Path, needed: int) -> None:
    free = shutil.disk_usage(folder).free
    if free < needed * 1.1 + 50 * 1024 ** 2:
        raise DiskSpaceError(
            f"Not enough free disk space. This file needs about {needed / 1024 ** 3:.2f} GB "
            f"but only {free / 1024 ** 3:.2f} GB is free."
        )


def _ffmpeg_cmd(ffmpeg: str, s: ExportSettings, out: Path) -> list[str]:
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
           "-f", "f32le", "-ar", str(s.sample_rate), "-ac", str(s.channels), "-i", "pipe:0", "-vn"]
    if s.fmt == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", f"{s.bitrate_kbps}k"]
    elif s.fmt == "flac":
        cmd += ["-c:a", "flac"]
    else:
        cmd += ["-c:a", "pcm_s16le", "-rf64", "auto"]   # rf64 lets WAV pass 4 GB
    return cmd + [str(out)]


def _kill(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
    except Exception:
        pass


def _read_log(log) -> str:
    try:
        log.seek(0)
        text = log.read().decode("utf-8", "replace").strip()
    except Exception:
        text = ""
    return text[-400:] or "unknown FFmpeg error"


def export_track(
    layers: list[Layer],
    s: ExportSettings,
    progress: ProgressFn | None = None,
    is_cancelled: CancelFn | None = None,
) -> RenderResult:
    """Render the mix and encode it with FFmpeg. Writes to a temporary
    '.partial' file first, so a failed or cancelled export never leaves a
    broken file behind."""
    validate_settings(s)
    ffmpeg = find_ffmpeg()
    try:
        s.output_path.parent.mkdir(parents=True, exist_ok=True)
        check_disk_space(s.output_path.parent, estimate_size_bytes(s))
    except OSError as exc:
        raise ExportError(f"Cannot write to the output folder: {exc}") from exc

    mixer = Mixer(layers, s.sample_rate, s.channels, s.seed)
    tmp = s.output_path.with_name(f"{s.output_path.stem}.partial{s.output_path.suffix}")
    log = tempfile.TemporaryFile()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(_ffmpeg_cmd(ffmpeg, s, tmp), stdin=subprocess.PIPE,
                                stderr=log, creationflags=flags)
    except OSError as exc:
        log.close()
        raise ExportError(f"Could not start FFmpeg: {exc}") from exc

    started = time.monotonic()
    ok = False
    try:
        for chunk, done, total in render_chunks(mixer, s.duration_s):
            if is_cancelled and is_cancelled():
                raise Cancelled()
            proc.stdin.write(chunk.astype("<f4", copy=False).tobytes())
            if progress:
                frac = done / total
                eta = (time.monotonic() - started) * (1 - frac) / frac
                progress(frac, eta)
        proc.stdin.close()
        if proc.wait() != 0:
            raise ExportError(f"FFmpeg failed to encode the file: {_read_log(log)}")
        os.replace(tmp, s.output_path)
        ok = True
    except BrokenPipeError:
        proc.wait()
        raise ExportError(f"FFmpeg stopped unexpectedly: {_read_log(log)}") from None
    finally:
        if not ok:
            _kill(proc)
            tmp.unlink(missing_ok=True)
        log.close()
    return RenderResult(s.output_path, mixer.warnings)


def render_preview(
    layers: list[Layer],
    path: Path,
    duration_s: float = 180.0,
    sample_rate: int = 44100,
    progress: ProgressFn | None = None,
    is_cancelled: CancelFn | None = None,
) -> RenderResult:
    """Render a short WAV preview (uses soundfile, so FFmpeg is not needed)."""
    mixer = Mixer(layers, sample_rate, 2)
    path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with sf.SoundFile(str(path), "w", samplerate=sample_rate, channels=2,
                          format="WAV", subtype="PCM_16") as out:
            for chunk, done, total in render_chunks(mixer, duration_s, chunk_seconds=10):
                if is_cancelled and is_cancelled():
                    raise Cancelled()
                out.write(chunk)
                if progress:
                    frac = done / total
                    progress(frac, (time.monotonic() - started) * (1 - frac) / frac)
    except Cancelled:
        path.unlink(missing_ok=True)
        raise
    except (OSError, RuntimeError) as exc:
        path.unlink(missing_ok=True)
        raise ExportError(f"Could not build the preview: {exc}") from exc
    return RenderResult(path, mixer.warnings)
