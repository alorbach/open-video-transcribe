"""Whisper model adapter using faster-whisper."""
from __future__ import annotations

from typing import Optional, List, Dict, Any
import psutil

from faster_whisper import WhisperModel

from core.models.base import TranscriptionAdapter, TranscriptionResult
from core.logging_config import get_logger
from core.exceptions import ModelLoadError
from config.manager import config_manager

logger = get_logger(__name__)


def _make_repo_string(model_name: str, quantization_type: str) -> str:
    """Create repository string for model."""
    if model_name.startswith("distil-whisper"):
        return f"ctranslate2-4you/{model_name}-ct2-{quantization_type}"
    return f"ctranslate2-4you/whisper-{model_name}-ct2-{quantization_type}"


class WhisperAdapter(TranscriptionAdapter):
    """Adapter for faster-whisper models."""
    
    WHISPER_LANGUAGES = [
        "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs", "ca", "cs",
        "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi", "fo", "fr", "gl", "gu",
        "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy", "id", "is", "it", "ja", "jw", "ka",
        "kk", "km", "kn", "ko", "la", "lb", "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml",
        "mn", "mr", "ms", "mt", "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt",
        "ro", "ru", "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw",
        "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi", "yi", "yo",
        "zh", "yue"
    ]
    
    def __init__(self):
        self.model: Optional[WhisperModel] = None
        self.model_name: Optional[str] = None
        self.quantization: Optional[str] = None
        self.device: Optional[str] = None
        self.cpu_threads: Optional[int] = None
    
    def load_model(
        self,
        model_name: str,
        device: str,
        quantization: str = "float16",
        cpu_threads: Optional[int] = None
    ) -> WhisperModel:
        """Load a Whisper model."""
        if cpu_threads is None:
            cpu_threads = psutil.cpu_count(logical=False) or 1
        
        # CPU does not support float16; use float32 (works with float16 model weights)
        compute_type = quantization
        if device == "cpu":
            if quantization in ("float16", "bfloat16"):
                compute_type = "float32"
            elif quantization not in ("float32", "int8", "int8_float32"):
                compute_type = "float32"
        
        repo = _make_repo_string(model_name, quantization)
        logger.info(f"Loading Whisper model {repo} on {device}")
        
        try:
            self.model = WhisperModel(
                repo,
                device=device,
                compute_type=compute_type,
                cpu_threads=cpu_threads,
            )
            self.model_name = model_name
            self.quantization = quantization
            self.device = device
            self.cpu_threads = cpu_threads
            logger.info(f"Model {repo} loaded successfully")
            return self.model
        except Exception as e:
            logger.exception(f"Failed to load model {repo}")
            raise ModelLoadError(f"Error loading model {repo}: {e}") from e
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        word_timestamps: bool = False
    ) -> TranscriptionResult:
        """Transcribe audio file."""
        if not self.model:
            raise ModelLoadError("No model loaded")
        
        logger.info(f"Transcribing {audio_path} with language: {language or 'auto-detect'}, word_timestamps: {word_timestamps}")
        
        try:
            return self._transcribe_impl(
                audio_path, language, progress_callback, word_timestamps
            )
        except RuntimeError as e:
            err_str = str(e).lower()
            if self.device == "cuda" and ("cublas" in err_str or "cuda" in err_str or "cudnn" in err_str):
                logger.warning(
                    "CUDA failed (%s), falling back to CPU. "
                    "For GPU: Settings > Install CUDA Runtime (nvidia-cublas-cu12, nvidia-cudnn-cu12), then restart.",
                    e,
                )
                config_manager.set_value("model.device", "cpu")
                cpu_quant = "float32" if self.quantization == "float16" else self.quantization
                self.load_model(
                    self.model_name,
                    "cpu",
                    quantization=cpu_quant,
                    cpu_threads=self.cpu_threads,
                )
                return self._transcribe_impl(
                    audio_path, language, progress_callback, word_timestamps
                )
            raise
        except Exception:
            logger.exception("Transcription failed")
            raise

    def _transcribe_impl(
        self,
        audio_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        word_timestamps: bool = False,
    ) -> TranscriptionResult:
        """Internal transcription implementation."""
        segments, info = self.model.transcribe(
            audio_path,
            language=language if language and language != "auto" else None,
            beam_size=5,
            word_timestamps=word_timestamps
        )
        
        # Get duration from info if available
        total_duration = None
        if info and hasattr(info, 'duration'):
            total_duration = info.duration
        elif info and hasattr(info, 'language'):
            pass
        
        segments_list = []
        segment_count = 0
        last_progress_update = 0.0
        max_seen_time = 0.0
        
        for segment in segments:
            segments_list.append(segment)
            segment_count += 1
            
            if segment.end:
                max_seen_time = max(max_seen_time, segment.end)
            
            if progress_callback and (segment_count % 5 == 0 or (segment.end and segment.end - last_progress_update > 5.0)):
                if total_duration and segment.end:
                    progress = min(segment.end / total_duration, 0.99)
                    progress_callback(progress, f"Transcribing... {int(progress * 100)}%")
                    last_progress_update = segment.end
                elif max_seen_time > 0:
                    estimated_total = max_seen_time * 1.1
                    progress = min(max_seen_time / estimated_total, 0.95)
                    progress_callback(progress, f"Transcribing... {int(progress * 100)}%")
                else:
                    estimated_progress = min(0.3 + (segment_count * 0.005), 0.90)
                    progress_callback(estimated_progress, f"Processing segments... {segment_count}")
        
        if progress_callback:
            progress_callback(1.0, "Transcription complete")
        
        logger.info(f"Transcription completed, got {len(segments_list)} segments")
        
        segment_dicts = []
        text_parts = []
        
        for segment in segments_list:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            }
            if word_timestamps and segment.words:
                segment_dict["words"] = [
                    {"start": w.start, "end": w.end, "word": w.word}
                    for w in segment.words
                ]
            segment_dicts.append(segment_dict)
            text_parts.append(segment.text)
        
        text = "\n".join(text_parts)
        detected_lang = getattr(info, 'language', None) if info else None
        lang_prob = getattr(info, 'language_probability', None) if info else None
        if info:
            logger.info(f"Detected language: {detected_lang}, probability: {lang_prob}")
        
        return TranscriptionResult(
            text=text,
            segments=segment_dicts,
            language=detected_lang,
            language_probability=lang_prob
        )
    
    def supports_language(self, language_code: str) -> bool:
        """Check if language is supported."""
        return language_code.lower() in [lang.lower() for lang in self.WHISPER_LANGUAGES]
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self.WHISPER_LANGUAGES.copy()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "type": "whisper",
            "name": self.model_name,
            "quantization": self.quantization,
            "device": self.device,
            "cpu_threads": self.cpu_threads,
            "loaded": self.model is not None
        }

