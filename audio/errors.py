"""Errors whose messages are written for humans and safe to show in a dialog."""
from __future__ import annotations


class StudioError(Exception):
    """Base class: the message can be shown directly to the user."""


class FFmpegMissingError(StudioError):
    pass


class InvalidAudioError(StudioError):
    pass


class EmptyMixError(StudioError):
    pass


class DiskSpaceError(StudioError):
    pass


class ExportError(StudioError):
    pass


class Cancelled(Exception):
    """Raised inside a render when the user presses Cancel."""
