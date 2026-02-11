"""
Configuration file for Video Translator
Author: Amir Aeiny

This file contains all configurable settings for the video translation pipeline.
Edit these values to customize behavior without modifying source code.
"""

# ============================================================
# IMPORTS
# ============================================================
import os
import multiprocessing
from pathlib import Path

# ============================================================
# PROJECT PATHS
# These define where the application looks for files
# ============================================================
BASE_DIR = Path(__file__).parent          # Root directory of the project
MODELS_DIR = BASE_DIR / "models"          # Where Whisper models are cached
INPUT_DIR = BASE_DIR / "inputs"           # Default folder for input videos
OUTPUT_DIR = BASE_DIR / "output"          # Where output subtitles are saved

# Create directories if they don't exist (runs on import)
MODELS_DIR.mkdir(exist_ok=True)
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================
# WHISPER MODEL CONFIGURATION
# Controls the speech-to-text engine
# ============================================================
WHISPER_MODEL_SIZE = "large-v3"  # Model size: tiny, base, small, medium, large-v2, large-v3
DEVICE = "cuda"                   # "cuda" for NVIDIA GPU, "cpu" for CPU-only
COMPUTE_TYPE = "float16"          # Precision: "float16" (fast), "int8" (smaller), "int8_float16"

# For CPU-only systems, uncomment these lines:
# DEVICE = "cpu"
# COMPUTE_TYPE = "int8"

# ============================================================
# TRANSLATION CONFIGURATION
# Controls source/target language settings
# ============================================================
TARGET_LANGUAGE = "fa"    # Target language code (fa = Persian/Farsi)
SOURCE_LANGUAGE = "auto"  # Source language ("auto" = detect automatically)

# ============================================================
# SUBTITLE FORMATTING
# Controls how subtitles appear on screen
# ============================================================
MAX_CHARS_PER_CAPTION = 42  # Max characters per line (wraps if longer)
MAX_WORDS_PER_SEGMENT = 10  # Max words per subtitle segment

# ============================================================
# PROCESSING PERFORMANCE
# Tune these based on your hardware
# ============================================================
BATCH_SIZE = 8                                          # GPU batch size (higher = faster, more VRAM)
BEAM_SIZE = 5                                           # Beam search width (higher = more accurate, slower)
NUM_WORKERS = 4                                         # Parallel workers for translation
CPU_THREADS = max(1, multiprocessing.cpu_count() // 2)  # CPU threads (auto-tuned to half of cores)
NUM_WHISPER_WORKERS = max(1, multiprocessing.cpu_count() // 4)  # Whisper internal workers

# ============================================================
# VOICE ACTIVITY DETECTION (VAD)
# Filters out silence and non-speech audio
# ============================================================
VAD_FILTER = True           # Enable VAD filtering (recommended)
VAD_MIN_SILENCE_MS = 500    # Minimum silence duration to split on (milliseconds)
VAD_THRESHOLD = 0.5         # Speech detection sensitivity (0.0-1.0, higher = stricter)

# ============================================================
# AUDIO EXTRACTION
# Settings for extracting audio from video
# ============================================================
AUDIO_CODEC = "pcm_s16le"   # Audio codec (16-bit PCM, high quality)
AUDIO_SAMPLE_RATE = 16000   # Sample rate in Hz (Whisper expects 16kHz)

# ============================================================
# TRANSLATION RETRY SETTINGS
# Handles API failures gracefully
# ============================================================
RETRY_BASE_DELAY = 1.0      # Initial retry delay in seconds
MAX_RETRY_DELAY = 16.0      # Maximum retry delay (caps exponential backoff)
TRANSLATION_RETRIES = 3     # Number of retry attempts per segment
TRANSLATION_CACHE = True    # Cache translations to avoid re-translating duplicates

# ============================================================
# SEGMENT REFLOW
# Improves subtitle timing and readability
# ============================================================
SEGMENT_MIN_DURATION = 0.8  # Merge segments shorter than this (seconds)
SEGMENT_MAX_DURATION = 7.0  # Split segments longer than this (seconds)
ENABLE_SEGMENT_REFLOW = True  # Enable automatic segment merging/splitting

# ============================================================
# QUALITY CONTROL
# Flags uncertain transcriptions for review
# ============================================================
LOW_CONFIDENCE_THRESHOLD = 0.5  # Flag segments with avg word probability below this

# ============================================================
# RESUME / SKIP SETTINGS
# For batch processing efficiency
# ============================================================
RESUME_PROCESSING = True  # Skip videos if output already exists and is up-to-date

# ============================================================
# OUTPUT SETTINGS
# Controls what files are generated
# ============================================================
OUTPUT_FORMATS = ["srt", "txt", "vtt"]  # Enabled output formats
KEEP_AUDIO = False                       # Keep extracted audio file after processing
