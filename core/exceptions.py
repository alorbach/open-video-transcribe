"""Custom exceptions for Open Video Transcribe."""
from __future__ import annotations


class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class ModelLoadError(TranscriptionError):
    """Exception raised when model loading fails."""
    pass


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class AudioConversionError(TranscriptionError):
    """Exception raised when audio conversion fails."""
    pass


class FFmpegError(AudioConversionError):
    """Exception raised when FFmpeg operations fail."""
    pass

