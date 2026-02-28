# Agent Instructions for Open Video Transcribe

This document provides guidance for AI agents working on the Open Video Transcribe project.

## Project Overview

Open Video Transcribe is a Python-based video transcription service with GUI that supports:
- Multiple model types (Whisper via faster-whisper, extensible to HuggingFace ASR)
- FFmpeg video-to-audio conversion
- GPU acceleration (CUDA)
- Automatic venv setup
- Multiple output formats (TXT with optional timestamps, SRT, VTT)
- Real-time progress tracking for conversion and transcription
- Drag-and-drop file support
- Test mode (5-minute limit for quick testing)
- Comprehensive logging

## Architecture Principles

### 1. Video-First Design
- **Primary workflow**: Video file → Audio extraction → Transcription → Text output
- Video files are the main input type
- Audio extraction happens automatically via FFmpeg
- Audio files are saved alongside original video files

### 2. Adapter Pattern for Models
- All transcription models use the `TranscriptionAdapter` interface (`core/models/base.py`)
- New model types can be added by:
  1. Creating a new adapter class inheriting from `TranscriptionAdapter`
  2. Implementing required abstract methods
  3. Registering in `ModelRegistry` (`core/models/registry.py`)

### 3. Separation of Concerns
- **GUI Layer** (`gui/`): User interface only, delegates to controller
- **Controller** (`core/controller.py`): Orchestrates workflow, coordinates services
- **Services** (`core/transcription/`, `core/audio/`): Business logic
- **Models** (`core/models/`): Model adapters and registry
- **Config** (`config/`): Configuration management

### 4. Threading Model
- Transcription runs in `QThread` to keep GUI responsive
- Use Qt signals for thread-safe communication
- Always check `isInterruptionRequested()` in long-running operations
- Clean up threads properly in `cleanup()` methods

## Code Style Guidelines

### Python Style
- Use `from __future__ import annotations` for type hints
- Follow PEP 8 naming conventions:
  - Files: `snake_case.py`
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
- Use type hints for function parameters and return values
- Use dataclasses for data structures (`@dataclass`)

### Import Organization
```python
# Standard library
import sys
from pathlib import Path

# Third-party
from PySide6.QtCore import QObject, Signal

# Local
from core.logging_config import get_logger
from core.exceptions import TranscriptionError
```

### Logging
- Always use `get_logger(__name__)` for module-level loggers
- Use appropriate log levels:
  - `DEBUG`: Detailed diagnostic information
  - `INFO`: General informational messages
  - `WARNING`: Warning messages
  - `ERROR`: Error messages
  - `CRITICAL`: Critical errors

### Error Handling
- Use custom exceptions from `core/exceptions.py`
- Log exceptions with `logger.exception()` for full traceback
- Emit error signals for GUI notification
- Always clean up resources in `finally` blocks or `cleanup()` methods

## Key Components

### Configuration Management
- **File**: `config/manager.py`
- **Usage**: `config_manager.get_value("key.subkey", default)`
- **Saving**: `config_manager.set_value("key.subkey", value)`
- **Format**: YAML with nested dictionaries
- **Location**: `config.yaml` in project root

### Logging System
- **File**: `core/logging_config.py`
- **Setup**: Call `setup_logging(level)` at application start
- **Logs**: Stored in `logs/` directory with rotation
- **Format**: Timestamp, logger name, level, message

### Model Adapters
- **Base**: `core/models/base.py` - `TranscriptionAdapter` abstract class
- **Whisper**: `core/models/whisper_adapter.py` - faster-whisper integration
- **Registry**: `core/models/registry.py` - Model discovery and creation

### FFmpeg Integration
- **File**: `core/audio/converter.py`
- **Requirement**: User-provided FFmpeg path (validated on startup)
- **Function**: Converts video files to audio (WAV/MP3)
- **Progress**: Supports progress callbacks for conversion

### Transcription Service
- **File**: `core/transcription/service.py`
- **Threading**: Uses `QThread` for async operations
- **Cancellation**: Supports interruption via `requestInterruption()`
- **Progress**: Emits progress signals for GUI updates

## Adding New Features

### Adding a New Model Type

1. Create adapter class in `core/models/`:
```python
from core.models.base import TranscriptionAdapter, TranscriptionResult

class NewModelAdapter(TranscriptionAdapter):
    def load_model(self, model_name: str, device: str, **kwargs):
        # Implementation
        pass
    
    def transcribe(self, audio_path: str, language: Optional[str] = None, 
                   progress_callback: Optional[callable] = None) -> TranscriptionResult:
        # Implementation
        pass
    
    # ... implement other required methods
```

2. Register in `core/models/registry.py`:
```python
from core.models.new_model_adapter import NewModelAdapter

model_registry.register_adapter("newmodel", NewModelAdapter)
```

