"""Main controller/orchestrator for Open Video Transcribe."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

from config.manager import config_manager
from core.models.registry import model_registry
from core.models.base import TranscriptionAdapter, TranscriptionResult
from core.audio.converter import FFmpegConverter
from core.transcription.service import TranscriptionService
from core.transcription.progress import ProgressInfo
from core.logging_config import get_logger
from core.exceptions import FFmpegError, TranscriptionError

logger = get_logger(__name__)


class Controller(QObject):
    """Main controller for video transcription workflow."""
    
    status_updated = Signal(str)
    progress_updated = Signal(float, str)
    transcription_completed = Signal(str, Path)
    error_occurred = Signal(str, str)
    widgets_enabled = Signal(bool)

    def __init__(self, cuda_available: bool = False):
        super().__init__()
        
        self.cuda_available = cuda_available
        self.ffmpeg_path: Optional[str] = None
        self.converter: Optional[FFmpegConverter] = None
        self.adapter: Optional[TranscriptionAdapter] = None
        self.transcription_service = TranscriptionService()
        
        self.current_language: Optional[str] = None
        self.current_model_type: Optional[str] = None
        self.current_model_name: Optional[str] = None
        self.current_input_file: Optional[Path] = None
        self._lyrics_mode: bool = False
        
        self._connect_signals()
        self._load_settings()
        
        logger.info("Controller initialized")
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.transcription_service.transcription_started.connect(
            lambda: self.status_updated.emit("Transcribing...")
        )
        self.transcription_service.transcription_completed.connect(self._on_transcription_completed)
        self.transcription_service.transcription_error.connect(self._on_transcription_error)
        self.transcription_service.progress_updated.connect(self._on_progress_updated)
    
    def _load_settings(self) -> None:
        """Load settings from config."""
        ffmpeg_path = config_manager.get_value("ffmpeg_path", "")
        if ffmpeg_path:
            try:
                self.set_ffmpeg_path(ffmpeg_path)
            except Exception as e:
                logger.warning(f"Failed to set FFmpeg path: {e}")
        
        model_type = config_manager.get_value("model.type", "whisper")
        model_name = config_manager.get_value("model.name", "large-v3")
        quantization = config_manager.get_value("model.quantization", "float16")
        device = config_manager.get_value("model.device", "cuda")
        # Auto-enable CUDA at startup when GPU is available
        if self.cuda_available and device == "cpu":
            device = "cuda"
            config_manager.set_value("model.device", "cuda")
        
        self.current_language = config_manager.get_value("languages.input", "auto")
        if self.current_language == "auto":
            self.current_language = None
        
        try:
            self.load_model(model_type, model_name, quantization, device)
        except Exception as e:
            logger.warning(f"Failed to load model from config: {e}")
    
    def set_ffmpeg_path(self, path: str) -> None:
        """Set FFmpeg path and validate."""
        try:
            self.converter = FFmpegConverter(path)
            self.ffmpeg_path = path
            config_manager.set_value("ffmpeg_path", path)
            logger.info(f"FFmpeg path set: {path}")
            self.status_updated.emit("FFmpeg ready")
        except FFmpegError as e:
            logger.error(f"FFmpeg error: {e}")
            raise
    
    def load_model(
        self,
        model_type: str,
        model_name: str,
        quantization: str,
        device: str
    ) -> bool:
        """Load a transcription model. Returns True on success, False on failure."""
        self.widgets_enabled.emit(False)
        self.status_updated.emit(f"Loading model {model_name}...")
        
        try:
            adapter = model_registry.create_adapter(model_type)
            if not adapter:
                raise TranscriptionError(f"Unknown model type: {model_type}")
            
            adapter.load_model(model_name, device, quantization=quantization)
            
            self.adapter = adapter
            self.current_model_type = model_type
            self.current_model_name = model_name
            
            config_manager.set_value("model.type", model_type)
            config_manager.set_value("model.name", model_name)
            config_manager.set_value("model.quantization", quantization)
            config_manager.set_value("model.device", device)
            
            logger.info(f"Model loaded: {model_name} on {device}")
            self.status_updated.emit(f"Model {model_name} ready")
            self.widgets_enabled.emit(True)
            return True
            
        except Exception as e:
            logger.exception("Failed to load model")
            self.status_updated.emit("Model load failed")
            self.widgets_enabled.emit(True)
            self.error_occurred.emit("Model Error", f"Failed to load model: {e}")
            return False
    
    def transcribe_file(
        self,
        file_path: Path,
        test_mode: bool = False,
        lyrics_mode: bool = False
    ) -> None:
        """Transcribe a video or audio file.
        
        Args:
            file_path: Path to video or audio file
            test_mode: If True, only transcribe first 5 minutes (300 seconds)
            lyrics_mode: If True, use word-level timestamps and output lyrics format
        """
        if not self.adapter:
            self.error_occurred.emit("Error", "No model loaded")
            return
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.error_occurred.emit("Error", f"File not found: {file_path}")
            return
        
        self.widgets_enabled.emit(False)
        
        # Store original input file path and mode for saving output
        self.current_input_file = file_path
        self._lyrics_mode = lyrics_mode
        
        try:
            audio_path = self._prepare_audio(file_path, test_mode=test_mode)
            self._start_transcription(audio_path, lyrics_mode=lyrics_mode)
        except Exception as e:
            logger.exception("Transcription failed")
            self.status_updated.emit("Transcription failed")
            self.widgets_enabled.emit(True)
            self.error_occurred.emit("Error", str(e))
            self.current_input_file = None
            self._lyrics_mode = False
    
    def _prepare_audio(self, file_path: Path, test_mode: bool = False) -> Path:
        """Prepare audio file from video or return existing audio.
        
        Args:
            file_path: Path to video or audio file
            test_mode: If True, limit to first 5 minutes (300 seconds)
        """
        if not self.converter:
            raise FFmpegError("FFmpeg not configured")
        
        duration_limit = 300.0 if test_mode else None  # 5 minutes for test mode
        
        if self.converter.is_audio_file(file_path):
            if test_mode:
                # For audio files in test mode, we need to create a trimmed version
                logger.info(f"Creating test version (5 min) of audio file: {file_path}")
                self.status_updated.emit("Preparing test audio (5 minutes)...")
                
                # Create a temporary output path
                audio_path = file_path.parent / f"{file_path.stem}_test{file_path.suffix}"
                
                def progress_callback(progress: float):
                    self.progress_updated.emit(progress * 0.3, f"Preparing test audio... {int(progress * 100)}%")
                
                # Use FFmpeg to extract first 5 minutes
                audio_path = self.converter.convert_video_to_audio(
                    file_path,
                    output_path=audio_path,
                    progress_callback=progress_callback,
                    duration_limit=duration_limit
                )
                return audio_path
            else:
                logger.info(f"File is already audio: {file_path}")
                return file_path
        
        if self.converter.is_video_file(file_path):
            mode_text = "test (5 min)" if test_mode else "full"
            logger.info(f"Converting video to audio ({mode_text}): {file_path}")
            self.status_updated.emit(f"Converting video to audio ({mode_text})...")
            
            def progress_callback(progress: float):
                self.progress_updated.emit(progress * 0.3, f"Converting... {int(progress * 100)}%")
            
            audio_path = self.converter.convert_video_to_audio(
                file_path,
                progress_callback=progress_callback,
                duration_limit=duration_limit
            )
            return audio_path
        
        raise TranscriptionError(f"Unsupported file format: {file_path.suffix}")
    
    def _start_transcription(self, audio_path: Path, lyrics_mode: bool = False) -> None:
        """Start transcription of audio file."""
        logger.info(f"Starting transcription: {audio_path} (lyrics_mode={lyrics_mode})")
        self.transcription_service.transcribe_file(
            self.adapter,
            audio_path,
            language=self.current_language,
            word_timestamps=lyrics_mode
        )
    
    @Slot(object)
    def _on_transcription_completed(self, result: TranscriptionResult) -> None:
        """Handle transcription completion."""
        logger.info(f"Transcription completed: {len(result.text)} characters")
        
        if self._lyrics_mode:
            output_format = "lyrics"
        else:
            output_format = config_manager.get_value("output.format", "txt")
        save_location = config_manager.get_value("output.save_location", "same_as_input")
        
        output_path = self._save_transcription(result, output_format, save_location)
        
        self.transcription_completed.emit(result.text, output_path)
        self.status_updated.emit("Done")
        self.widgets_enabled.emit(True)
        self.current_input_file = None  # Clear after saving
        self._lyrics_mode = False
    
    def _save_transcription(self, result: TranscriptionResult, format: str, save_location: str) -> Path:
        """Save transcription to file."""
        if save_location == "same_as_input":
            # Use the same directory as the input file
            if self.current_input_file:
                base_path = self.current_input_file.parent
                # Use the same basename as input file
                base_name = self.current_input_file.stem
                output_path = base_path / f"{base_name}.{format}"
            else:
                # Fallback to current directory if no input file tracked
                base_path = Path.cwd()
                output_path = base_path / f"transcription.{format}"
        else:
            base_path = Path(save_location)
            if self.current_input_file:
                base_name = self.current_input_file.stem
                output_path = base_path / f"{base_name}.{format}"
            else:
                output_path = base_path / f"transcription.{format}"
        
        if format == "txt":
            # Check if timestamps should be included
            include_timestamps = config_manager.get_value("output.include_timestamps", True)
            if include_timestamps:
                formatted_text = self._format_text_with_timestamps(result)
            else:
                formatted_text = result.text
            output_path.write_text(formatted_text, encoding="utf-8")
        elif format == "lyrics":
            formatted_text = self._format_lyrics(result)
            output_path.write_text(formatted_text, encoding="utf-8")
        elif format == "srt":
            output_path.write_text(self._text_to_srt(result.text), encoding="utf-8")
        elif format == "vtt":
            output_path.write_text(self._text_to_vtt(result.text), encoding="utf-8")
        else:
            output_path.write_text(result.text, encoding="utf-8")
        
        logger.info(f"Transcription saved to: {output_path}")
        return output_path
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as timestamp string (e.g., 00:00, 00:35, 01:23)."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _format_timestamp_lyrics(self, seconds: float) -> str:
        """Format seconds as lyrics timestamp (e.g., 0:04.400, 1:00.400)."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{minutes}:{secs:02d}.{millis:03d}"
    
    def _format_lyrics(self, result: TranscriptionResult) -> str:
        """Format transcription as lyrics with START=END=TEXT per line."""
        if not result.segments:
            return ""
        
        lines = []
        for segment in result.segments:
            words = segment.get("words")
            if words:
                for word in words:
                    start = word.get("start", segment.get("start", 0.0))
                    end = word.get("end", segment.get("end", 0.0))
                    text = word.get("word", "").strip()
                    start_str = self._format_timestamp_lyrics(start)
                    end_str = self._format_timestamp_lyrics(end)
                    lines.append(f"{start_str}={end_str}={text}")
            else:
                # Fallback: use segment-level timing
                start = segment.get("start", 0.0)
                end = segment.get("end", 0.0)
                text = segment.get("text", "").strip()
                start_str = self._format_timestamp_lyrics(start)
                end_str = self._format_timestamp_lyrics(end)
                lines.append(f"{start_str}={end_str}={text}")
        
        return "\n".join(lines)
    
    def _format_text_with_timestamps(self, result: TranscriptionResult) -> str:
        """Format transcription text with timestamps at the beginning of each line."""
        if not result.segments:
            # Fallback to plain text if no segments available
            return result.text
        
        lines = []
        last_text = None
        last_timestamp = None
        
        for segment in result.segments:
            start_time = segment.get("start", 0.0)
            text = segment.get("text", "").strip()
            
            if not text:
                continue
            
            # Skip duplicate consecutive segments with identical text
            if text == last_text:
                continue
            
            # Skip very short segments that are likely artifacts
            if len(text) < 3:
                continue
            
            timestamp = self._format_timestamp(start_time)
            lines.append(f"{timestamp} {text}")
            last_text = text
            last_timestamp = timestamp
        
        return "\n".join(lines)
    
    def _text_to_srt(self, text: str) -> str:
        """Convert plain text to SRT format (simplified)."""
        lines = text.strip().split("\n")
        srt = []
        for i, line in enumerate(lines, 1):
            if line.strip():
                srt.append(f"{i}\n00:00:00,000 --> 00:00:00,000\n{line}\n")
        return "\n".join(srt)
    
    def _text_to_vtt(self, text: str) -> str:
        """Convert plain text to VTT format (simplified)."""
        lines = text.strip().split("\n")
        vtt = ["WEBVTT", ""]
        for line in lines:
            if line.strip():
                vtt.append(f"00:00:00.000 --> 00:00:00.000\n{line}\n")
        return "\n".join(vtt)
    
    @Slot(str)
    def _on_transcription_error(self, error: str) -> None:
        """Handle transcription error."""
        logger.error(f"Transcription error: {error}")
        self.status_updated.emit("Transcription failed")
        self.widgets_enabled.emit(True)
        self.error_occurred.emit("Transcription Error", error)
    
    @Slot(float, str)
    def _on_progress_updated(self, progress: float, message: str) -> None:
        """Handle progress update."""
        self.progress_updated.emit(0.3 + progress * 0.7, message)
    
    def set_language(self, language: Optional[str]) -> None:
        """Set transcription language."""
        if language == "auto" or language is None:
            self.current_language = None
        else:
            self.current_language = language
        
        config_manager.set_value("languages.input", language or "auto")
        logger.info(f"Language set to: {self.current_language or 'auto-detect'}")
    
    def cancel(self) -> None:
        """Cancel current operation."""
        self.transcription_service.cancel()
        self.status_updated.emit("Cancelled")
        self.widgets_enabled.emit(True)
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.transcription_service.cleanup()
        logger.info("Controller cleanup complete")

