"""FFmpeg download/install for Windows (used by install.py and GUI)."""
from __future__ import annotations

import platform
import shutil
import urllib.error
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Tuple

FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def download_ffmpeg() -> Tuple[bool, str]:
    """Download and extract FFmpeg for Windows.

    Returns:
        Tuple of (success, message).
    """
    ffmpeg_dir = Path("ffmpeg")
    ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"

    if ffmpeg_exe.exists():
        return True, str(ffmpeg_exe.absolute())

    if platform.system() != "Windows":
        return False, "FFmpeg auto-download is only supported on Windows. Please install FFmpeg via your package manager."

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = Path(temp_dir) / "ffmpeg.zip"

            urllib.request.urlretrieve(FFMPEG_URL, zip_path)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                extract_temp = Path(temp_dir) / "extract"
                zip_ref.extractall(extract_temp)

                extracted_dirs = list(extract_temp.iterdir())
                if not extracted_dirs:
                    return False, "FFmpeg archive structure unexpected"

                source_dir = extracted_dirs[0]
                for item in source_dir.rglob("ffmpeg.exe"):
                    bin_dir = item.parent
                    ffmpeg_root = bin_dir.parent
                    shutil.copytree(ffmpeg_root, ffmpeg_dir)
                    break
                else:
                    return False, "Could not find ffmpeg.exe in archive"

        if ffmpeg_exe.exists():
            return True, str(ffmpeg_exe.absolute())
        return False, f"FFmpeg executable not found at {ffmpeg_exe}"

    except urllib.error.URLError as e:
        return False, f"Download failed: {e}. Get FFmpeg from https://ffmpeg.org/download.html"
    except zipfile.BadZipFile:
        return False, "Downloaded file is not a valid ZIP archive"
    except Exception as e:
        return False, str(e)
