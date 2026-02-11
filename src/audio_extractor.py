"""
Audio Extractor Module
Extracts audio from video files using ffmpeg directly for speed and reliability.

This module uses FFmpeg subprocess calls instead of Python libraries like MoviePy
because it's 5-10x faster and doesn't require decoding video frames.
"""

# ============================================================
# IMPORTS
# ============================================================
import os                    # File path operations
import shutil                # Finding executables in PATH
import subprocess            # Running FFmpeg as external process
from pathlib import Path     # Cross-platform path handling
from typing import Optional  # Type hints for optional parameters
import logging               # Logging status and errors

# Configure module-level logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AudioExtractor:
    """
    Extracts audio from video files with high quality using ffmpeg.
    
    This class wraps FFmpeg commands to extract mono 16kHz WAV audio,
    which is the optimal format for Whisper speech recognition.
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize the audio extractor.
        
        Args:
            sample_rate: Output audio sample rate in Hz (default 16000 for Whisper)
        """
        self.sample_rate = sample_rate
        # Find ffmpeg binary on system PATH during initialization
        self._ffmpeg = self._find_ffmpeg()

    @staticmethod
    def _find_ffmpeg() -> str:
        """
        Locate the ffmpeg binary on the system PATH.
        
        Returns:
            Path to ffmpeg executable
            
        Raises:
            RuntimeError: If ffmpeg is not found in PATH
        """
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise RuntimeError(
                "ffmpeg not found in PATH. Install it from https://ffmpeg.org/download.html"
            )
        return ffmpeg

    def extract(self, video_path: str, output_audio_path: Optional[str] = None) -> str:
        """
        Extract audio from video file using ffmpeg subprocess.
        
        This method runs FFmpeg with optimized settings for speech recognition:
        - Mono audio (single channel)
        - 16kHz sample rate (Whisper's expected input)
        - 16-bit PCM WAV format (lossless)

        Args:
            video_path: Path to input video file
            output_audio_path: Path for output audio file (optional, auto-generated if not provided)

        Returns:
            Path to extracted audio file
            
        Raises:
            FileNotFoundError: If video file doesn't exist
            RuntimeError: If ffmpeg fails or times out
        """
        # Validate input file exists
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        video_path = Path(video_path)

        # Generate output path if not provided
        if output_audio_path is None:
            output_audio_path = video_path.parent / f"{video_path.stem}_audio.wav"
        else:
            output_audio_path = Path(output_audio_path)

        logger.info(f"Extracting audio from: {video_path.name}")

        # Build FFmpeg command with optimal settings for speech recognition
        cmd = [
            self._ffmpeg,
            "-i", str(video_path),          # Input file
            "-vn",                          # No video output (audio only)
            "-acodec", "pcm_s16le",         # 16-bit PCM codec (lossless)
            "-ar", str(self.sample_rate),   # Target sample rate (16kHz)
            "-ac", "1",                     # Mono (single channel)
            "-y",                           # Overwrite output without asking
            str(output_audio_path),
        ]

        # Execute FFmpeg with timeout protection
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600  # 10 minute timeout
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio extraction timed out after 10 minutes")

        # Verify output file was created
        if not output_audio_path.exists():
            raise RuntimeError("ffmpeg completed but output file was not created")

        logger.info(f"Audio extracted successfully: {output_audio_path.name}")
        return str(output_audio_path)
