"""Installation script for Open Video Transcribe."""
import sys
import subprocess
import os
import platform
import shutil
import urllib.request
import zipfile
import tempfile
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11 or 3.12."""
    major, minor = sys.version_info[:2]
    if major == 3 and minor in [11, 12]:
        return True
    return False

def has_nvidia_gpu():
    """Check if NVIDIA GPU is available."""
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def create_venv():
    """Create virtual environment if it doesn't exist."""
    venv_path = Path("venv")
    if venv_path.exists():
        print("Virtual environment already exists")
        return True
    
    print("Creating virtual environment...")
    try:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print("Virtual environment created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        return False

def get_venv_python():
    """Get path to venv Python executable."""
    if platform.system() == "Windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"

def install_requirements():
    """Install requirements in venv."""
    venv_python = get_venv_python()
    if not venv_python.exists():
        print("Virtual environment Python not found")
        return False
    
    print("Installing requirements...")
    try:
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install requirements: {e}")
        return False

def install_torch(gpu_available):
    """Install PyTorch with appropriate CUDA support."""
    venv_python = get_venv_python()
    if not venv_python.exists():
        return False
    
    python_version = f"cp{sys.version_info.major}{sys.version_info.minor}"
    
    if gpu_available and python_version in ["cp311", "cp312"]:
        print("Installing PyTorch with CUDA support...")
        torch_urls = {
            "cp311": "https://download.pytorch.org/whl/cu128/torch-2.8.0%2Bcu128-cp311-cp311-win_amd64.whl",
            "cp312": "https://download.pytorch.org/whl/cu128/torch-2.8.0%2Bcu128-cp312-cp312-win_amd64.whl"
        }
        try:
            subprocess.run([str(venv_python), "-m", "pip", "install", torch_urls[python_version]], check=True)
            print("PyTorch with CUDA installed successfully")
        except subprocess.CalledProcessError:
            print("Failed to install PyTorch with CUDA, falling back to CPU version")
            subprocess.run([str(venv_python), "-m", "pip", "install", "torch"], check=True)
    else:
        print("Installing PyTorch (CPU version)...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "torch"], check=True)
    
    return True

def download_ffmpeg():
    """Download and extract FFmpeg if ffmpeg folder doesn't exist."""
    ffmpeg_dir = Path("ffmpeg")
    if ffmpeg_dir.exists():
        print("FFmpeg folder already exists")
        return True
    
    system = platform.system()
    
    if system == "Windows":
        print("Downloading FFmpeg for Windows...")
        # FFmpeg Windows build URL (static build, latest release)
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        ffmpeg_exe_path = ffmpeg_dir / "bin" / "ffmpeg.exe"
    elif system == "Linux":
        print("FFmpeg download for Linux not implemented.")
        print("Please install FFmpeg using your package manager:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Fedora: sudo dnf install ffmpeg")
        print("  Arch: sudo pacman -S ffmpeg")
        return False
    elif system == "Darwin":  # macOS
        print("FFmpeg download for macOS not implemented.")
        print("Please install FFmpeg using Homebrew:")
        print("  brew install ffmpeg")
        return False
    else:
        print(f"FFmpeg download not implemented for {system}")
        return False
    
    if system == "Windows":
        try:
            # Create temp directory for download
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "ffmpeg.zip"
                
                print("Downloading FFmpeg (this may take a few minutes)...")
                urllib.request.urlretrieve(ffmpeg_url, zip_path)
                
                print("Extracting FFmpeg...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Extract to temp directory first
                    extract_temp = Path(temp_dir) / "extract"
                    zip_ref.extractall(extract_temp)
                    
                    # Find the ffmpeg folder in the extracted contents
                    extracted_dirs = list(extract_temp.iterdir())
                    if not extracted_dirs:
                        print("Error: FFmpeg archive structure unexpected")
                        return False
                    
                    # Usually the structure is: ffmpeg-*-essentials/ffmpeg-*-essentials/...
                    source_dir = extracted_dirs[0]
                    # Look for bin/ffmpeg.exe
                    for item in source_dir.rglob("ffmpeg.exe"):
                        # Found ffmpeg.exe, get its parent directory structure
                        bin_dir = item.parent
                        # Get the root of the ffmpeg installation
                        ffmpeg_root = bin_dir.parent
                        # Copy the entire ffmpeg structure
                        shutil.copytree(ffmpeg_root, ffmpeg_dir)
                        break
                    else:
                        print("Error: Could not find ffmpeg.exe in archive")
                        return False
                
                # Verify installation
                if ffmpeg_exe_path.exists():
                    print(f"FFmpeg installed successfully to {ffmpeg_dir}")
                    return True
                else:
                    print(f"Error: FFmpeg executable not found at {ffmpeg_exe_path}")
                    return False
                    
        except urllib.error.URLError as e:
            print(f"Error downloading FFmpeg: {e}")
            print("Please download FFmpeg manually from https://ffmpeg.org/download.html")
            return False
        except zipfile.BadZipFile:
            print("Error: Downloaded file is not a valid ZIP archive")
            return False
        except Exception as e:
            print(f"Error installing FFmpeg: {e}")
            return False
    
    return False

def create_config_file():
    """Create config.yaml from sample if it doesn't exist."""
    config_path = Path("config.yaml")
    sample_path = Path("config.yaml.sample")
    
    if config_path.exists():
        print("config.yaml already exists")
        # Check if FFmpeg path should be updated
        try:
            import yaml
            with config_path.open() as f:
                config = yaml.safe_load(f) or {}
            
            ffmpeg_path = config.get("ffmpeg_path", "")
            ffmpeg_exe = Path("ffmpeg") / "bin" / "ffmpeg.exe"
            
            # If ffmpeg_path is empty and we have downloaded FFmpeg, update it
            if not ffmpeg_path and ffmpeg_exe.exists():
                config["ffmpeg_path"] = str(ffmpeg_exe.absolute())
                with config_path.open("w") as f:
                    yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)
                print(f"Updated config.yaml with FFmpeg path: {config['ffmpeg_path']}")
        except ImportError:
            # PyYAML not available yet, that's okay
            pass
        except Exception as e:
            print(f"Warning: Could not update config.yaml: {e}")
        return True
    
    if not sample_path.exists():
        print("Warning: config.yaml.sample not found, creating default config.yaml")
        # Check if we have downloaded FFmpeg
        ffmpeg_exe = Path("ffmpeg") / "bin" / "ffmpeg.exe"
        ffmpeg_path = str(ffmpeg_exe.absolute()) if ffmpeg_exe.exists() else ""
        
        default_config = f"""ffmpeg_path: "{ffmpeg_path}"
model:
  type: whisper
  name: large-v3
  quantization: float16
  device: cuda
languages:
  input: auto
  output: en
ui:
  show_progress: true
  log_level: INFO
output:
  format: txt
  save_location: same_as_input
"""
        config_path.write_text(default_config, encoding="utf-8")
        print("Created default config.yaml")
        return True
    
    try:
        shutil.copy(sample_path, config_path)
        print("Created config.yaml from config.yaml.sample")
        
        # Update FFmpeg path if we downloaded it
        ffmpeg_exe = Path("ffmpeg") / "bin" / "ffmpeg.exe"
        if ffmpeg_exe.exists():
            try:
                import yaml
                with config_path.open() as f:
                    config = yaml.safe_load(f) or {}
                config["ffmpeg_path"] = str(ffmpeg_exe.absolute())
                with config_path.open("w") as f:
                    yaml.safe_dump(config, f, sort_keys=False, default_flow_style=False)
                print(f"Updated config.yaml with FFmpeg path: {config['ffmpeg_path']}")
            except ImportError:
                # PyYAML not available yet, that's okay - user can set path manually
                print(f"Note: FFmpeg downloaded to {ffmpeg_exe.absolute()}")
                print("      Please set ffmpeg_path in config.yaml manually")
            except Exception as e:
                print(f"Warning: Could not update FFmpeg path in config: {e}")
        
        return True
    except Exception as e:
        print(f"Failed to create config.yaml: {e}")
        return False

def generate_starter_scripts():
    """Generate starter scripts for Windows and Unix."""
    if platform.system() == "Windows":
        run_bat = """@echo off
if not exist venv\\Scripts\\python.exe (
    echo Virtual environment not found. Please run install.py first.
    pause
    exit /b 1
)
call venv\\Scripts\\activate.bat
python main.py
pause
"""
        Path("run.bat").write_text(run_bat)
        
        setup_bat = """@echo off
python install.py
pause
"""
        Path("setup.bat").write_text(setup_bat)
    else:
        run_sh = """#!/bin/bash
if [ ! -f venv/bin/python ]; then
    echo "Virtual environment not found. Please run install.py first."
    exit 1
fi
source venv/bin/activate
python main.py
"""
        Path("run.sh").write_text(run_sh)
        Path("run.sh").chmod(0o755)
        
        setup_sh = """#!/bin/bash
python install.py
"""
        Path("setup.sh").write_text(setup_sh)
        Path("setup.sh").chmod(0o755)
    
    print("Starter scripts generated")

def main():
    """Main installation function."""
    print("=" * 60)
    print("Open Video Transcribe - Installation")
    print("=" * 60)
    
    if not check_python_version():
        print("Error: Python 3.11 or 3.12 is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    
    print(f"Python version: {sys.version}")
    
    gpu_available = has_nvidia_gpu()
    print(f"GPU available: {gpu_available}")
    
    if not create_venv():
        sys.exit(1)
    
    if not install_requirements():
        sys.exit(1)
    
    if not install_torch(gpu_available):
        sys.exit(1)
    
    # Download FFmpeg if not present
    download_ffmpeg()
    
    # Create config file (will update FFmpeg path if downloaded)
    create_config_file()
    
    generate_starter_scripts()
    
    print("=" * 60)
    print("Installation completed successfully!")
    print("=" * 60)
    print("You can now run the application using:")
    if platform.system() == "Windows":
        print("  run.bat")
    else:
        print("  ./run.sh")

if __name__ == "__main__":
    main()

