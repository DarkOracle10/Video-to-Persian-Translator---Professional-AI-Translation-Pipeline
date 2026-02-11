# Contributing to Video to Persian Translator

First off, thank you for considering contributing! 🎉

## How Can I Contribute?

### 🐛 Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/DarkOracle10/video-to-persian-translator/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version, OS, GPU info

### 💡 Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the feature and its use case
3. Explain why it would benefit users

### 🔧 Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code, add tests
3. Ensure the test suite passes
4. Make sure your code follows the style guide
5. Issue the pull request!

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/video-to-persian-translator.git
cd video-to-persian-translator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black isort flake8

# Run tests
pytest tests/ -v
```

## Code Style

- Use **Black** for formatting: `black src/ main.py config.py`
- Use **isort** for imports: `isort src/ main.py config.py`
- Follow **PEP 8** guidelines
- Add docstrings to all functions and classes
- Add comments for complex logic

## Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters

Examples:
- `Add speaker diarization feature`
- `Fix translation cache memory leak`
- `Update README with GPU requirements`

## Questions?

Feel free to open an issue with the `question` label!