3. Update GUI to support new model type (if needed)

### Adding a New Output Format

1. Add format to `config.yaml` options
2. Implement format conversion in `core/controller.py` `_save_transcription()` method
3. Update `gui/settings_dialog.py` format dropdown

### TXT Output Format

TXT format supports optional timestamps:
- **With timestamps**: Each line starts with `MM:SS` format (e.g., `00:30 Text here`)
- **Without timestamps**: Plain text only
- Timestamp inclusion is controlled by `output.include_timestamps` config setting
- Timestamps are derived from Whisper segment start times
- Duplicate consecutive segments are automatically filtered

### Modifying GUI

- **Main Window**: `gui/main_window.py`
  - Supports drag-and-drop via `dragEnterEvent()` and `dropEvent()`
  - Shows transcription mode dialog (Full File vs Test Mode)
  - Connects to controller signals for status/progress updates
- **Progress Dialog**: `gui/progress_dialog.py`
  - Displays real-time progress during conversion and transcription
- **Settings Dialog**: `gui/settings_dialog.py`
  - Contains timestamp toggle checkbox for TXT output
  - Manages all output and language settings
- Always use Qt signals for thread-safe communication
- Connect controller signals to GUI slots

## Testing Considerations

### Manual Testing Checklist
1. FFmpeg path validation
2. Model loading (CPU and CUDA)
3. Video file conversion
4. Audio file transcription
5. Output format generation (TXT, SRT, VTT)
6. Progress tracking
7. Cancellation handling
8. Error handling (invalid files, missing FFmpeg, etc.)

### Common Issues
- **FFmpeg not found**: Check path validation in `FFmpegConverter._validate_ffmpeg()`
- **Model loading fails**: Check internet connection, disk space, model name
- **CUDA errors**: Verify PyTorch CUDA compatibility, fall back to CPU
- **Thread issues**: Ensure proper signal/slot connections, check `isInterruptionRequested()`

## File Structure Reference

```
open-video-transcribe/
├── main.py                 # Entry point, system checks, GUI initialization
├── install.py              # Venv creation, dependency installation
├── requirements.txt        # Python dependencies
├── config.yaml             # User configuration
├── run.bat / run.sh        # Starter scripts
├── setup.bat / setup.sh    # Setup scripts (Python version selection)
│
├── core/
│   ├── controller.py       # Main orchestrator (video → audio → transcription)
│   ├── logging_config.py   # Logging setup
│   ├── exceptions.py       # Custom exceptions
│   │
│   ├── audio/
│   │   └── converter.py   # FFmpeg video-to-audio conversion
│   │
│   ├── models/
│   │   ├── base.py         # TranscriptionAdapter abstract base
│   │   ├── whisper_adapter.py    # Whisper/faster-whisper adapter
│   │   └── registry.py     # Model registry/discovery
│   │
│   └── transcription/
│       ├── service.py      # Transcription service (threading, cancellation)
│       └── progress.py     # Progress tracking utilities
│
├── gui/
│   ├── main_window.py      # Main GUI window (drag-and-drop support)
│   ├── progress_dialog.py  # Progress indicator
│   └── settings_dialog.py  # Settings/configuration UI (timestamp toggle)
│
└── config/
    └── manager.py          # Configuration management (YAML)
```

## Dependencies

### Core Dependencies
- `PySide6>=6.9.0` - GUI framework
- `faster-whisper>=1.1.0` - Whisper model backend
- `torch>=2.0.0` - PyTorch (CPU or CUDA)
- `PyYAML>=6.0` - Configuration file parsing
- `psutil>=5.9.0` - System utilities
- `tqdm>=4.65.0` - Progress bars (if needed)

### External Requirements
- **FFmpeg**: User-provided, validated at runtime
- **Python**: 3.11 or 3.12 (checked by setup scripts)

## Configuration Schema

```yaml
ffmpeg_path: ""              # User-provided FFmpeg executable path
model:
  type: "whisper"            # Model adapter type
  name: "large-v3"            # Model name
  quantization: "float16"     # Quantization type
  device: "cuda"             # Device (cpu/cuda)
languages:
  input: "auto"              # Input language (auto-detect if "auto")
  output: "en"               # Output language (for translation)
ui:
  show_progress: true        # Show progress dialog
  log_level: "INFO"          # Logging level
output:
  format: "txt"              # Output format (txt/srt/vtt)
  save_location: "same_as_input"  # Where to save output
  include_timestamps: true   # Include timestamps in TXT output (MM:SS format)
```

## Important Notes

