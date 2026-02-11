"""
Utility Functions Module
========================
Helper functions for the video translation pipeline.

This module provides:
- Video file information extraction (using ffprobe)
- File and directory management
- JSON saving utilities
- Duration formatting
- Low-confidence segment flagging for quality review
- Resume processing detection
- UI helpers (banner, summary printing)
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import shutil       # For finding executables on PATH
import subprocess   # For running ffprobe
import logging
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import timedelta
import config as cfg

# Set up logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# TIME FORMATTING
# ============================================================================
def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Examples:
        format_duration(65) -> "1m 5s"
        format_duration(3665) -> "1h 1m 5s"
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable string like "1h 5m 30s"
    """
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


# ============================================================================
# VIDEO INFORMATION (using ffprobe)
# ============================================================================
def _find_ffprobe() -> str:
    """
    Locate ffprobe executable on the system PATH.
    
    ffprobe is part of the FFmpeg suite and provides fast
    video metadata extraction without decoding.
    
    Raises:
        RuntimeError: If ffprobe is not found
        
    Returns:
        Full path to ffprobe executable
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError(
            "ffprobe not found in PATH. Install ffmpeg from https://ffmpeg.org/download.html"
        )
    return ffprobe


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get video file information using ffprobe.
    
    This is much faster than loading the video with Python libraries
    because ffprobe only reads metadata, not video frames.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        Dictionary with:
        - filename: Name of the video file
        - duration: Duration in seconds
        - duration_formatted: Human-readable duration
        - size_mb: File size in megabytes
        - fps: Frames per second
        - resolution: [width, height] in pixels
        
    Raises:
        FileNotFoundError: If video file doesn't exist
        RuntimeError: If ffprobe fails
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    ffprobe = _find_ffprobe()
    
    # Run ffprobe with JSON output for easy parsing
    cmd = [
        ffprobe,
        "-v", "quiet",              # Suppress log messages
        "-print_format", "json",    # Output as JSON
        "-show_format",             # Include format info
        "-show_streams",            # Include stream info
        str(video_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffprobe timed out while reading video info")

    # Extract format-level information
    fmt = data.get("format", {})
    duration = float(fmt.get("duration", 0))

    # Find video stream for fps and resolution
    fps = 0.0
    width, height = 0, 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            # Parse frame rate (often "30/1" or "29.97")
            r_fps = stream.get("r_frame_rate", "0/1")
            try:
                num, den = r_fps.split("/")
                fps = float(num) / float(den)
            except (ValueError, ZeroDivisionError):
                fps = 0.0
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            break  # Use first video stream

    return {
        "filename": video_path.name,
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "size_mb": video_path.stat().st_size / (1024 * 1024),
        "fps": fps,
        "resolution": [width, height],
    }


# ============================================================================
# FILE OPERATIONS
# ============================================================================
def save_json(data: Any, output_path: str) -> str:
    """
    Save data to a JSON file with pretty formatting.
    
    Uses UTF-8 encoding and preserves Unicode characters.
    
    Args:
        data: Any JSON-serializable Python object
        output_path: Path for the output file
        
    Returns:
        Path to the saved file
    """
    output_path = Path(output_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"JSON saved: {output_path}")
    return str(output_path)


def cleanup_temp_files(file_paths: list, keep_files: bool = False):
    """
    Clean up temporary files created during processing.
    
    Args:
        file_paths: List of file paths to remove
        keep_files: If True, skip deletion (for debugging)
    """
    if keep_files:
        return

    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Removed temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not remove {file_path}: {str(e)}")


def validate_file(file_path: str, extensions: list = None) -> bool:
    """
    Validate that a file exists and has an acceptable extension.
    
    Args:
        file_path: Path to the file to validate
        extensions: List of valid extensions (e.g., [".mp4", ".mkv"])
        
    Returns:
        True if file is valid, False otherwise
    """
    file_path = Path(file_path)

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False

    if extensions and file_path.suffix.lower() not in extensions:
        logger.error(f"Invalid file extension. Expected: {extensions}")
        return False

    return True


def create_output_directory(base_dir: str, video_name: str) -> Path:
    """
    Create a directory for storing processing outputs.
    
    Creates directories recursively if needed.
    
    Args:
        base_dir: Base output directory (e.g., "output")
        video_name: Name of the video (used in folder name)
        
    Returns:
        Path object for the created directory
    """
    output_dir = Path(base_dir) / f"{video_name}_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    return output_dir


# ============================================================================
# UI HELPERS
# ============================================================================
def print_banner():
    """Print application banner with project information."""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║        VIDEO TO PERSIAN TRANSLATOR                      ║
    ║        High-Performance AI Translation Pipeline         ║
    ║                                                          ║
    ║        Author: Amir Aeiny                               ║
    ║        Version: 2.0.0                                   ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_summary(
    video_info: Dict,
    detected_language: str,
    segment_count: int,
    processing_time: float,
    output_files: Dict[str, str]
):
    """
    Print a formatted summary of the processing results.
    
    Called at the end of video processing to show the user
    what was processed and what files were created.
    
    Args:
        video_info: Dictionary from get_video_info()
        detected_language: Language code detected by Whisper
        segment_count: Number of segments transcribed
        processing_time: Total processing time in seconds
        output_files: Dictionary of format -> filepath
    """
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    print(f"Video: {video_info['filename']}")
    print(f"Duration: {video_info['duration_formatted']}")
    print(f"Size: {video_info['size_mb']:.2f} MB")
    print(f"Detected Language: {detected_language}")
    print(f"Segments Processed: {segment_count}")
    print(f"Processing Time: {format_duration(processing_time)}")
    print("\nOutput Files:")
    for format_type, filepath in output_files.items():
        print(f"  - {format_type.upper()}: {Path(filepath).name}")
    print("="*60)


# ============================================================================
# LOW-CONFIDENCE SEGMENT FLAGGING (Quality Review Feature)
# ============================================================================

def flag_low_confidence_segments(
    segments: List[Dict],
    threshold: float = None,
) -> List[Dict]:
    """
    Identify segments with low transcription confidence for review.
    
    Whisper provides word-level probability scores. This function
    identifies segments where the average word confidence is below
    a threshold, indicating potential transcription errors.
    
    Use Case: Export these segments for human review to ensure
    critical translations are accurate.
    
    Args:
        segments: List of segment dicts with "words" containing probabilities
        threshold: Minimum acceptable average probability (default from config)
        
    Returns:
        List of segment dicts that need review, with added:
        - avg_probability: Average word confidence for the segment
        - segment_index: Original position in segment list
    """
    if threshold is None:
        threshold = getattr(cfg, "LOW_CONFIDENCE_THRESHOLD", 0.5)

    flagged: List[Dict] = []
    for idx, seg in enumerate(segments):
        words = seg.get("words", [])
        if not words:
            continue  # Skip segments without word-level data
            
        # Calculate average probability across all words
        probs = [w.get("probability", 1.0) for w in words]
        avg_p = sum(probs) / len(probs)
        
        # Flag if below threshold
        if avg_p < threshold:
            entry = seg.copy()
            entry["avg_probability"] = round(avg_p, 4)
            entry["segment_index"] = idx
            flagged.append(entry)
            
    return flagged


def save_review_list(
    flagged_segments: List[Dict],
    output_path: str,
) -> str:
    """
    Write a human-readable review list for low-confidence segments.
    
    Creates a text file that can be given to a human reviewer
    to check and correct potential transcription/translation errors.
    
    Args:
        flagged_segments: List from flag_low_confidence_segments()
        output_path: Path for the review list file
        
    Returns:
        Path to the created file
    """
    output_path = Path(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("LOW-CONFIDENCE SEGMENTS – REVIEW LIST\n")
        f.write("=" * 60 + "\n\n")
        
        if not flagged_segments:
            f.write("All segments passed the confidence threshold ✓\n")
        
        for seg in flagged_segments:
            # Write timestamp range and confidence score
            f.write(
                f"[{seg['start']:.2f}s – {seg['end']:.2f}s]  "
                f"avg_prob={seg['avg_probability']:.2%}\n"
            )
            # Write translated text
            f.write(f"  Text: {seg['text']}\n")
            # Write original text if available
            if "original_text" in seg:
                f.write(f"  Original: {seg['original_text']}\n")
            f.write("\n")
            
    logger.info(f"Review list saved: {output_path}")
    return str(output_path)


# ============================================================================
# RESUME PROCESSING HELPERS
# ============================================================================

def output_already_exists(video_path: str, output_dir: Path) -> bool:
    """
    Check if output files already exist for a video (for resume support).
    
    When RESUME_PROCESSING is enabled, this function checks if the
    video has already been processed by looking for existing output
    files that are newer than the source video.
    
    Args:
        video_path: Path to the source video file
        output_dir: Directory where outputs would be saved
        
    Returns:
        True if outputs exist and are up-to-date, False otherwise
    """
    video_path = Path(video_path)
    
    # If output directory doesn't exist, definitely need to process
    if not output_dir.exists():
        return False

    # Check for the main output file (Persian SRT)
    srt_file = output_dir / f"{video_path.stem}_persian.srt"
    if not srt_file.exists():
        return False

    # Outputs must be newer than the source video
    # This handles cases where the source video was modified
    return srt_file.stat().st_mtime >= video_path.stat().st_mtime
