"""CUDA runtime install via pip (nvidia-cublas-cu12, nvidia-cudnn-cu12).

Provides cublas64_12.dll and cuDNN libraries needed by faster-whisper/CTranslate2
when using GPU. No admin rights required.
"""
from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from typing import Tuple

CUDA_PACKAGES = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]


def _get_venv_python() -> Path | None:
    """Get path to venv Python executable (relative to project root)."""
    project_root = Path(__file__).resolve().parent.parent
    if platform.system() == "Windows":
        venv_python = project_root / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = project_root / "venv" / "bin" / "python"
    return venv_python if venv_python.exists() else None


def install_cuda_redist() -> Tuple[bool, str]:
    """Install CUDA runtime libraries via pip (nvidia-cublas-cu12, nvidia-cudnn-cu12).

    Required for faster-whisper GPU when cublas64_12.dll is missing.
    No admin rights needed. Downloads ~400-600MB.

    Returns:
        Tuple of (success, message).
    """
    if platform.system() != "Windows":
        return False, "CUDA auto-install is only supported on Windows."

    venv_python = _get_venv_python()
    if not venv_python:
        return False, "Virtual environment not found. Run setup.bat first."

    project_root = Path(__file__).resolve().parent.parent
    try:
        orig_cwd = os.getcwd()
        os.chdir(project_root)
        try:
            for pkg in CUDA_PACKAGES:
                subprocess.run(
                    [str(venv_python), "-m", "pip", "install", pkg],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            return True, "CUDA runtime libraries installed. Restart the application and try GPU again."
        finally:
            os.chdir(orig_cwd)
    except subprocess.TimeoutExpired:
        return False, "Installation timed out. Try running: pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        return False, f"Installation failed: {err}"
    except Exception as e:
        return False, str(e)
