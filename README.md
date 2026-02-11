# 🎬 Video to Persian Translator

[![CI Pipeline](https://github.com/your-username/video-to-persian-translator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/video-to-persian-translator/actions)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A high-performance AI pipeline that extracts audio from videos, transcribes speech using OpenAI Whisper, translates to Persian, and generates professional subtitles.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎙️ **Audio Extraction** | Fast ffmpeg-based extraction (no Python decoding overhead) |
| 🗣️ **Speech-to-Text** | State-of-the-art Faster Whisper with GPU acceleration |
| 🌍 **Auto Language Detection** | Automatically detects source language |
| 🇮🇷 **Persian Translation** | High-quality Google Translate with caching & retry |
| 📝 **Multiple Outputs** | SRT, VTT, TXT, bilingual subtitles, clean Persian prose |
| ⚡ **Segment Reflow** | Merges short / splits long subtitles for readability |
| 🔍 **Quality Checks** | Flags low-confidence segments for manual review |
| 🔄 **Resume Support** | Skips already-processed videos in batch mode |
| 🎨 **RTL Support** | Optional Persian text shaping for correct display |

---

## 📦 Installation

### Prerequisites

- **Python 3.10+**
- **FFmpeg** (must be in PATH)
- **CUDA** (optional, for GPU acceleration)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-username/video-to-persian-translator.git
cd video-to-persian-translator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# (Optional) Install RTL shaping for better Persian display
pip install arabic-reshaper python-bidi
```

### FFmpeg Installation

| OS | Command |
|----|---------|
| **Windows** | `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html) |
| **macOS** | `brew install ffmpeg` |
| **Ubuntu** | `sudo apt install ffmpeg` |

---

## 🚀 Usage

### Single Video

```bash
python main.py path/to/video.mp4
```

### Batch Processing (folder)

```bash
python main.py --input-dir path/to/videos/
```

### Options

```bash
python main.py video.mp4 [OPTIONS]

Options:
  -o, --output DIR      Output directory (default: auto-generated)
  --no-translate        Only transcribe, don't translate
  --no-bilingual        Don't generate bilingual subtitles
  --model MODEL         Whisper model: tiny, base, small, medium, large-v2, large-v3
  --device DEVICE       cuda (GPU) or cpu
```

### Examples

```bash
# Use smaller model for faster processing
python main.py video.mp4 --model medium

# CPU-only processing
python main.py video.mp4 --device cpu

# Transcribe only (no translation)
python main.py video.mp4 --no-translate

# Custom output directory
python main.py video.mp4 -o ./my-subtitles/
```

---

## 📁 Output Files

For each video `example.mp4`, the pipeline generates:

| File | Description |
|------|-------------|
| `example_original.srt` | Original language subtitles |
| `example_persian.srt` | Persian translated subtitles |
| `example_persian_bilingual.srt` | Side-by-side original + Persian |
| `example_persian_clean.txt` | Clean Persian prose (paragraphed) |
| `example_persian.vtt` | WebVTT format for web players |
| `example_segments.json` | Full data with timestamps & confidence |
| `example_review.txt` | Low-confidence segments for manual review |

---

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Model settings
WHISPER_MODEL_SIZE = "large-v3"  # Model accuracy vs speed
DEVICE = "cuda"                   # GPU acceleration
COMPUTE_TYPE = "float16"          # Precision (float16/int8)

# Subtitle settings
MAX_CHARS_PER_CAPTION = 42        # Line wrapping width
SEGMENT_MIN_DURATION = 0.8        # Merge segments shorter than this
SEGMENT_MAX_DURATION = 7.0        # Split segments longer than this

# Quality settings
LOW_CONFIDENCE_THRESHOLD = 0.5    # Flag uncertain transcriptions

# Performance
BATCH_SIZE = 8                    # GPU memory usage
NUM_WORKERS = 4                   # Parallel translation threads
RESUME_PROCESSING = True          # Skip already-processed videos
```

---

## 🏗️ Project Structure

```
video-to-persian-translator/
├── main.py                 # Entry point & CLI
├── config.py               # All configuration settings
├── requirements.txt        # Python dependencies
├── src/
│   ├── __init__.py
│   ├── audio_extractor.py  # FFmpeg audio extraction
│   ├── transcriber.py      # Whisper speech-to-text
│   ├── translator.py       # Google Translate with caching
│   ├── subtitle_generator.py # SRT/VTT/TXT generation
│   └── utils.py            # Helper functions
├── inputs/                 # Place videos here
├── output/                 # Generated subtitles
├── models/                 # Cached Whisper models
└── .github/
    └── workflows/
        └── ci.yml          # CI/CD pipeline
```

---

## 🧪 Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

---

## 📊 Performance

| Video Length | Model | Device | Processing Time |
|--------------|-------|--------|-----------------|
| 3 min | large-v3 | RTX 3080 | ~25 sec |
| 10 min | large-v3 | RTX 3080 | ~1.5 min |
| 60 min | large-v3 | RTX 3080 | ~8 min |
| 10 min | large-v3 | CPU | ~15 min |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) - Speech recognition
- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) - Optimized inference
- [deep-translator](https://github.com/nidhaloff/deep-translator) - Translation API
- [FFmpeg](https://ffmpeg.org/) - Audio/video processing

---

## 👤 Author

**Amir Aeiny**

- GitHub: [@DarkOracle10](https://github.com/DarkOracle10)

---

<p align="center">Made with ❤️ for the Persian-speaking community</p>
