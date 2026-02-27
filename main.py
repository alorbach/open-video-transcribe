"""Application entry point for Open Video Transcribe."""
from __future__ import annotations

import sys
import signal
import platform
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from core.logging_config import setup_logging, get_logger
from gui.main_window import MainWindow

logger = get_logger(__name__)


def _get_system_info() -> dict[str, str]:
    """Collect system information for debugging."""
    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
    }
    
    try:
        from PySide6 import __version__ as pyside_version
        info["pyside6_version"] = pyside_version
    except ImportError:
        info["pyside6_version"] = "Not installed"
    
    try:
        import torch
        info["torch_version"] = torch.__version__
        info["cuda_available"] = str(torch.cuda.is_available())
        if torch.cuda.is_available():
            info["cuda_version"] = torch.version.cuda or "Unknown"
            info["cuda_device_count"] = str(torch.cuda.device_count())
            if torch.cuda.device_count() > 0:
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        info["torch_version"] = "Not installed"
        info["cuda_available"] = "False"
    
    return info


def _log_system_info() -> None:
    """Log system information for debugging."""
    logger.info("=" * 60)
    logger.info("Starting Open Video Transcribe")
    logger.info("=" * 60)
    
    system_info = _get_system_info()
    for key, value in system_info.items():
        logger.debug(f"{key}: {value}")
    
    logger.info(f"Working directory: {Path.cwd()}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Script location: {Path(__file__).parent.absolute()}")


def _install_sigint_handler() -> None:
    """Install signal handler for graceful shutdown."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        logger.debug("SIGINT handler installed")
    except (ValueError, OSError) as e:
        logger.warning(f"Could not install SIGINT handler: {e}")


def _check_dependencies() -> tuple[bool, list[str]]:
    """Check if required dependencies are available."""
    missing = []
    
    try:
        import PySide6
        logger.debug("PySide6 is available")
    except ImportError:
        missing.append("PySide6")
        logger.error("PySide6 is not installed")
    
    try:
        import faster_whisper
        logger.debug("faster-whisper is available")
    except ImportError:
        missing.append("faster-whisper")
        logger.warning("faster-whisper is not installed")
    
    return len(missing) == 0, missing


def _check_cuda_availability() -> tuple[bool, str]:
    """Check CUDA availability. Uses CTranslate2 runtime; falls back to nvidia-smi for GPU presence."""
    import subprocess

    def _nvidia_gpu_name() -> str | None:
        """Get first NVIDIA GPU name via nvidia-smi, or None."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split("\n")[0]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    # CTranslate2 (used by faster-whisper) is the source of truth for GPU support
    try:
        import ctranslate2
        get_count = getattr(ctranslate2, "get_cuda_device_count", None)
        if get_count is not None:
            count = get_count()
            if count > 0:
                gpu_name = _nvidia_gpu_name() or "NVIDIA GPU"
                logger.info(f"CTranslate2 CUDA available - Devices: {count}, Device: {gpu_name}")
                return True, f"CUDA ({gpu_name})"
    except Exception as e:
        logger.debug(f"CTranslate2 CUDA check failed: {e}")

    # Fallback: PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            cuda_version = torch.version.cuda or "Unknown"
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            logger.info(f"CUDA available (PyTorch) - Version: {cuda_version}, Devices: {device_count}, Device: {device_name}")
            return True, f"CUDA {cuda_version} ({device_name})"
    except ImportError:
        pass
    except Exception as e:
        logger.debug(f"PyTorch CUDA check failed: {e}")

    # GPU present but CUDA runtime missing - guide user
    gpu_name = _nvidia_gpu_name()
    if gpu_name:
        logger.info(
            f"NVIDIA GPU detected ({gpu_name}) but CUDA 12 runtime libraries missing. "
            "Use Settings > Install CUDA Runtime (nvidia-cublas-cu12, nvidia-cudnn-cu12)."
        )
        return False, f"GPU detected - install CUDA runtime (Settings)"

    logger.info("CUDA is not available - using CPU")
    return False, "CPU only"


def run_gui() -> None:
    """Initialize and run the GUI application."""
    try:
        logger.info("Initializing QApplication...")
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        logger.debug("QApplication initialized with Fusion style")
        
        _install_sigint_handler()
        
        deps_ok, missing = _check_dependencies()
        if not deps_ok:
            logger.error(f"Missing dependencies: {', '.join(missing)}")
            QMessageBox.critical(
                None,
                "Missing Dependencies",
                f"The following required dependencies are missing:\n\n{', '.join(missing)}\n\n"
                "Please install them using: pip install {' '.join(missing)}"
            )
            sys.exit(1)
        
        cuda_ok, cuda_info = _check_cuda_availability()
        logger.info(f"Device status: {cuda_info}")
        
        logger.info("Creating MainWindow...")
        window = MainWindow(cuda_available=cuda_ok)
        window.show()
        logger.info("MainWindow created and shown")
        
        logger.info("Starting application event loop...")
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        error_msg = f"Fatal error during application startup: {e}"
        logger.critical(error_msg, exc_info=True)
        
        try:
            if 'app' in locals():
                QMessageBox.critical(
                    None,
                    "Fatal Error",
                    f"{error_msg}\n\nCheck the log file for details."
                )
        except Exception:
            pass
        
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    try:
        log_level = logging.DEBUG if "--debug" in sys.argv else logging.INFO
        log_file = setup_logging(level=log_level)
        logger.info(f"Logging initialized - Log file: {log_file}")

        from core.cuda_install import prepend_nvidia_cuda_paths
        prepend_nvidia_cuda_paths()

        _log_system_info()
        
        run_gui()
    except Exception as e:
        print(f"Critical error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

