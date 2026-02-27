"""CUDA runtime install via pip (nvidia-cublas-cu12, nvidia-cudnn-cu12).

Provides cublas64_12.dll and cuDNN libraries needed by faster-whisper/CTranslate2
when using GPU. No admin rights required.
"""
from __future__ import annotations

import importlib.util
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Tuple

CUDA_PACKAGES = ["nvidia-cublas-cu12", "nvidia-cudnn-cu12"]

# Package names to lib/bin subdir mapping (Windows uses bin, Linux uses lib)
_NVIDIA_PKG_MODULES = ["nvidia.cublas", "nvidia.cudnn"]
_WIN_LIB_SUBDIR = "bin"
_UNIX_LIB_SUBDIR = "lib"


def get_nvidia_cuda_lib_paths() -> List[Path]:
    """Discover nvidia pip package lib/bin directories for CUDA runtime DLLs.

    Returns paths that contain cublas64_12.dll and cuDNN libraries needed by
    CTranslate2. Call prepend_nvidia_cuda_paths() to add these to the process.
    """
    paths: List[Path] = []
    lib_subdir = _WIN_LIB_SUBDIR if platform.system() == "Windows" else _UNIX_LIB_SUBDIR

    for mod_name in _NVIDIA_PKG_MODULES:
        try:
            spec = importlib.util.find_spec(mod_name)
            if spec is None:
                continue
            # Namespace packages have submodule_search_locations, regular packages have origin
            if spec.origin:
                pkg_dir = Path(spec.origin).resolve().parent
            elif spec.submodule_search_locations:
                pkg_dir = Path(spec.submodule_search_locations[0]).resolve()
            else:
                continue
            lib_path = pkg_dir / lib_subdir
            if lib_path.is_dir() and lib_path not in paths:
                paths.append(lib_path)
        except (ImportError, ValueError, AttributeError, IndexError):
            pass

    return paths


def prepend_nvidia_cuda_paths() -> None:
    """Prepend nvidia pip package lib/bin paths to DLL search so CTranslate2 can find cublas64_12.dll.

    Call this at application startup, before importing faster_whisper or ctranslate2.
    On Windows, also uses os.add_dll_directory() for proper DLL resolution.
    """
    paths = get_nvidia_cuda_lib_paths()
    if not paths:
        return

    path_strs = [str(p) for p in paths]
    sep = os.pathsep
    existing = os.environ.get("PATH", "")
    os.environ["PATH"] = sep.join(path_strs) + sep + existing

    if platform.system() == "Windows":
        for p in paths:
            try:
                os.add_dll_directory(str(p))
            except (OSError, FileNotFoundError):
                pass


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
