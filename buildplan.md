---
name: Open Video Transcribe
overview: "Create a new clean Python-based video transcription service with GUI that supports multiple model types (Whisper and HuggingFace ASR), ffmpeg video-to-audio conversion, GPU acceleration, automatic venv setup, and comprehensive logging. Primary focus: transcribing video files to text."
todos: []
---

# Open Video Transcribe - Implementation Plan

## Project Name

**Open Video Transcribe** - Open-source video transcription tool that emphasizes the primary use case: transcribing video files to text with support for multiple model types.

## Primary Use Case

**Video Transcription Workflow:**

1. User selects a video file (mp4, avi, mkv, webm, etc.)
2. Tool uses user-provided ffmpeg path to extract audio
3. Audio file is automatically saved alongside the video
4. Selected transcription model processes the audio
5. Transcription result is saved in chosen format (txt, srt, vtt)
6. User can also record audio directly or process existing audio files

**Key Focus**: Video files are the primary input, with audio extraction as an automatic first step.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      GUI Layer (PySide6)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Main Window  │  │ Progress UI  │  │ Settings UI  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼─────────────┘
          │                 │                 │
┌─────────┼─────────────────┼─────────────────┼─────────────┐
│         │                 │                 │              │
│  ┌──────▼──────────┐  ┌──▼──────────┐  ┌──▼──────────┐   │
│  │ Controller      │  │ Audio      │  │ Model       │   │
│  │ (Orchestrator)  │  │ Processor  │  │ Registry    │   │
│  └──────┬──────────┘  └──┬──────────┘  └──┬──────────┘   │
│         │                 │                 │              │
│  ┌──────▼─────────────────▼─────────────────▼──────────┐   │
│  │         Transcription Service (Abstract)           │   │
│  │  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │ Whisper      │  │ HuggingFace  │               │   │
│  │  │ Adapter      │  │ Adapter      │               │   │
│  │  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ FFmpeg       │  │ Logging      │  │ Config       │   │
│  │ Converter    │  │ System       │  │ Manager      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Project Structure

```
open-video-transcribe/
├── main.py                 # Entry point
├── install.py              # Auto venv creation & dependency installer
├── requirements.txt        # Python dependencies
├── config.yaml             # User configuration
├── run.bat / run.sh        # Starter scripts (auto-generated)
├── setup.bat / setup.sh    # Setup scripts (auto-generated)
│
├── core/
│   ├── __init__.py
│   ├── controller.py       # Main orchestrator
│   ├── logging_config.py   # Logging setup (similar to current)
│   ├── exceptions.py       # Custom exceptions
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── manager.py      # Audio recording management
│   │   ├── recording.py    # Recording thread
│   │   └── converter.py    # FFmpeg video-to-audio conversion
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── registry.py     # Model registry/discovery
│   │   ├── base.py         # Abstract base class for models
│   │   ├── whisper_adapter.py    # Whisper model adapter
│   │   └── huggingface_adapter.py # HuggingFace model adapter
│   │
│   ├── transcription/
│   │   ├── __init__.py
│   │   ├── service.py      # Transcription service (refactored)
│   │   └── progress.py     # Progress tracking
│   │
│   └── utils/
│       ├── __init__.py
│       ├── venv_manager.py # Venv creation/management
│       └── file_manager.py # File operations
│
├── gui/
│   ├── __init__.py
│   ├── main_window.py      # Main GUI window
│   ├── progress_dialog.py  # Progress indicator
│   ├── settings_dialog.py  # Settings/configuration UI
│   └── widgets.py          # Reusable widgets
│
└── config/
    ├── __init__.py
    └── manager.py          # Configuration management
```

### 2. Core Features Implementation

#### 2.1 Model Registry System

- **Location**: `core/models/registry.py`
- **Purpose**: Discover and register available transcription models
- **Features**:
  - Auto-detect Whisper models (faster-whisper compatible)
  - Auto-detect HuggingFace ASR models
  - Plugin system for custom model adapters
  - Model metadata (languages, capabilities, GPU support)

#### 2.2 FFmpeg Integration (Core Feature)

- **Location**: `core/audio/converter.py`
- **Purpose**: Convert video files to audio using user-provided ffmpeg path (PRIMARY WORKFLOW)
- **Features**:
  - Validate ffmpeg path on startup (required for video processing)
  - Convert video → audio (WAV/MP3) - this is the main entry point
  - Store audio file alongside original video automatically
  - Support common video formats (mp4, avi, mkv, webm, mov, etc.)
  - Progress callback for conversion
  - Preserve video metadata where possible
  - Handle video codec variations

#### 2.3 Language Selection

- **Input Language**: Language of source audio (auto-detect or manual)
- **Output Language**: Target language for translation (if supported)
- **Implementation**: 
  - Language dropdown in GUI (similar to current)
  - Pass to model adapters
  - Store in config

#### 2.4 GPU Support

- **Location**: `core/models/base.py` and adapters
- **Features**:
  - Auto-detect CUDA availability
  - Device selection (CPU/CUDA)
  - Quantization options per device
  - Similar to current project's GPU handling

#### 2.5 Progress Tracking

- **Location**: `core/transcription/progress.py`
- **Features**:
  - Progress callbacks from models
  - Progress bar in GUI
  - Estimated time remaining
  - Segment-by-segment progress (if available)

#### 2.6 Cancellation Support

