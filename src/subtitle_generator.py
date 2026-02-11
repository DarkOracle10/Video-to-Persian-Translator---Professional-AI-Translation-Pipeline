"""
Subtitle Generator Module
=========================
Generates subtitle files in multiple formats (SRT, VTT, TXT) with advanced
features for Persian text output.

Key Features:
- Multiple output formats: SRT, VTT, TXT, bilingual SRT, clean Persian text
- Automatic line wrapping for readability on screen
- Optional RTL shaping for proper Persian/Arabic display
- Segment reflow: merges short segments, splits long ones
- UTF-8-sig encoding for RTL editor compatibility

Output Formats:
- SRT: SubRip format (most common)
- VTT: WebVTT format (web-friendly)
- TXT: Plain text with timestamps
- Bilingual SRT: Original + translation side by side
- Clean Persian: Properly paragraphed prose without timestamps
"""

# ============================================================================
# IMPORTS
# ============================================================================
import re
import textwrap
from typing import List, Dict
from pathlib import Path
import logging
import config as cfg

# ============================================================================
# OPTIONAL RTL SHAPING LIBRARIES
# ============================================================================
# These libraries are optional but recommended for proper Persian display.
# arabic_reshaper: Connects Persian/Arabic letters properly
# python-bidi: Handles bidirectional text (RTL + LTR mixed)
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _HAS_RTL = True
except ImportError:
    _HAS_RTL = False

