# Installation Guide

Detailed installation instructions for Open Video Transcribe.

## Quick Installation (Recommended)

### Windows

1. **Download the project** to your computer
2. **Double-click `setup.bat`**
3. Follow the on-screen prompts:
   - Select Python version (auto-selects 3.11/3.12 if available)
   - Wait for installation to complete
4. **Done!** You can now run `run.bat` to start the application

### Linux/macOS

1. **Open terminal** in the project directory
2. **Run**: `./setup.sh`
3. Wait for installation to complete
4. **Run**: `./run.sh` to start the application

## Detailed Installation Steps

### Step 1: Verify Python Installation

Open a terminal/command prompt and check Python version:

```bash
python --version
```

You need **Python 3.11 or 3.12**. If you don't have it:

- **Windows**: Download from https://www.python.org/downloads/
- **Linux**: Use your package manager: `sudo apt install python3.11` (Ubuntu/Debian)
- **macOS**: Use Homebrew: `brew install python@3.11`

### Step 2: Run the Installer

#### Windows

```cmd
setup.bat
```

The script will:
- Detect all installed Python versions
- Let you choose which to use
- Create virtual environment
- Install dependencies
- Download FFmpeg (Windows only)
- Generate starter scripts

#### Linux/macOS

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
python install.py
```

### Step 3: What Gets Installed

The installer creates:

- **`venv/`** - Virtual environment with all Python packages
- **`ffmpeg/`** - FFmpeg binaries (Windows only, auto-downloaded)
- **`config.yaml`** - Configuration file (created from template)
- **`run.bat` / `run.sh`** - Starter scripts
- **`logs/`** - Log directory

### Step 4: Verify Installation

Check that these files/folders exist:

- ✅ `venv/` folder
- ✅ `config.yaml` file
- ✅ `ffmpeg/` folder (Windows) or FFmpeg installed system-wide (Linux/macOS)

## Manual Installation

If the automated installer doesn't work, you can install manually:

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows**:
```cmd
venv\Scripts\activate
```

**Linux/macOS**:
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install PyTorch

**With GPU (NVIDIA)**:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu128
```

**CPU only**:
```bash
pip install torch
```

### 5. Install FFmpeg

**Windows**:
- Download from https://www.gyan.dev/ffmpeg/builds/
- Extract to `ffmpeg/` folder in project directory
- Or use the auto-download feature in `install.py`

**Linux**:
```bash
sudo apt install ffmpeg  # Ubuntu/Debian
sudo dnf install ffmpeg  # Fedora
sudo pacman -S ffmpeg    # Arch
```

**macOS**:
```bash
brew install ffmpeg
```

### 6. Create Configuration

Copy the sample config:

```bash
cp config.yaml.sample config.yaml
```

Edit `config.yaml` and set your FFmpeg path.

## Post-Installation

### First Run

1. Start the application:
   - Windows: `run.bat`
   - Linux/macOS: `./run.sh`

2. **Windows Users**: FFmpeg should already be configured automatically. Skip to step 3.
   
   **Linux/macOS Users**: Configure FFmpeg path in Settings if not detected automatically.

3. Load a model (this will download it on first use)

4. Select a video or audio file to transcribe

5. The transcription will be saved in the same directory as your input file with the same name

### Updating

To update the application:

1. Pull latest changes from repository
2. Re-run `setup.bat` or `install.py`
3. Dependencies will be updated automatically

## Troubleshooting Installation

### Python Version Error

**Error**: "Python 3.11 or 3.12 is required"

**Solution**: Install Python 3.11 or 3.12 and run setup again.

### Virtual Environment Creation Fails

**Error**: "Failed to create virtual environment"

**Solution**:
- Ensure Python 3.11 or 3.12 is in PATH
- Try running as administrator (Windows)
- Check disk space

### Dependency Installation Fails

**Error**: "Failed to install requirements"

**Solution**:
- Check internet connection
- Try upgrading pip: `python -m pip install --upgrade pip`
- Install dependencies one by one to identify the problematic package

### FFmpeg Download Fails (Windows)

**Error**: "Error downloading FFmpeg"

**Solution**:
- Check internet connection
- Download manually from https://www.gyan.dev/ffmpeg/builds/
- Extract to `ffmpeg/` folder
- Set path in `config.yaml`

### PyTorch Installation Issues

**Error**: CUDA-related errors

**Solution**:
- For CPU-only: `pip install torch`
- For GPU: Ensure NVIDIA drivers are installed first
- Check CUDA compatibility with your GPU

## System Requirements

### Minimum Requirements

- **OS**: Windows 10+, Linux (Ubuntu 20.04+), macOS 10.15+
- **Python**: 3.11 or 3.12
- **RAM**: 4 GB (8 GB recommended)
- **Disk Space**: 5 GB free (for models and dependencies)
- **Internet**: Required for initial setup and model downloads

### Recommended Requirements

- **RAM**: 16 GB or more
- **GPU**: NVIDIA GPU with CUDA support (for faster transcription)
- **Disk Space**: 10 GB free (for larger models)
- **CPU**: Multi-core processor

## Next Steps

After installation:

1. Read the [User Guide](USER_GUIDE.md) for usage instructions
2. Check [README.md](../README.md) for overview
3. Start transcribing! Run `run.bat` (Windows) or `./run.sh` (Linux/macOS)

