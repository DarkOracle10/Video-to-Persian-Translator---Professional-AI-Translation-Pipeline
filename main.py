"""
Video to Persian Translator
===========================
Main execution script for the video translation pipeline.

This script orchestrates the entire translation process:
1. Audio extraction from video (FFmpeg)
2. Speech-to-text transcription (Faster Whisper)
3. Translation to Persian (Google Translate)
4. Subtitle file generation (SRT, VTT, TXT, bilingual)

Usage:
    python main.py                      # Process all videos in inputs/
    python main.py video.mp4            # Process a single video
    python main.py --input-dir /path/   # Process all videos in a directory
    python main.py --help               # Show all options

Author: Amir Aeiny
Version: 2.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import sys
import os

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
    # Set environment variable for subprocess calls
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import time
import argparse
from pathlib import Path
import logging

# Import project modules (from src/ directory)
from src.audio_extractor import AudioExtractor    # FFmpeg-based audio extraction
from src.transcriber import Transcriber            # Faster Whisper transcription
from src.translator import Translator              # Google Translate wrapper
from src.subtitle_generator import SubtitleGenerator  # Multi-format subtitle output
from src.utils import (
    print_banner,                  # ASCII art header
    get_video_info,                # FFprobe video metadata
    validate_file,                 # File existence check
    create_output_directory,       # Output folder creation
    cleanup_temp_files,            # Temp file removal
    save_json,                     # JSON serialization
    print_summary,                 # Processing summary
    flag_low_confidence_segments,  # Quality review flagging
    save_review_list,              # Review list export
    output_already_exists,         # Resume processing check
)

import config  # Project configuration

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# VIDEO TRANSLATOR CLASS
# ============================================================================
class VideoTranslator:
    """
    Main video translation pipeline orchestrator.
    
    This class coordinates all components to process videos:
    - AudioExtractor: Extracts audio track from video
    - Transcriber: Converts speech to text with timestamps
    - Translator: Translates text to Persian
    - SubtitleGenerator: Creates subtitle files in multiple formats
    
    The process() method handles the entire workflow with:
    - Resume support (skip already-processed videos)
    - Segment reflow (merge short, split long segments)
    - Low-confidence flagging (for human review)
    - Multiple output formats
    """

    def __init__(self):
        """
        Initialize all pipeline components with settings from config.
        
        Components are created once and reused for multiple videos,
        which is efficient for batch processing.
        """
        # Audio extractor with configured sample rate (16kHz for Whisper)
        self.audio_extractor = AudioExtractor(sample_rate=config.AUDIO_SAMPLE_RATE)
        
        # Whisper transcriber with GPU/CPU settings from config
        self.transcriber = Transcriber(
            model_size=config.WHISPER_MODEL_SIZE,
            device=config.DEVICE,
            compute_type=config.COMPUTE_TYPE,
            download_root=str(config.MODELS_DIR)
        )
        
        # Persian translator with language settings
        self.translator = Translator(
            target_language=config.TARGET_LANGUAGE,
            source_language=config.SOURCE_LANGUAGE
        )
        
        # Subtitle generator for all output formats
        self.subtitle_generator = SubtitleGenerator()

    def process(
        self,
        video_path: str,
        output_dir: str = None,
        translate: bool = True,
        bilingual: bool = True
    ) -> dict:
        """
        Process a single video through the complete translation pipeline.
        
        Steps:
        1. Validate input and get video metadata
        2. Check for existing outputs (resume support)
        3. Extract audio track from video
        4. Transcribe audio to text segments
        5. Optionally translate to Persian
        6. Generate subtitle files in all formats

        Args:
            video_path: Path to the input video file
            output_dir: Custom output directory (optional)
            translate: Whether to translate to Persian (default True)
            bilingual: Whether to generate bilingual subtitles (default True)

        Returns:
            Dictionary mapping format names to output file paths
            Empty dict if video was skipped (resume mode)
            
        Raises:
            ValueError: If video file is invalid
            Exception: If processing fails
        """
        start_time = time.time()
        temp_files = []  # Track files to clean up

        try:
            # ----- Input Validation -----
            video_path = Path(video_path)
            if not validate_file(video_path, ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']):
                raise ValueError("Invalid video file")

            # Get video metadata using ffprobe
            video_info = get_video_info(str(video_path))
            logger.info(f"Processing video: {video_info['filename']}")
            logger.info(f"Duration: {video_info['duration_formatted']}")

            # ----- Create Output Directory -----
            # Each video gets its own subfolder to avoid collisions
            if output_dir is None:
                output_dir = create_output_directory(
                    str(config.OUTPUT_DIR),
                    video_path.stem
                )
            else:
                output_dir = Path(output_dir) / f"{video_path.stem}_output"
                output_dir.mkdir(parents=True, exist_ok=True)

            # ----- Resume Check -----
            # Skip if outputs already exist and are up-to-date
            if getattr(config, "RESUME_PROCESSING", False):
                if output_already_exists(str(video_path), output_dir):
                    logger.info(
                        f"⏩ Skipping {video_path.name} – outputs already exist and are up-to-date"
                    )
                    return {}

            # ----- STEP 1: Extract Audio -----
            logger.info("\n[STEP 1/4] Extracting audio from video...")
            audio_path = self.audio_extractor.extract(
                str(video_path),
                str(output_dir / f"{video_path.stem}_audio.wav")
            )
            temp_files.append(audio_path)  # Mark for cleanup

            # ----- STEP 2: Transcribe Audio -----
            logger.info("\n[STEP 2/4] Transcribing audio to text...")
            segments, detected_language = self.transcriber.transcribe(
                audio_path,
                language=None,  # Auto-detect language
                beam_size=config.BEAM_SIZE,
                batch_size=config.BATCH_SIZE
            )

            # ----- Optional Segment Reflow -----
            # Merge very short segments, split very long ones
            if getattr(config, "ENABLE_SEGMENT_REFLOW", True):
                logger.info("Reflowing segments (merge short / split long)...")
                reflow_fn = getattr(SubtitleGenerator, "reflow_segments", None)
                if callable(reflow_fn):
                    segments = reflow_fn(segments)

            # ----- Low-Confidence Flagging -----
            # Identify segments that may have transcription errors
            flagged = flag_low_confidence_segments(segments)
            if flagged:
                logger.warning(
                    f"⚠ {len(flagged)} segment(s) below confidence threshold – "
                    "see review list in output folder"
                )
                # Save review list for human verification
                review_path = output_dir / f"{video_path.stem}_review.txt"
                save_review_list(flagged, str(review_path))

            # ----- Save Original Transcription -----
            # Generate subtitle files for the original (untranslated) text
            original_output = output_dir / f"{video_path.stem}_original"
            self.subtitle_generator.generate_all_formats(
                segments,
                str(original_output),
                include_bilingual=False  # No bilingual for original
            )

            output_files = {}

            if translate:
                # ----- STEP 3: Translate to Persian -----
                logger.info("\n[STEP 3/4] Translating to Persian...")
                translated_segments = self.translator.translate_segments(
                    segments,
                    max_workers=config.NUM_WORKERS  # Parallel translation
                )

                # Reflow translated segments too (translation may change length)
                if getattr(config, "ENABLE_SEGMENT_REFLOW", True):
                    reflow_fn = getattr(SubtitleGenerator, "reflow_segments", None)
                    if callable(reflow_fn):
                        translated_segments = reflow_fn(translated_segments)

                # ----- STEP 4: Generate Subtitle Files -----
                logger.info("\n[STEP 4/4] Generating subtitle files...")
                persian_output = output_dir / f"{video_path.stem}_persian"
                output_files = self.subtitle_generator.generate_all_formats(
                    translated_segments,
                    str(persian_output),
                    include_bilingual=bilingual  # Include English + Persian
                )

                # Save segments as JSON for later use or analysis
                json_path = output_dir / f"{video_path.stem}_segments.json"
                save_json({
                    "video_info": video_info,
                    "detected_language": detected_language,
                    "segments": translated_segments
                }, str(json_path))
                output_files["json"] = str(json_path)
            else:
                # ----- Transcription Only (No Translation) -----
                logger.info("\n[STEP 3/3] Generating subtitle files...")
                output_base = output_dir / f"{video_path.stem}_transcribed"
                output_files = self.subtitle_generator.generate_all_formats(
                    segments,
                    str(output_base),
                    include_bilingual=False
                )

            # ----- Cleanup -----
            # Remove temporary audio file unless configured to keep it
            if not config.KEEP_AUDIO:
                cleanup_temp_files(temp_files)

            # ----- Print Summary -----
            processing_time = time.time() - start_time
            print_summary(
                video_info,
                detected_language,
                len(segments),
                processing_time,
                output_files
            )

            return output_files

        except Exception as e:
            logger.error(f"Error during processing: {str(e)}")
            raise


# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================
def main():
    """
    Main entry point for command-line execution.
    
    Parses command-line arguments and processes video(s).
    Supports single file, directory, or batch processing.
    """
    print_banner()

    # Set up argument parser with all options
    parser = argparse.ArgumentParser(
        description="Translate video audio to Persian with high-quality subtitles"
    )
    
    # Positional argument: video file or directory
    parser.add_argument(
        "video",
        type=str,
        nargs="?",
        default=None,
        help="Path to input video file or directory (default: inputs folder)"
    )
    
    # Alternative: specify input directory explicitly
    parser.add_argument(
        "--input-dir",
        type=str,
        default=None,
        help="Directory containing input videos (overrides positional argument)"
    )
    
    # Output directory
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory (default: auto-generated)"
    )
    
    # Skip translation (transcription only)
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Only transcribe, don't translate"
    )
    
    # Skip bilingual output
    parser.add_argument(
        "--no-bilingual",
        action="store_true",
        help="Don't generate bilingual subtitles"
    )
    # Whisper model selection
    parser.add_argument(
        "--model",
        type=str,
        default=config.WHISPER_MODEL_SIZE,
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size"
    )
    
    # Device selection (GPU vs CPU)
    parser.add_argument(
        "--device",
        type=str,
        default=config.DEVICE,
        choices=["cuda", "cpu"],
        help="Device to use (cuda for GPU, cpu for CPU)"
    )

    args = parser.parse_args()

    # ----- Apply Command-Line Overrides -----
    # Override config settings with command-line arguments
    config.WHISPER_MODEL_SIZE = args.model
    config.DEVICE = args.device
    
    # Adjust compute type based on device
    if args.device == "cpu":
        config.COMPUTE_TYPE = "int8"  # CPU only supports int8
    if args.device == "cuda" and args.model in ["large-v2", "large-v3"]:
        config.COMPUTE_TYPE = "int8_float16"  # Best for large models on GPU
        config.BATCH_SIZE = min(config.BATCH_SIZE, 4)  # Limit batch size for VRAM

    # ----- Initialize Pipeline -----
    translator = VideoTranslator()

    # Supported video file extensions
    supported_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}

    def collect_videos(input_path: str) -> list:
        """
        Collect video files from a file or directory path.
        
        Args:
            input_path: Path to file or directory
            
        Returns:
            List of Path objects for video files
        """
        if input_path is None:
            input_path = str(config.INPUT_DIR)

        path = Path(input_path)

        # If it's a directory, find all video files
        if path.is_dir():
            videos = [p for p in path.iterdir() if p.suffix.lower() in supported_extensions]
            return sorted(videos)

        # If it's a single file, return it in a list
        if path.is_file():
            return [path]

        raise FileNotFoundError(f"Input path not found: {path}")

    # ----- Process Videos -----
    try:
        # Determine input path from arguments
        input_path = args.input_dir if args.input_dir else args.video
        video_files = collect_videos(input_path)

        if not video_files:
            raise ValueError("No video files found in the input folder.")

        # Track processing statistics
        processed = 0
        skipped = 0

        # Process each video file
        for video_file in video_files:
            output_files = translator.process(
                str(video_file),
                output_dir=args.output,
                translate=not args.no_translate,
                bilingual=not args.no_bilingual
            )
            # Empty dict means video was skipped (resume mode)
            if output_files:
                processed += 1
            else:
                skipped += 1

        # Print final summary
        print(f"\n✅ Processing completed: {processed} video(s) done, {skipped} skipped.")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        sys.exit(1)


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    main()