- **Location**: Throughout transcription service
- **Features**:
  - Cancel button in GUI
  - Thread interruption handling
  - Clean resource cleanup
  - Signal-based cancellation

#### 2.7 Logging System

- **Location**: `core/logging_config.py`
- **Features**:
  - Rotating file logs (like current project)
  - Debug/Info/Warning/Error levels
  - Console + file output
  - Timestamped log files

### 3. Auto-Venv Setup

#### 3.1 Venv Manager

- **Location**: `core/utils/venv_manager.py`
- **Features**:
  - Check Python version (3.11 or 3.12)
  - Create venv if doesn't exist
  - Validate venv activation
  - Cross-platform (Windows/Linux/macOS)

#### 3.2 Install Script

- **Location**: `install.py`
- **Features**:
  - Detect Python version
  - Create venv
  - Install requirements
  - Detect GPU and install appropriate PyTorch
  - Similar to current `install.py` but cleaner

#### 3.3 Starter Scripts

- **Files**: `run.bat`, `run.sh`, `setup.bat`, `setup.sh`
- **Auto-generation**: Created by install script
- **Features**:
  - Activate venv
  - Run main.py
  - Handle errors gracefully
  - Platform-specific (Windows batch, Unix shell)

### 4. GUI Enhancements

#### 4.1 Main Window

- **Primary**: Video file selection (main workflow)
- Model selection (dropdown with registry)
- Input/Output language selection
- FFmpeg path configuration (required for video processing)
- File selection (video files prioritized, audio files supported)
- Record button (optional - for direct audio recording)
- Progress indicator (shows: video conversion → transcription)
- Cancel button
- Settings button
- Output format selection (txt, srt, vtt for subtitles)

#### 4.2 Progress Dialog

- Progress bar
- Status text
- Cancel button
- Estimated time
- Segment information (if available)

#### 4.3 Settings Dialog

- FFmpeg path
- Default languages
- GPU settings
- Log level
- Output format preferences

### 5. Configuration Management

#### 5.1 Config File Structure

```yaml
# config.yaml
ffmpeg_path: ""  # User-provided path
model:
  type: "whisper"  # or "huggingface"
  name: "large-v3"
  quantization: "float16"
  device: "cuda"
  
languages:
  input: "auto"  # or specific code
  output: "en"   # for translation
  
ui:
  show_progress: true
  log_level: "INFO"
  
output:
  format: "txt"  # txt, srt, vtt, json
  save_location: "same_as_input"
```

### 6. Model Adapter Pattern

#### 6.1 Base Adapter

```python
# core/models/base.py
class TranscriptionAdapter(ABC):
    @abstractmethod
    def load_model(self, model_name: str, device: str, **kwargs):
        pass
    
    @abstractmethod
    def transcribe(self, audio_path: str, language: str, 
                   progress_callback=None) -> TranscriptionResult:
        pass
    
    @abstractmethod
    def supports_language(self, language_code: str) -> bool:
        pass
```

#### 6.2 Whisper Adapter

- Wraps faster-whisper
- Handles quantization, device selection
- Progress callbacks
- Language support

#### 6.3 HuggingFace Adapter

- Uses transformers library
- Auto-detects ASR pipelines
- Handles different model architectures
- Language support from model metadata

## Implementation Steps

### Phase 1: Foundation

1. Create project structure
2. Implement logging system (copy/adapt from current)
3. Implement config manager
4. Create base model adapter interface
5. Implement venv manager

### Phase 2: Core Services

6. Implement Whisper adapter
7. Implement HuggingFace adapter
8. Create model registry
9. Implement FFmpeg converter
10. Implement transcription service with cancellation

### Phase 3: GUI

11. Create main window
12. Implement progress dialog
13. Implement settings dialog
14. Connect GUI to services

### Phase 4: Integration & Polish

15. Create install script with venv setup
16. Generate starter scripts
17. Add language selection
18. Add progress tracking
19. Testing and bug fixes

### Phase 5: Documentation

20. Create README
21. Add usage examples
22. Document model registry

## Key Differences from Current Project

1. **Video-First Design**: Primary workflow is video → audio → transcription (vs audio-only focus)
2. **Model Flexibility**: Plugin-based system vs hardcoded Whisper models
3. **FFmpeg Integration**: Explicit user-provided path for video conversion (vs bundled PyAV for audio only)
4. **Output Formats**: Multiple format support (txt, srt, vtt) vs clipboard-only
5. **Progress Tracking**: Explicit progress UI with video conversion + transcription stages
6. **Auto-Setup**: Automatic venv creation and script generation
7. **Architecture**: Cleaner separation with adapter pattern
8. **File Management**: Automatic audio file storage alongside video files

## Technical Decisions

- **GUI Framework**: PySide6 (same as current, proven)
- **Model Backend**: faster-whisper + transformers
- **Video Processing**: FFmpeg via subprocess (user-provided)
- **Threading**: QThread for async operations (same as current)
- **Config**: YAML (same as current)
- **Logging**: Rotating file handler (same as current)

## Dependencies

```txt
# Core
PySide6>=6.9.0
faster-whisper>=1.1.0
transformers>=4.30.0
torch>=2.0.0
PyYAML>=6.0
sounddevice>=0.5.0

# Audio/Video
av>=15.0.0  # For audio decoding (fallback if ffmpeg fails)

# Utilities
psutil>=5.9.0
tqdm>=4.65.0  # Progress bars
```

## File Naming Conventions

- Python files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Config keys: `snake_case`