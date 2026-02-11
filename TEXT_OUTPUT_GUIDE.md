# TEXT OUTPUT FORMATS - VIDEO TO PERSIAN TRANSLATOR

## Available Text File Formats

Your video translator now generates **MULTIPLE TEXT FILE FORMATS** for maximum flexibility:

---

## 📄 OUTPUT FILES GENERATED

### 1. **Persian Translation Outputs**

#### A. `video_name_persian.txt` (with timestamps)
```
[00:00:05,120 --> 00:00:08,450]
این یک مثال از متن ترجمه شده به فارسی است

[00:00:08,450 --> 00:00:12,200]
با برچسب زمانی برای هر بخش
```

#### B. `video_name_persian_plain.txt` (clean text, no timestamps)
```
این یک مثال از متن ترجمه شده به فارسی است با برچسب زمانی برای هر بخش
```

#### C. `video_name_persian_bilingual.txt` (original + Persian)
```
Original: This is an example of translated text to Persian
Persian:  این یک مثال از متن ترجمه شده به فارسی است

Original: With timestamp for each section
Persian:  با برچسب زمانی برای هر بخش
```

#### D. `video_name_persian_bilingual_timestamped.txt` (bilingual + timestamps)
```
[00:00:05,120 --> 00:00:08,450]
Original: This is an example of translated text to Persian
Persian:  این یک مثال از متن ترجمه شده به فارسی است

[00:00:08,450 --> 00:00:12,200]
Original: With timestamp for each section
Persian:  با برچسب زمانی برای هر بخش
```

---

### 2. **Original Language Outputs**

#### E. `video_name_original.txt` (original transcription with timestamps)
```
[00:00:05,120 --> 00:00:08,450]
This is an example of translated text to Persian

[00:00:08,450 --> 00:00:12,200]
With timestamp for each section
```

#### F. `video_name_original_plain.txt` (clean original text)
```
This is an example of translated text to Persian With timestamp for each section
```

---

## 🎯 USAGE EXAMPLES

### Example 1: Process a video and get all text formats
```bash
python main.py my_video.mp4
```

**Output directory structure:**
```
output/my_video_output/
├── my_video_original.txt                      # Original with timestamps
├── my_video_original_plain.txt                # Original clean text
├── my_video_original.srt                      # Original subtitles
├── my_video_original.vtt                      # Original WebVTT
├── my_video_persian.txt                       # Persian with timestamps
├── my_video_persian_plain.txt                 # Persian clean text ⭐
├── my_video_persian_bilingual.txt             # Bilingual text ⭐
├── my_video_persian_bilingual_timestamped.txt # Bilingual + timestamps ⭐
├── my_video_persian.srt                       # Persian subtitles
├── my_video_persian.vtt                       # Persian WebVTT
├── my_video_persian_bilingual.srt             # Bilingual subtitles
└── my_video_segments.json                     # Complete data
```

---

## 🔧 CUSTOMIZATION

### Control text output in config.py:

```python
# Enable/disable text generation
GENERATE_PLAIN_TEXT = True        # Generate plain text files

# Control timestamps in TXT files
TEXT_WITH_TIMESTAMPS = True       # Include timestamps by default

# Specify output formats
OUTPUT_FORMATS = ["srt", "txt", "vtt"]
```

### Or via code:

```python
from src.subtitle_generator import SubtitleGenerator

generator = SubtitleGenerator()

# Generate only plain text (no timestamps)
generator.generate_plain_text(segments, "output.txt")

# Generate text with timestamps
generator.generate_txt(segments, "output_timestamped.txt", include_timestamps=True)

# Generate bilingual text
generator.generate_bilingual_txt(segments, "bilingual.txt", include_timestamps=False)
```

---

## 📊 USE CASES FOR EACH FORMAT

| Format | Best For |
|--------|----------|
| `_plain.txt` | Reading, copying, pasting, simple transcript |
| `_timestamped.txt` | Reference with timing, searching specific moments |
| `_bilingual.txt` | Language learning, comparison, verification |
| `_bilingual_timestamped.txt` | Detailed analysis, subtitle editing |
| `.srt` | Adding subtitles to video players |
| `.vtt` | Web video players (HTML5) |
| `.json` | Programming, data analysis, custom processing |

---

## 💡 TIPS

1. **For quick reading**: Use `*_plain.txt` files
2. **For video editing**: Use `.srt` files
3. **For language learning**: Use `*_bilingual.txt` files
4. **For research**: Use `*_bilingual_timestamped.txt` or `.json`

---

## 🚀 QUICK START

```bash
# Install
pip install -r requirements.txt

# Run
python main.py your_video.mp4

# Check output
ls output/your_video_output/
```

All text files will be in UTF-8 encoding, fully supporting Persian (Farsi) script! 🇮🇷

---

**Created by Amir Aeiny | February 2026**