# Set up logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SUBTITLE GENERATOR CLASS
# ============================================================================
class SubtitleGenerator:
    """
    Generates subtitle files in multiple formats with Persian text support.
    
    Features:
    - Automatic line wrapping to prevent text overflow
    - RTL shaping for proper Persian character rendering
    - Segment reflow for optimal timing
    """

    def __init__(self):
        """
        Initialize the subtitle generator.
        
        Reads MAX_CHARS_PER_CAPTION from config to control line length.
        Logs whether RTL shaping is available.
        """
        # Maximum characters per line before wrapping
        self.max_chars = getattr(cfg, "MAX_CHARS_PER_CAPTION", 42)
        
        # Log RTL shaping status for debugging
        if _HAS_RTL:
            logger.info("Persian RTL shaping enabled (arabic_reshaper + python-bidi)")
        else:
            logger.info(
                "RTL shaping libs not installed – subtitles will be plain Unicode. "
                "Install arabic-reshaper and python-bidi for shaped output."
            )

    # ------------------------------------------------------------------ #
    #  RTL Helpers - Persian/Arabic Text Shaping
    # ------------------------------------------------------------------ #
    @staticmethod
    def _shape_persian(text: str) -> str:
        """
        Apply Arabic/Persian reshaping and bidirectional algorithm.
        
        Persian letters have different forms depending on position in word.
        This method ensures letters are connected properly and RTL display
        is correct even in environments that don't handle it natively.
        
        Args:
            text: Raw Persian text
            
        Returns:
            Reshaped text ready for display, or original if libs unavailable
        """
        if not _HAS_RTL:
            return text  # Graceful degradation
        try:
            # Step 1: Reshape letters (connect them properly)
            reshaped = arabic_reshaper.reshape(text)
            # Step 2: Apply bidi algorithm for proper ordering
            return get_display(reshaped)
        except Exception:
            return text  # Return original on any error

    # ------------------------------------------------------------------ #
    #  Line Wrapping
    # ------------------------------------------------------------------ #
    def _wrap_text(self, text: str) -> str:
        """
        Wrap subtitle text to fit within max_chars per line.
        
        Long subtitles are hard to read on screen. This method
        splits text into multiple lines, each within the limit.
        
        Args:
            text: Subtitle text to wrap
            
        Returns:
            Text with newlines inserted for wrapping
        """
        if len(text) <= self.max_chars:
            return text  # No wrapping needed
        
        # textwrap.wrap handles word boundaries properly
        lines = textwrap.wrap(text, width=self.max_chars)
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Segment Reflow (Merge Short / Split Long Segments)
    # ------------------------------------------------------------------ #
    @staticmethod
    def reflow_segments(
        segments: List[Dict],
        min_dur: float = None,
        max_dur: float = None,
    ) -> List[Dict]:
        """
        Optimize segment timing by merging short and splitting long segments.
        
        Problems this solves:
        - Very short segments (<1s) flash by too quickly to read
        - Very long segments (>7s) show too much text at once
        
        Solution:
        - Pass 1: Merge segments shorter than min_dur with their neighbor
        - Pass 2: Split segments longer than max_dur at punctuation marks

        Args:
            segments: Original segment list from transcriber
            min_dur: Merge segments shorter than this (default from config)
            max_dur: Split segments longer than this (default from config)

        Returns:
            Reflowed segment list with optimized timing
        """
        # Get thresholds from config if not provided
        if min_dur is None:
            min_dur = getattr(cfg, "SEGMENT_MIN_DURATION", 0.8)
        if max_dur is None:
            max_dur = getattr(cfg, "SEGMENT_MAX_DURATION", 7.0)

        # ----- Pass 1: Merge short segments with their predecessor -----
        merged: List[Dict] = []
        for seg in segments:
            dur = seg["end"] - seg["start"]
            
            # If this segment is too short and we have a previous one, merge
            if merged and dur < min_dur:
                prev = merged[-1]
                # Extend previous segment to cover this one
                prev["end"] = seg["end"]
                prev["text"] = prev["text"] + " " + seg["text"]
                
                # Also merge original text if present (for bilingual output)
                if "original_text" in prev and "original_text" in seg:
                    prev["original_text"] = (
                        prev["original_text"] + " " + seg["original_text"]
                    )
                
                # Merge word-level timing if present
                if "words" in prev and "words" in seg:
                    prev["words"] = prev.get("words", []) + seg.get("words", [])
            else:
                # Keep segment as-is
                merged.append(seg.copy())

        # ----- Pass 2: Split long segments at punctuation -----
        result: List[Dict] = []
        # Regex to split at sentence-ending punctuation (English and Persian)
        _split_re = re.compile(r"(?<=[.!?،؛:;])\s+")

        for seg in merged:
            dur = seg["end"] - seg["start"]
            
            # If segment is within limit, keep it
            if dur <= max_dur:
                result.append(seg)
                continue

            # Try to split at punctuation
            parts = _split_re.split(seg["text"])
            if len(parts) <= 1:
                # No good split point found, keep as-is
                result.append(seg)
                continue

            # Distribute time proportionally by character count
            # Longer text parts get more time
            total_chars = max(sum(len(p) for p in parts), 1)  # Avoid division by zero
            t = seg["start"]  # Current time position
            
            for part_text in parts:
                # Calculate duration fraction based on character count
                frac = len(part_text) / total_chars
                part_dur = dur * frac
                
                # Create new segment for this part
                new_seg = seg.copy()
                new_seg["start"] = t
                new_seg["end"] = t + part_dur
                new_seg["text"] = part_text.strip()
                if "original_text" in seg:
                    new_seg["original_text"] = part_text.strip()
                new_seg.pop("words", None)  # Word timing no longer valid after split
                result.append(new_seg)
                
                t += part_dur  # Move to next time position

        return result

    # ------------------------------------------------------------------ #
    #  Timestamp Formatting
    # ------------------------------------------------------------------ #
    @staticmethod
    def format_timestamp(seconds: float, format_type: str = "srt") -> str:
        """
        Format seconds into subtitle timestamp format.
        
        SRT uses comma for milliseconds: 00:01:23,456
        VTT uses period for milliseconds: 00:01:23.456

        Args:
            seconds: Time in seconds (float)
            format_type: "srt" or "vtt"

        Returns:
            Formatted timestamp string (HH:MM:SS,mmm or HH:MM:SS.mmm)
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        if format_type == "srt":
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
        else:  # vtt
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    # ------------------------------------------------------------------ #
    #  SRT Generation
    # ------------------------------------------------------------------ #
    def generate_srt(self, segments: List[Dict], output_path: str) -> str:
        """
        Generate SRT (SubRip) subtitle file.
        
        SRT is the most widely supported subtitle format.
        Format:
            1
            00:00:01,000 --> 00:00:04,000
            Subtitle text here

        Args:
            segments: List of segments with start, end, and text
            output_path: Full path for output .srt file

        Returns:
            Path to the generated file
        """
        output_path = Path(output_path)
        logger.info(f"Generating SRT file: {output_path.name}")

        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self.format_timestamp(segment["start"], "srt")
                end_time = self.format_timestamp(segment["end"], "srt")
                # Apply wrapping and RTL shaping
                text = self._wrap_text(self._shape_persian(segment["text"].strip()))

                # Write SRT entry: index, timestamps, text, blank line
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n")
                f.write("\n")

        logger.info(f"SRT file created: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------ #
    #  VTT (WebVTT) Generation
    # ------------------------------------------------------------------ #
    def generate_vtt(self, segments: List[Dict], output_path: str) -> str:
        """
        Generate VTT (WebVTT) subtitle file.
        
        WebVTT is the standard for HTML5 video subtitles.
        Similar to SRT but starts with "WEBVTT" header.

        Args:
            segments: List of segments with start, end, and text
            output_path: Full path for output .vtt file

        Returns:
            Path to the generated file
        """
        output_path = Path(output_path)
        logger.info(f"Generating VTT file: {output_path.name}")

        with open(output_path, "w", encoding="utf-8") as f:
            # VTT requires this header
            f.write("WEBVTT\n\n")

            for i, segment in enumerate(segments, 1):
                start_time = self.format_timestamp(segment["start"], "vtt")
                end_time = self.format_timestamp(segment["end"], "vtt")
                text = self._wrap_text(self._shape_persian(segment["text"].strip()))

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n")
                f.write("\n")

        logger.info(f"VTT file created: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------ #
    #  Plain Text Generation
    # ------------------------------------------------------------------ #
    def generate_txt(self, segments: List[Dict], output_path: str, include_timestamps: bool = True) -> str:
        """
        Generate plain text transcript file.
        
        Useful for reading or editing the transcript outside of video.

        Args:
            segments: List of segments with start, end, and text
            output_path: Full path for output .txt file
            include_timestamps: Whether to include time markers

        Returns:
            Path to the generated file
        """
        output_path = Path(output_path)
        logger.info(f"Generating TXT file: {output_path.name}")

        with open(output_path, "w", encoding="utf-8") as f:
            if include_timestamps:
                # Format: [00:00:01,000 --> 00:00:04,000]\nText
                for segment in segments:
                    start_time = self.format_timestamp(segment["start"], "srt")
                    end_time = self.format_timestamp(segment["end"], "srt")
                    text = self._wrap_text(self._shape_persian(segment["text"].strip()))

                    f.write(f"[{start_time} --> {end_time}]\n")
                    f.write(f"{text}\n\n")
            else:
                # Just the text, one segment per paragraph
                for segment in segments:
                    text = self._wrap_text(self._shape_persian(segment["text"].strip()))
                    f.write(f"{text}\n\n")

        logger.info(f"TXT file created: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------ #
    #  Bilingual SRT Generation
    # ------------------------------------------------------------------ #
    def generate_bilingual_srt(
        self, 
        segments: List[Dict], 
        output_path: str,
        include_original: bool = True
    ) -> str:
        """
        Generate bilingual SRT file with original and translated text.
        
        Useful for language learning or reviewing translations.
        Shows original text (e.g., English) above Persian translation.

        Args:
            segments: List of segments with "text" (translated) and "original_text"
            output_path: Full path for output .srt file
            include_original: Whether to include the source text

        Returns:
            Path to the generated file
        """
        output_path = Path(output_path)
        logger.info(f"Generating bilingual SRT file: {output_path.name}")

        with open(output_path, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start_time = self.format_timestamp(segment["start"], "srt")
                end_time = self.format_timestamp(segment["end"], "srt")
                
                # Apply RTL shaping to Persian translation
                translated_text = self._wrap_text(
                    self._shape_persian(segment["text"].strip())
                )

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")

                # Write original (source language) on first line, translation on second
                if include_original and "original_text" in segment:
                    original_text = segment["original_text"].strip()
                    f.write(f"{original_text}\n")
                    f.write(f"{translated_text}\n")
                else:
                    f.write(f"{translated_text}\n")

                f.write("\n")

        logger.info(f"Bilingual SRT file created: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------ #
    #  Clean Persian Text Generation (Prose Format)
    # ------------------------------------------------------------------ #
    def generate_clean_persian_text(
        self,
        segments: List[Dict],
        output_path: str,
        sentences_per_paragraph: int = 3,
    ) -> str:
        """
        Generate a clean, readable Persian text document with proper paragraphing.
        
        This creates a prose document suitable for reading, publishing,
        or further editing. Unlike subtitle files, this has no timestamps
        and flows naturally as paragraphs.

        Features:
        - No timestamps - pure text
        - Sentences grouped into readable paragraphs
        - Multiple spaces collapsed into one
        - UTF-8 BOM for better RTL editor support
        - RTL shaping applied if available

        Args:
            segments: List of translated segments with "text" key
            output_path: Full path for output .txt file
            sentences_per_paragraph: Number of sentences per paragraph (default 3)

        Returns:
            Path to the generated file
        """
        import re
        output_path = Path(output_path)
        logger.info(f"Generating clean Persian text: {output_path.name}")

        # Step 1: Collect all translated text from segments
        raw_sentences: List[str] = []
        for seg in segments:
            text = seg["text"].strip()
            if text:
                raw_sentences.append(text)

        # Step 2: Join into one continuous block
        full_text = " ".join(raw_sentences)

        # Step 3: Normalize whitespace (collapse multiple spaces)
        full_text = re.sub(r"\s+", " ", full_text)

        # Step 4: Split at sentence boundaries
        # Handles both English (.!?) and Persian (؟) punctuation
        sentence_pattern = re.compile(r"(?<=[.!?؟])\s+")
        sentences = sentence_pattern.split(full_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Step 5: Group sentences into paragraphs
        paragraphs: List[str] = []
        for i in range(0, len(sentences), sentences_per_paragraph):
            para = " ".join(sentences[i : i + sentences_per_paragraph])
            # Apply RTL shaping for proper display
            para = self._shape_persian(para)
            paragraphs.append(para)

        # Step 6: Write file with UTF-8 BOM (helps RTL editors like Notepad)
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write("\n\n".join(paragraphs))
            f.write("\n")

        logger.info(f"Clean Persian text created: {output_path}")
        return str(output_path)

    # ------------------------------------------------------------------ #
    #  Generate All Formats at Once
    # ------------------------------------------------------------------ #
    def generate_all_formats(
        self,
        segments: List[Dict],
        base_output_path: str,
        include_bilingual: bool = True
    ) -> Dict[str, str]:
        """
        Generate all subtitle formats in one call.
        
        Convenience method that creates SRT, VTT, TXT, and optionally
        bilingual SRT and clean Persian text.

        Args:
            segments: List of segment dictionaries
            base_output_path: Base path without extension (e.g., "output/video_persian")
            include_bilingual: Generate bilingual formats if original_text exists

        Returns:
            Dictionary mapping format name to file path:
            {"srt": "...", "vtt": "...", "txt": "...", "bilingual_srt": "...", "clean_persian": "..."}
        """
        base_path = Path(base_output_path)
        results = {}

        # Always generate these three basic formats
        results["srt"] = self.generate_srt(segments, f"{base_path}.srt")
        results["vtt"] = self.generate_vtt(segments, f"{base_path}.vtt")
        results["txt"] = self.generate_txt(segments, f"{base_path}.txt")

        # Generate bilingual and clean Persian if we have original text
        if include_bilingual and any("original_text" in seg for seg in segments):
            results["bilingual_srt"] = self.generate_bilingual_srt(
                segments, 
                f"{base_path}_bilingual.srt"
            )
            # Clean Persian prose document (no timestamps)
            results["clean_persian"] = self.generate_clean_persian_text(
                segments,
                f"{base_path}_clean.txt"
            )

        return results
