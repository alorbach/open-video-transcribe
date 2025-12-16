"""Model registry for discovering and managing transcription models."""
from __future__ import annotations

from typing import Dict, List, Optional, Type
from core.models.base import TranscriptionAdapter
from core.models.whisper_adapter import WhisperAdapter
from core.logging_config import get_logger

logger = get_logger(__name__)


class ModelRegistry:
    """Registry for transcription model adapters."""
    
    def __init__(self):
        self._adapters: Dict[str, Type[TranscriptionAdapter]] = {}
        self._register_default_adapters()
    
    def _register_default_adapters(self) -> None:
        """Register default model adapters."""
        self.register_adapter("whisper", WhisperAdapter)
        logger.info("Registered default adapters")
    
    def register_adapter(self, model_type: str, adapter_class: Type[TranscriptionAdapter]) -> None:
        """Register a model adapter.
        
        Args:
            model_type: Type identifier (e.g., 'whisper', 'huggingface')
            adapter_class: Adapter class to register
        """
        self._adapters[model_type] = adapter_class
        logger.info(f"Registered adapter: {model_type}")
    
    def get_adapter(self, model_type: str) -> Optional[Type[TranscriptionAdapter]]:
        """Get an adapter class by type.
        
        Args:
            model_type: Type identifier
            
        Returns:
            Adapter class or None if not found
        """
        return self._adapters.get(model_type)
    
    def create_adapter(self, model_type: str) -> Optional[TranscriptionAdapter]:
        """Create an adapter instance.
        
        Args:
            model_type: Type identifier
            
        Returns:
            Adapter instance or None if not found
        """
        adapter_class = self.get_adapter(model_type)
        if adapter_class:
            return adapter_class()
        return None
    
    def get_available_types(self) -> List[str]:
        """Get list of available model types.
        
        Returns:
            List of model type identifiers
        """
        return list(self._adapters.keys())
    
    def is_registered(self, model_type: str) -> bool:
        """Check if a model type is registered.
        
        Args:
            model_type: Type identifier
            
        Returns:
            True if registered
        """
        return model_type in self._adapters


model_registry = ModelRegistry()

