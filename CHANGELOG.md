# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-02-10

### Added
- **Clean Persian Text Output**: New `_clean.txt` file with proper paragraphing and RTL support
- **Segment Reflow**: Automatically merge short segments and split long ones for better readability
- **Low-Confidence Flagging**: Segments with low transcription confidence are flagged in a `_review.txt` file
- **Translation Caching**: Identical text segments are cached to avoid redundant API calls
- **Exponential Backoff**: Translation retries use exponential backoff to handle rate limits gracefully
- **Resume Processing**: Skip videos that have already been processed (configurable)
- **RTL Shaping Support**: Optional arabic-reshaper and python-bidi integration for correct Persian display
- **Configurable VAD**: Voice Activity Detection parameters now configurable in `config.py`
- **Auto CPU Tuning**: Thread counts automatically tuned based on system CPU cores

### Changed
- **Audio Extraction**: Replaced MoviePy with direct FFmpeg subprocess for 5-10x faster extraction
- **Video Info**: Replaced MoviePy with FFprobe for instant metadata retrieval
- **Removed MoviePy Dependency**: No longer required, reducing installation size
- **Multi-Video Handling**: Each video now gets its own output subdirectory to prevent collisions
- **Line Wrapping**: Subtitle lines now respect `MAX_CHARS_PER_CAPTION` setting

### Fixed
- **translate_batch Bug**: Fixed undefined `self.translator` reference
- **Hardcoded Threading**: Removed hardcoded thread counts, now uses config values
- **Memory Leaks**: Proper cleanup of audio/video handles

### Security
- Added `.gitignore` to exclude sensitive files and large models

## [1.0.0] - 2026-01-15

### Added
- Initial release
- Audio extraction from video files
- Speech-to-text using Faster Whisper
- Translation to Persian using Google Translate
- SRT, VTT, TXT subtitle generation
- Bilingual subtitle support
- GPU (CUDA) and CPU support
- Batch processing of multiple videos
- Command-line interface

---

## Upgrade Guide

### From 1.0.0 to 2.0.0

1. **MoviePy no longer required**: You can uninstall it if not used elsewhere
   ```bash
   pip uninstall moviepy
   ```

2. **FFmpeg is now required**: Ensure FFmpeg is installed and in PATH

3. **New config options**: Review `config.py` for new settings like:
   - `RESUME_PROCESSING`
   - `SEGMENT_MIN_DURATION` / `SEGMENT_MAX_DURATION`
   - `LOW_CONFIDENCE_THRESHOLD`
   - `TRANSLATION_CACHE`

4. **New output files**: Expect additional output files:
   - `*_clean.txt` (clean Persian prose)
   - `*_review.txt` (if low-confidence segments exist)
