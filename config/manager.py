"""Configuration management for Open Video Transcribe."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from core.logging_config import get_logger
from core.exceptions import ConfigurationError

logger = get_logger(__name__)


class ConfigManager:
    """Manages application configuration."""
    
    DEFAULT_CONFIG = {
        "ffmpeg_path": "",
        "model": {
            "type": "whisper",
            "name": "large-v3",
            "quantization": "float16",
            "device": "cuda"
        },
        "languages": {
            "input": "auto",
            "output": "en"
        },
        "ui": {
            "show_progress": True,
            "log_level": "INFO"
        },
        "output": {
            "format": "txt",
            "save_location": "same_as_input"
        }
    }
    
    def __init__(self):
        self._config_path = Path("config.yaml")
        self._config_cache: Optional[Dict[str, Any]] = None
    
    @property
    def config_path(self) -> Path:
        """Get the configuration file path."""
        return self._config_path
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self._config_cache is None:
            self._config_cache = self._load_from_file()
        return self._config_cache.copy()
    
    def _load_from_file(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            if self._config_path.exists():
                with self._config_path.open() as f:
                    config = yaml.safe_load(f) or {}
            else:
                logger.info("Config file not found, using defaults")
                config = {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing config file: {e}")
            config = {}
        except Exception as e:
            logger.error(f"Unexpected error loading config: {e}")
            config = {}
        
        merged_config = self.DEFAULT_CONFIG.copy()
        self._deep_update(merged_config, config)
        return merged_config
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._config_path.open("w") as f:
                yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)
            
            self._config_cache = config.copy()
            logger.debug("Configuration saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}") from e
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        config = self.load_config()
        self._deep_update(config, updates)
        self.save_config(config)
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key (supports dot notation)."""
        config = self.load_config()
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value if value is not None else default
    
    def set_value(self, key: str, value: Any) -> None:
        """Set a configuration value by key (supports dot notation)."""
        config = self.load_config()
        keys = key.split(".")
        target = config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value
        self.save_config(config)
    
    def invalidate_cache(self) -> None:
        """Invalidate the configuration cache."""
        self._config_cache = None
    
    @staticmethod
    def _deep_update(base_dict: Dict[str, Any], update_dict: Dict[str, Any]) -> None:
        """Recursively update a dictionary."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                ConfigManager._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value


config_manager = ConfigManager()