1. **FFmpeg is user-provided**: Never bundle FFmpeg, always require user to provide path
2. **Video-first workflow**: Primary use case is video files, audio is secondary
3. **Thread safety**: Always use Qt signals for cross-thread communication
4. **Resource cleanup**: Always implement `cleanup()` methods for services
5. **Error handling**: Log errors and notify user via signals/dialogs
6. **Configuration**: Use `config_manager` for all settings, never hardcode
7. **Logging**: Log important operations, especially errors and state changes
8. **ASCII only**: User preference for ASCII-only output (no special characters in logs/UI)
9. **Timestamps**: TXT output timestamps use MM:SS format (00:30, not 0:30)
10. **Duplicate filtering**: Automatically filters consecutive duplicate segments and very short segments
11. **Progress updates**: Always provide progress callbacks for long-running operations
12. **Test mode**: Supports duration limits for testing (5 minutes default)

## Common Patterns

### Creating a Service with Threading
```python
from PySide6.QtCore import QObject, Signal, QThread

class MyService(QObject):
    operation_completed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        self._thread = None
    
    def start_operation(self, data):
        self._thread = _OperationThread(data)
        self._thread.completed.connect(self.operation_completed.emit)
        self._thread.error.connect(self.error_occurred.emit)
        self._thread.start()
    
    def cleanup(self):
        if self._thread and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(5000)
```

### Using Configuration
```python
from config.manager import config_manager

# Get value with default
value = config_manager.get_value("model.name", "base")

# Set value
config_manager.set_value("model.name", "large-v3")

# Nested keys
device = config_manager.get_value("model.device", "cpu")
```

### Logging Best Practices
```python
from core.logging_config import get_logger

logger = get_logger(__name__)

# Info for normal operations
logger.info("Starting transcription")

# Debug for detailed info
logger.debug(f"Model loaded: {model_name}")

# Warning for recoverable issues
logger.warning("FFmpeg path not set, video conversion disabled")

# Error for failures
logger.error("Transcription failed")

# Exception for full traceback
logger.exception("Unexpected error occurred")
```

## When Making Changes

1. **Update this file** if architecture changes
2. **Update README.md** if user-facing features change
3. **Test thoroughly** before committing
4. **Check linting** with `read_lints` tool
5. **Maintain backward compatibility** with config files when possible
6. **Document new features** in both README and this file

## Questions to Ask Before Making Changes

1. Does this change affect the video-first workflow?
2. Does this require FFmpeg or can it work without it?
3. Is this thread-safe (if touching GUI or services)?
4. Does this need configuration (add to config.yaml schema)?
5. Does this need logging?
6. Does this break backward compatibility?
7. Should this be in a separate adapter/service?

## Summarizing Work

### Summarize Workflow

After completing work, always summarize:

1. **List what changed** - Files modified, features added/removed
2. **Note what was verified** - Testing performed, validation steps
3. **Document any known limitations** - Issues, TODOs, follow-ups needed

### Git Workflow Summaries

Generate two COPY-READY summaries for Git workflow:

#### 1. Pull Request Summary (for reviewers)

Format as complete markdown ready to paste into PR description:

```markdown
## What Changed
- [High-level bullet point of change 1]
- [High-level bullet point of change 2]
- [High-level bullet point of change 3]

## Why It Changed
[Brief explanation of intent and benefits]

## Validation Performed
- [Test/validation item 1]
- [Test/validation item 2]
- [Test/validation item 3]

## Risks/Notes
- [Breaking changes, if any]
- [Follow-ups needed, if any]
- [Known limitations, if any]
```

**Example:**
```markdown
## What Changed
- Added Python version selection to setup.bat
- Implemented automatic detection of installed Python versions
- Added validation to ensure Python 3.11 or 3.12 is used

## Why It Changed
Users may have multiple Python versions installed. The setup script now detects
all available versions and allows users to choose, with auto-selection of
compatible versions (3.11/3.12) when available.

## Validation Performed
- Tested Python Launcher detection on Windows
- Verified auto-selection of Python 3.12 and 3.11
- Tested manual selection menu
- Validated custom path input
- Confirmed version validation works correctly

## Risks/Notes
- None - backward compatible change
- Requires Python Launcher (py) for best experience, falls back to PATH check
```

#### 2. Squashed Commit Message (concise)

Format in code block ready to copy/paste directly into Git:

```
Subject line (imperative, max 72 chars)

Short body explaining what and why (wrapped at 72 chars per line).
Optional bullet list of key changes if needed.

- Key change 1
- Key change 2
- Key change 3
```

**Example:**
```
Add Python version selection to setup.bat

Detect installed Python versions using Python Launcher and allow
user to choose which version to use. Auto-selects Python 3.12 or
3.11 if available. Falls back to PATH check if launcher unavailable.

- Use py launcher to detect installed versions
- Auto-select compatible versions (3.11/3.12)
- Interactive menu for manual selection
- Custom path input option
- Version validation before installation
```

