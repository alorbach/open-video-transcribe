"""FFmpeg video-to-audio converter."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional, Callable

from core.logging_config import get_logger
from core.exceptions import FFmpegError

logger = get_logger(__name__)


class FFmpegConverter:
    """Converts video files to audio using FFmpeg."""
    
    SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mkv", ".webm", ".mov", ".flv", ".wmv", ".m4v"]
    SUPPORTED_AUDIO_FORMATS = [".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg"]
    
    def __init__(self, ffmpeg_path: str):
        """Initialize converter with FFmpeg path.
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
        """
        self.ffmpeg_path = Path(ffmpeg_path)
        self._validate_ffmpeg()
    
    def _validate_ffmpeg(self) -> None:
        """Validate that FFmpeg is available."""
        if not self.ffmpeg_path.exists():
            raise FFmpegError(f"FFmpeg not found at: {self.ffmpeg_path}")
        
        try:
            result = subprocess.run(
                [str(self.ffmpeg_path), "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise FFmpegError(f"FFmpeg validation failed: {result.stderr}")
            logger.info(f"FFmpeg validated: {result.stdout.split()[2]}")
        except subprocess.TimeoutExpired:
            raise FFmpegError("FFmpeg validation timed out")
        except Exception as e:
            raise FFmpegError(f"FFmpeg validation error: {e}") from e
    
    def is_video_file(self, file_path: Path) -> bool:
        """Check if file is a supported video format."""
        return file_path.suffix.lower() in self.SUPPORTED_VIDEO_FORMATS
    
    def is_audio_file(self, file_path: Path) -> bool:
        """Check if file is a supported audio format."""
        return file_path.suffix.lower() in self.SUPPORTED_AUDIO_FORMATS
    
    def convert_video_to_audio(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        audio_format: str = "wav",
        progress_callback: Optional[Callable[[float], None]] = None,
        duration_limit: Optional[float] = None
    ) -> Path:
        """Convert video file to audio.
        
        Args:
            video_path: Path to video file
            output_path: Optional output path (default: same directory as video)
            audio_format: Output audio format (wav, mp3, etc.)
            progress_callback: Optional callback for progress (0.0-1.0)
            duration_limit: Optional duration limit in seconds (e.g., 300 for 5 minutes)
            
        Returns:
            Path to converted audio file
        """
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FFmpegError(f"File not found: {video_path}")
        
        # Allow audio files if duration_limit is set (for test mode)
        if duration_limit is None:
            if not self.is_video_file(video_path):
                raise FFmpegError(f"Unsupported video format: {video_path.suffix}")
        else:
            # In test mode, allow both video and audio files
            if not (self.is_video_file(video_path) or self.is_audio_file(video_path)):
                raise FFmpegError(f"Unsupported file format: {video_path.suffix}")
        
        if output_path is None:
            output_path = video_path.with_suffix(f".{audio_format}")
        else:
            output_path = Path(output_path)
            if not output_path.suffix:
                output_path = output_path.with_suffix(f".{audio_format}")
        
        logger.info(f"Converting video {video_path} to audio {output_path}")
        
        try:
            cmd = [
                str(self.ffmpeg_path),
                "-i", str(video_path),
                "-vn",
                "-acodec", "pcm_s16le" if audio_format == "wav" else "libmp3lame",
                "-ar", "16000",
                "-ac", "1",
            ]
            
            # Add duration limit if specified (for test mode)
            if duration_limit is not None:
                cmd.extend(["-t", str(duration_limit)])
            
            cmd.extend(["-y", str(output_path)])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            duration = None
            current_time = None
            
            for line in iter(process.stderr.readline, ''):
                if not line:
                    break
                
                if "Duration:" in line:
                    try:
                        time_str = line.split("Duration:")[1].split(",")[0].strip()
                        parts = time_str.split(":")
                        duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                    except (IndexError, ValueError):
                        pass
                
                if "time=" in line:
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        parts = time_str.split(":")
                        current_time = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                        if duration and progress_callback:
                            progress = min(current_time / duration, 0.99)  # Cap at 99% until complete
                            progress_callback(progress)
                    except (IndexError, ValueError):
                        pass
                
                # Also check for frame-based progress (alternative format)
                if "frame=" in line and "fps=" in line:
                    # This is a fallback if time-based progress doesn't work
                    if duration and progress_callback:
                        # Try to extract frame info (rough estimate)
                        try:
                            # This is a fallback - we'll use time-based primarily
                            pass
                        except (IndexError, ValueError):
                            pass
            
            # Ensure we show 100% when complete
            if duration and progress_callback:
                progress_callback(1.0)
            
            process.wait()
            
            if process.returncode != 0:
                _, error_output = process.communicate()
                raise FFmpegError(f"FFmpeg conversion failed: {error_output}")
            
            if not output_path.exists():
                raise FFmpegError(f"Output file was not created: {output_path}")
            
            logger.info(f"Successfully converted video to audio: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise FFmpegError("FFmpeg conversion timed out")
        except Exception as e:
            logger.exception("Video conversion failed")
            raise FFmpegError(f"Video conversion error: {e}") from e

