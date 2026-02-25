"""Transcription service with cancellation support."""
from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QThread

from core.models.base import TranscriptionAdapter, TranscriptionResult
from core.logging_config import get_logger
from core.exceptions import TranscriptionError

logger = get_logger(__name__)


class _TranscriptionThread(QThread):
    """Thread for running transcription."""
    transcription_done = Signal(object)
    error_occurred = Signal(str)
    progress_updated = Signal(float, str)

    def __init__(
        self,
        adapter: TranscriptionAdapter,
        audio_file: Path,
        language: Optional[str] = None,
        word_timestamps: bool = False
    ) -> None:
        super().__init__()
        self.adapter = adapter
        self.audio_file = Path(audio_file)
        self.language = language
        self.word_timestamps = word_timestamps

    def run(self) -> None:
        """Run transcription in thread."""
        try:
            if self.isInterruptionRequested():
                return
            
            logger.info(f"Starting transcription: {self.audio_file} (language: {self.language or 'auto-detect'})")
            
            # Create progress callback that emits signals
            def progress_callback(progress: float, message: str = ""):
                if not self.isInterruptionRequested():
                    self.progress_updated.emit(progress, message or f"Transcribing... {int(progress * 100)}%")
            
            result = self.adapter.transcribe(
                str(self.audio_file),
                language=self.language,
                progress_callback=progress_callback,
                word_timestamps=self.word_timestamps
            )
            
            if self.isInterruptionRequested():
                return
            
            if self.isInterruptionRequested():
                return
            
            logger.info(f"Transcription completed: {len(result.text)} characters")
            self.transcription_done.emit(result)
            
        except Exception as e:
            logger.exception("Transcription failed")
            self.error_occurred.emit(f"Transcription failed: {e}")


class TranscriptionService(QObject):
    """Service for managing transcription operations."""
    
    transcription_started = Signal()
    transcription_completed = Signal(object)
    transcription_error = Signal(str)
    progress_updated = Signal(float, str)

    def __init__(self):
        super().__init__()
        self.language: Optional[str] = None
        self._transcription_thread: Optional[_TranscriptionThread] = None

    def transcribe_file(
        self,
        adapter: TranscriptionAdapter,
        audio_file: Path,
        language: Optional[str] = None,
        word_timestamps: bool = False
    ) -> None:
        """Start transcription of an audio file.
        
        Args:
            adapter: Model adapter to use
            audio_file: Path to audio file
            language: Language code (None for auto-detect)
            word_timestamps: If True, request word-level timestamps from adapter
        """
        if not adapter:
            error_msg = "No model adapter available for transcription"
            logger.error(error_msg)
            self.transcription_error.emit(error_msg)
            return

        transcription_language = language if language is not None else self.language
        logger.info(f"Transcription language: {transcription_language or 'auto-detect'}")

        try:
            self._transcription_thread = _TranscriptionThread(
                adapter,
                audio_file,
                transcription_language,
                word_timestamps=word_timestamps
            )
            self._transcription_thread.transcription_done.connect(self._on_transcription_done)
            self._transcription_thread.error_occurred.connect(self._on_transcription_error)
            self._transcription_thread.progress_updated.connect(self._on_progress_updated)
            self._transcription_thread.start()
            self.transcription_started.emit()
        except Exception as e:
            logger.exception("Failed to start transcription thread")
            self.transcription_error.emit(f"Failed to start transcription: {e}")

    def _on_transcription_done(self, result: TranscriptionResult) -> None:
        """Handle transcription completion."""
        logger.info(f"Transcription completed: {len(result.text)} characters")
        self.transcription_completed.emit(result)

    def _on_transcription_error(self, error: str) -> None:
        """Handle transcription error."""
        logger.error(f"Transcription error: {error}")
        self.transcription_error.emit(error)

    def _on_progress_updated(self, progress: float, message: str) -> None:
        """Handle progress update."""
        self.progress_updated.emit(progress, message)

    def set_language(self, language: Optional[str]) -> None:
        """Set the language for transcription."""
        self.language = language if language and language != "auto" else None
        logger.info(f"TranscriptionService language set to: {self.language or 'auto-detect'}")

    def cancel(self) -> None:
        """Cancel current transcription."""
        if self._transcription_thread and self._transcription_thread.isRunning():
            logger.info("Cancelling transcription")
            self._transcription_thread.requestInterruption()
            self._transcription_thread.wait(5000)
            if self._transcription_thread.isRunning():
                logger.warning("Transcription thread did not stop in time")
                self._transcription_thread.terminate()

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.cancel()
        logger.debug("TranscriptionService cleanup complete")