**Commit Message Guidelines:**
- **Subject line**: Imperative mood, max 72 characters, no period
- **Body**: Wrap at 72 characters per line
- **Bullets**: Use for key changes if multiple items
- **Be concise**: Focus on what and why, not how (code shows how)

## Recent Changes Summary

### Session: Model Description, Detection, Download and New Models (2026-02)

#### What Changed
- Added centralized model metadata (id, display name, description, rating 1-10, VRAM, languages)
- Fixed distil model repo mapping (distil-whisper-X-ct2 format; fallback to Systran on 401/404)
- Added large-v3-turbo, turbo, distil-large-v3.5 to model list
- Model combo now shows ratings and sorts by quality (best first)
- Added model description label with VRAM hint and cached status
- Implemented Systran fallback when ctranslate2-4you repo fails
- Model load runs in background thread; Download Model button for pre-download
- GPU VRAM detection and display in model description

#### Why It Changed
- Users need clearer model selection (descriptions, ratings)
- distil-large-v3 returned 401 due to wrong repo mapping
- Newer models (turbo, distil-large-v3.5) offer better speed/quality options
- Non-blocking model load and pre-download improve UX

#### Technical Details

**Files Created/Modified:**
- `core/models/model_info.py`: New - metadata table, resolve_repo, is_model_cached, get_gpu_vram_mb
- `core/models/whisper_adapter.py`: Use model_info resolver, Systran fallback on HTTP errors
- `gui/main_window.py`: Model combo from metadata, description label, Load/Download threads
- `core/controller.py`: load_model returns bool for async usage

**Validation Performed:**
- Verified model list and ratings display
- Tested resolve_repo for large-v3, distil-large-v3
- App launches and loads model

**Risks/Notes:**
- distil-large-v3 may still 401 on ctranslate2-4you; Systran fallback kicks in
- Cache check uses huggingface_hub.scan_cache_dir

### Session: Enhanced Transcription Features (2025-01)

#### What Changed
- Added timestamps to TXT output (MM:SS format, e.g., 00:30)
- Implemented drag-and-drop file support in main window
- Added test mode option (transcribe first 5 minutes only)
- Enhanced progress tracking with real-time updates during transcription
- Added configurable timestamp option in Settings (enable/disable)
- Improved duplicate segment filtering to remove repeated text
- Updated timestamp format from M:SS to MM:SS (00:30 instead of 0:30)

#### Why It Changed
- **Timestamps**: Users requested timestamps at the beginning of each line to easily navigate transcriptions
- **Drag-and-Drop**: Improves user experience by allowing quick file selection
- **Test Mode**: Enables quick testing of settings without processing entire files
- **Progress Updates**: Better user feedback during long transcription operations
- **Timestamp Toggle**: Some users prefer plain text without timestamps
- **Duplicate Filtering**: Whisper sometimes generates duplicate segments that need filtering

#### Technical Details

**Files Modified:**
- `core/controller.py`: Added timestamp formatting, test mode support, duplicate filtering
- `gui/main_window.py`: Added drag-and-drop handlers, transcription mode dialog
- `gui/settings_dialog.py`: Added timestamp enable/disable checkbox
- `core/audio/converter.py`: Added duration_limit parameter for test mode
- `core/models/whisper_adapter.py`: Enhanced progress callback with segment-based tracking
- `core/transcription/service.py`: Added progress callback support

**New Configuration Options:**
- `output.include_timestamps` (boolean, default: true) - Enable/disable timestamps in TXT output

**New Features:**
1. **Timestamp Formatting**: `_format_timestamp()` formats seconds as MM:SS (e.g., 00:30, 01:23)
2. **Text Formatting**: `_format_text_with_timestamps()` adds timestamps to each segment line
3. **Duplicate Filtering**: Skips consecutive segments with identical text and very short segments (< 3 chars)
4. **Test Mode**: `transcribe_file()` accepts `test_mode` parameter (limits to 5 minutes)
5. **Drag-and-Drop**: `dragEnterEvent()` and `dropEvent()` handle file drops
6. **Progress Updates**: Whisper adapter tracks segment progress and emits updates

**Validation Performed:**
- Tested timestamp formatting with various durations
- Verified drag-and-drop with multiple file formats
- Tested test mode with video and audio files
- Confirmed progress updates during transcription
- Validated timestamp toggle in Settings
- Tested duplicate filtering with real transcription results

**Risks/Notes:**
- Timestamp format change (M:SS → MM:SS) may affect existing workflows expecting old format
- Test mode creates temporary audio files that should be cleaned up (future enhancement)
- Duplicate filtering may remove legitimate repeated phrases (edge case)
- Progress updates depend on segment iteration, may not be perfectly accurate for all audio lengths

