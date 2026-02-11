"""
Transcriber Module
High-performance speech-to-text using Faster Whisper.

This module uses the Faster Whisper library which is an optimized implementation
of OpenAI's Whisper model using CTranslate2 for 4x faster inference.
"""

# ============================================================
# IMPORTS
# ============================================================
from faster_whisper import WhisperModel  # Optimized Whisper implementation
from typing import List, Dict, Tuple     # Type hints for function signatures
import logging                           # Logging status and errors
from tqdm import tqdm                    # Progress bar for long operations
import config as cfg                     # Project configuration settings

# Configure module-level logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Transcriber:
    """
    High-performance transcription using Faster Whisper.
    
    This class wraps the Faster Whisper model to provide speech-to-text
    with automatic language detection, word-level timestamps, and
    voice activity detection filtering.
    """

    def __init__(
        self, 
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        download_root: str = None
    ):
        """
        Initialize Faster Whisper transcriber.
        
        The model is loaded once during initialization and reused for all
        transcriptions to avoid repeated loading overhead.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: "cuda" for GPU acceleration or "cpu" for CPU-only
            compute_type: Precision - "float16", "int8", or "int8_float16" for GPU; "int8" for CPU
            download_root: Directory to download/cache models (uses HuggingFace cache if None)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

        # Get threading config from settings (auto-tuned based on CPU cores)
        cpu_threads = getattr(cfg, "CPU_THREADS", 4)
        num_workers = getattr(cfg, "NUM_WHISPER_WORKERS", 4)

        logger.info(f"Loading Whisper model: {model_size} on {device} with {compute_type}")
        logger.info(f"  cpu_threads={cpu_threads}, num_workers={num_workers}")

        # Load the Whisper model (may download on first run)
        try:
            self.model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
                cpu_threads=cpu_threads,      # Number of CPU threads for inference
                num_workers=num_workers       # Number of parallel decoding workers
            )
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: str = None,
        beam_size: int = 5,
        batch_size: int = 8
    ) -> Tuple[List[Dict], str]:
        """
        Transcribe audio file to text with timestamps.
        
        This method processes the audio through Whisper and returns
        a list of segments with start/end times, text, and word-level data.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Source language code (None for auto-detection)
            beam_size: Beam search width (higher = more accurate but slower)
            batch_size: Batch size for GPU (higher = faster but more VRAM)

        Returns:
            Tuple of (segments list, detected language code)
            Each segment contains: start, end, text, words (with probabilities)
        """
        logger.info(f"Transcribing audio: {audio_path}")

        # Get VAD (Voice Activity Detection) config from settings
        vad_filter = getattr(cfg, "VAD_FILTER", True)
        vad_min_silence = getattr(cfg, "VAD_MIN_SILENCE_MS", 500)
        vad_threshold = getattr(cfg, "VAD_THRESHOLD", 0.5)

        try:
            # Try transcription with batch_size (newer faster-whisper versions)
            try:
                segments, info = self.model.transcribe(
                    audio_path,
                    language=language,           # None = auto-detect
                    beam_size=beam_size,         # Higher = better accuracy
                    batch_size=batch_size,       # Higher = faster on GPU
                    word_timestamps=True,        # Get word-level timing
                    vad_filter=vad_filter,       # Filter out silence
                    vad_parameters=dict(
                        min_silence_duration_ms=vad_min_silence,  # Min silence to split
                        threshold=vad_threshold                    # Speech detection threshold
                    )
                )
            except TypeError as e:
                # Fallback for older versions without batch_size parameter
                if "batch_size" not in str(e):
                    raise
                segments, info = self.model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=beam_size,
                    word_timestamps=True,
                    vad_filter=vad_filter,
                    vad_parameters=dict(
                        min_silence_duration_ms=vad_min_silence,
                        threshold=vad_threshold
                    )
                )

            detected_language = info.language
            logger.info(f"Detected language: {detected_language}")
            logger.info(f"Language probability: {info.language_probability:.2f}")

            # Convert segments generator to list with progress bar
            # Each segment contains timing info, text, and word-level details
            segments_list = []
            logger.info("Processing transcription segments...")

            for segment in tqdm(segments, desc="Transcribing", unit="segment"):
                # Build segment dictionary with all relevant data
                segments_list.append({
                    "start": segment.start,          # Start time in seconds
                    "end": segment.end,              # End time in seconds
                    "text": segment.text.strip(),    # Transcribed text
                    "words": [                       # Word-level timing and confidence
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                            "probability": word.probability  # Confidence score (0-1)
                        }
                        for word in (segment.words or [])
                    ]
                })

            logger.info(f"Transcription complete: {len(segments_list)} segments")
            return segments_list, detected_language

        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise

    def get_full_text(self, segments: List[Dict]) -> str:
        """
        Extract full transcript text from segments.
        
        Args:
            segments: List of segment dictionaries
            
        Returns:
            Complete transcript as a single string
        """
        return " ".join(seg["text"] for seg in segments)
