# Open Video Transcribe

Open-source video transcription tool that emphasizes the primary use case: transcribing video files to text with support for multiple model types.

## Features

- **Video-First Design**: Primary workflow is video → audio → transcription
- **FFmpeg Integration**: Automatic video-to-audio conversion using user-provided FFmpeg
- **Multiple Model Support**: Plugin-based system supporting Whisper and HuggingFace ASR models
- **GPU Acceleration**: Automatic CUDA detection and support
- **Multiple Output Formats**: Save transcriptions as TXT (with timestamps), SRT, or VTT
- **Progress Tracking**: Real-time progress indicators for conversion and transcription
- **Drag and Drop**: Drag video/audio files directly onto the application window
- **Test Mode**: Transcribe only first 5 minutes for quick testing
- **Timestamps**: TXT output includes timestamps at the beginning of each line
- **Auto-Setup**: Automatic virtual environment creation and dependency installation

## Requirements

- Python 3.11 or 3.12
- FFmpeg (auto-downloaded on Windows, user-provided on Linux/macOS)
- NVIDIA GPU (optional, for CUDA acceleration)

## Installation

### Quick Start

1. Run the setup script:
   ```bash
   # Windows
   setup.bat
   
   # Linux/macOS
   ./setup.sh
   ```

   Or manually:
   ```bash
   python install.py
   ```

2. The installer will:
   - Detect installed Python versions (using Python Launcher)
   - Let you choose which Python version to use (auto-selects 3.11 or 3.12 if available)
   - Verify Python version is 3.11 or 3.12
   - Create a virtual environment
   - Install all dependencies
   - Detect GPU and install appropriate PyTorch version
   - **Download FFmpeg automatically (Windows only)**
   - Generate starter scripts

📖 **For detailed installation instructions, see [Installation Guide](doc/INSTALLATION.md)**

### Manual Installation

1. Create virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install PyTorch (with CUDA if GPU available):
   ```bash
   # GPU version (if NVIDIA GPU available)
   pip install torch --index-url https://download.pytorch.org/whl/cu128
   
   # CPU version
   pip install torch
   ```

## Usage

### Running the Application

```bash
# Windows
run.bat

# Linux/macOS
./run.sh
```

Or manually:
```bash
# Activate venv first
python main.py
```

### Configuration

1. **FFmpeg Path**: Set the path to your FFmpeg executable in Settings (auto-configured on Windows)
2. **Model Selection**: Choose Whisper model, quantization, and device
3. **Language**: Select input language (or auto-detect)
4. **Output Format**: Choose TXT, SRT, or VTT format

### Workflow

1. **Select a File**:
   - Click "Select Video/Audio File" to choose a file, OR
   - Drag and drop a video/audio file directly onto the window
2. **Choose Mode**:
   - **Full File**: Transcribe the entire file
   - **Test Mode (5 min)**: Transcribe only first 5 minutes (for testing)
3. The tool automatically:
   - Converts video to audio (if video file) - progress shown in real-time
   - Transcribes the audio - progress updated during processing
   - Saves the transcription in the selected format

**Output Location**: The transcription file is saved in the same directory as your input file, with the same basename. For example, `my_video.mp4` → `my_video.txt`.

**Output Format**: TXT files include timestamps at the beginning of each line (e.g., `0:35 Transcribed text`), making it easy to navigate the transcription.

📖 **For complete usage instructions with screenshots, see [User Guide](doc/USER_GUIDE.md)**

## Project Structure

```
open-video-transcribe/
├── main.py                 # Entry point
├── install.py              # Auto venv creation & dependency installer
├── requirements.txt        # Python dependencies
├── config.yaml             # User configuration
├── run.bat / run.sh        # Starter scripts
├── setup.bat / setup.sh    # Setup scripts
│
├── core/
│   ├── controller.py       # Main orchestrator
│   ├── logging_config.py   # Logging setup
│   ├── exceptions.py       # Custom exceptions
│   │
│   ├── audio/
│   │   └── converter.py    # FFmpeg video-to-audio conversion
│   │
│   ├── models/
│   │   ├── base.py         # Abstract base class for models
│   │   ├── whisper_adapter.py    # Whisper model adapter
│   │   └── registry.py     # Model registry/discovery
│   │
│   └── transcription/
│       ├── service.py      # Transcription service
│       └── progress.py     # Progress tracking
│
├── gui/
│   ├── main_window.py      # Main GUI window
│   ├── progress_dialog.py  # Progress indicator
│   └── settings_dialog.py  # Settings/configuration UI
│
└── config/
    └── manager.py          # Configuration management
```

## Configuration

The `config.yaml` file stores user preferences:

```yaml
ffmpeg_path: ""  # User-provided path
model:
  type: whisper
  name: large-v3
  quantization: float16
  device: cuda
languages:
  input: auto
  output: en
output:
  format: txt
  save_location: same_as_input
```

## Supported Formats

### Video Formats
- MP4, AVI, MKV, WebM, MOV, FLV, WMV, M4V

### Audio Formats
- MP3, WAV, AAC, FLAC, M4A, OGG

### Output Formats
- TXT: Plain text
- SRT: SubRip subtitle format
- VTT: WebVTT subtitle format

## Model Support

Currently supports:
- **Whisper models** via faster-whisper
  - tiny, base, small, medium, large-v1, large-v2, large-v3
  - distil-small.en, distil-medium.en, distil-large-v2, distil-large-v3

Future support planned:
- HuggingFace ASR models

## Troubleshooting

### FFmpeg Not Found
- **Windows**: FFmpeg is downloaded automatically during installation. If missing, re-run `setup.bat`
- **Linux/macOS**: Install via package manager (see [Installation Guide](doc/INSTALLATION.md))
- Ensure FFmpeg path is set correctly in Settings
- Download manually from: https://ffmpeg.org/download.html

### Model Loading Fails
- Check internet connection (models are downloaded from HuggingFace)
- Ensure sufficient disk space
- Try a smaller model if memory is limited

### CUDA Errors
- Verify NVIDIA drivers are installed
- Check CUDA compatibility with PyTorch version
- Fall back to CPU mode if GPU issues persist

## License

Open source - see LICENSE file for details.

## Python Version Selection

The `setup.bat` script (Windows) automatically detects installed Python versions and allows you to choose:

- **Auto-detection**: Uses Python Launcher (`py`) to find all installed versions
- **Auto-selection**: Automatically selects Python 3.12 or 3.11 if available
- **Manual selection**: Menu to choose from available versions
- **Custom path**: Option to specify a custom Python executable path
- **Validation**: Verifies selected Python is version 3.11 or 3.12 before proceeding

## Contributing

Contributions welcome! Please follow the existing code style and architecture patterns.

For AI agents working on this project, see [AGENTS.md](AGENTS.md) for detailed architecture and development guidelines.

