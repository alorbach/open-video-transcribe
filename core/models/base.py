"""Base model adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    text: str
    segments: List[Dict[str, Any]]
    language: Optional[str] = None
    language_probability: Optional[float] = None


class TranscriptionAdapter(ABC):
    """Abstract base class for transcription model adapters."""
    
    @abstractmethod
    def load_model(self, model_name: str, device: str, **kwargs) -> Any:
        """Load the transcription model.
        
        Args:
            model_name: Name of the model to load
            device: Device to use ('cpu' or 'cuda')
            **kwargs: Additional model-specific parameters
            
        Returns:
            Loaded model object
        """
        pass
    
    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> TranscriptionResult:
        """Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            language: Language code (None for auto-detect)
            progress_callback: Optional callback for progress updates
            
        Returns:
            TranscriptionResult object
        """
        pass
    
    @abstractmethod
    def supports_language(self, language_code: str) -> bool:
        """Check if the model supports a specific language.
        
        Args:
            language_code: ISO 639-1 language code
            
        Returns:
            True if language is supported
        """
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes.
        
        Returns:
            List of ISO 639-1 language codes
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model.
        
        Returns:
            Dictionary with model metadata
        """
        pass

