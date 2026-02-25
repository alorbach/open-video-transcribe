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
    """Check if Python version is 3.11, 3.12, or 3.13."""
    major, minor = sys.version_info[:2]
    if major == 3 and minor in [11, 12, 13]:
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
            "cp312": "https://download.pytorch.org/whl/cu128/torch-2.8.0%2Bcu128-cp312-cp312-win_amd64.whl",
        }
        try:
            subprocess.run([str(venv_python), "-m", "pip", "install", torch_urls[python_version]], check=True)
            print("PyTorch with CUDA installed successfully")
            if platform.system() == "Windows":
                print("Installing CUDA runtime libraries (nvidia-cublas-cu12, nvidia-cudnn-cu12)...")
                from core.cuda_install import install_cuda_redist
                cuda_ok, cuda_msg = install_cuda_redist()
                if cuda_ok:
                    print(cuda_msg)
                else:
                    print(f"CUDA runtime install skipped or failed: {cuda_msg}")
                    print("If GPU fails with cublas64_12.dll error, run Install CUDA in Settings.")
        except subprocess.CalledProcessError:
            print("Failed to install PyTorch with CUDA, falling back to CPU version")
            subprocess.run([str(venv_python), "-m", "pip", "install", "torch"], check=True)
    else:
        print("Installing PyTorch (CPU version)...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "torch"], check=True)
        if gpu_available and platform.system() == "Windows":
            print("Installing CUDA runtime (nvidia-cublas-cu12, nvidia-cudnn-cu12)...")
            from core.cuda_install import install_cuda_redist
            cuda_ok, _ = install_cuda_redist()
            if not cuda_ok:
                print("CUDA runtime install failed. Use Settings > Install CUDA if GPU fails.")
    
    return True

def download_ffmpeg():
    """Download and extract FFmpeg if ffmpeg folder doesn't exist."""
    if platform.system() == "Linux":
        print("FFmpeg download for Linux not implemented.")
        print("Please install FFmpeg using your package manager:")
        print("  Ubuntu/Debian: sudo apt install ffmpeg")
        print("  Fedora: sudo dnf install ffmpeg")
        print("  Arch: sudo pacman -S ffmpeg")
        return False
    if platform.system() == "Darwin":
        print("FFmpeg download for macOS not implemented.")
        print("Please install FFmpeg using Homebrew:")
        print("  brew install ffmpeg")
        return False
    if platform.system() != "Windows":
        print(f"FFmpeg download not implemented for {platform.system()}")
        return False

    print("Downloading FFmpeg for Windows...")
    from core.ffmpeg_install import download_ffmpeg as _download
    success, msg = _download()
    if success:
        print(msg)
        return True
    print(f"Error: {msg}")
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
        
        setup_bat = r"""@echo off
cd /d "%~dp0"

echo.
echo ============================================================
echo Open Video Transcribe - Installation
echo ============================================================
echo.
echo Python 3.11, 3.12, or 3.13 is required.
echo.

:menu
echo Select Python version:
echo   [1] Python 3.12 (py -3.12 or common paths)
echo   [2] Python 3.11 (py -3.11 or common paths)
echo   [3] Default (python from PATH)
echo   [4] Enter custom path
echo   [5] Search for Python 3.11/3.12 on this computer
echo   [0] Auto (try 3.12, then 3.11, then default)
echo.
set /p choice="Enter choice [0-5] (default 0): "
if "%choice%"=="" set choice=0

if "%choice%"=="0" goto auto
if "%choice%"=="1" goto use312
if "%choice%"=="2" goto use311
if "%choice%"=="3" goto use_default
if "%choice%"=="4" goto use_custom
if "%choice%"=="5" goto search_python
goto menu

:auto
echo.
echo Auto-selecting Python...
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        echo Using Python 3.12 (via py launcher)
        py -3.12 install.py
        goto end
    )
)
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.11 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        echo Using Python 3.11 (via py launcher)
        py -3.11 install.py
        goto end
    )
)
call :find_python312
if defined PY312_PATH (
    echo Using Python 3.12: %PY312_PATH%
    "%PY312_PATH%" install.py
    goto end
)
call :find_python311
if defined PY311_PATH (
    echo Using Python 3.11: %PY311_PATH%
    "%PY311_PATH%" install.py
    goto end
)
echo Python Launcher (py) not found or no 3.11/3.12 installed. Trying default...
goto use_default

:use312
echo.
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.12 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        py -3.12 install.py
        goto end
    )
)
call :find_python312
if defined PY312_PATH (
    "%PY312_PATH%" install.py
    goto end
)
echo Error: Python 3.12 not found.
echo.
echo Try option [4] to enter path, or option [5] to search for Python.
pause
exit /b 1

:use311
echo.
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3.11 -c "import sys; exit(0)" 2>nul
    if %errorlevel% equ 0 (
        py -3.11 install.py
        goto end
    )
)
call :find_python311
if defined PY311_PATH (
    "%PY311_PATH%" install.py
    goto end
)
echo Error: Python 3.11 not found. Try option [4] with path to python.exe
pause
exit /b 1

:use_default
echo.
python install.py
goto end

:use_custom
echo.
set /p py_path="Enter full path to python.exe (e.g. C:\Python312\python.exe): "
if "%py_path%"=="" (
    echo No path entered.
    goto menu
)
if not exist "%py_path%" (
    echo File not found: %py_path%
    pause
    goto menu
)
"%py_path%" install.py
goto end

:search_python
echo.
echo Searching common locations for Python 3.11 and 3.12...
powershell -NoProfile -Command "$paths = @('%%LocalAppData%%\\Programs\\Python\\Python312\\python.exe', '%%LocalAppData%%\\Programs\\Python\\Python311\\python.exe', 'C:\\Python312\\python.exe', 'C:\\Python311\\python.exe', '%%ProgramFiles%%\\Python312\\python.exe', '%%ProgramFiles%%\\Python311\\python.exe', '%%UserProfile%%\\AppData\\Local\\Programs\\Python\\Python312\\python.exe', '%%UserProfile%%\\AppData\\Local\\Programs\\Python\\Python311\\python.exe'); foreach ($p in $paths) { $exp = [Environment]::ExpandEnvironmentVariables($p); if (Test-Path $exp) { try { $v = & $exp -c 'import sys; print(sys.version_info.minor)' 2>$null; if ($v -match '^(11|12)$') { Write-Host 'FOUND:' $exp } } catch {} } }"
echo.
echo If found above, use option [4] and paste the path.
echo.
goto menu

:end
pause
exit /b 0

:find_python312
set PY312_PATH=
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY312_PATH=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :eof
)
if exist "C:\Python312\python.exe" (
    set "PY312_PATH=C:\Python312\python.exe"
    goto :eof
)
if exist "%ProgramFiles%\Python312\python.exe" (
    set "PY312_PATH=%ProgramFiles%\Python312\python.exe"
    goto :eof
)
if exist "%UserProfile%\AppData\Local\Programs\Python\Python312\python.exe" (
    set "PY312_PATH=%UserProfile%\AppData\Local\Programs\Python\Python312\python.exe"
    goto :eof
)
goto :eof

:find_python311
set PY311_PATH=
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY311_PATH=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto :eof
)
if exist "C:\Python311\python.exe" (
    set "PY311_PATH=C:\Python311\python.exe"
    goto :eof
)
if exist "%ProgramFiles%\Python311\python.exe" (
    set "PY311_PATH=%ProgramFiles%\Python311\python.exe"
    goto :eof
)
goto :eof
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
        print("Error: Python 3.11, 3.12, or 3.13 is required")
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

