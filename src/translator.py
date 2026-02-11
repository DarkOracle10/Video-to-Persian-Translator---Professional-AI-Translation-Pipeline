"""
Translator Module
=================
Translates text to Persian using Google Translate via deep-translator library.

Key Features:
- Thread-safe translation with thread-local translator instances
- MD5-based caching to avoid re-translating duplicate text
- Exponential backoff retry for handling API rate limits
- Parallel translation using ThreadPoolExecutor for speed
- Batch translation with automatic chunking

This module is designed for high-throughput translation of subtitle segments.
"""

# ============================================================================
# IMPORTS
# ============================================================================
from deep_translator import GoogleTranslator  # Free Google Translate API wrapper
from typing import List, Dict
import hashlib       # For generating cache keys
import threading     # For thread-local storage and locks
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time          # For retry delays
import config as cfg # Project configuration

# Set up logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# TRANSLATOR CLASS
# ============================================================================
class Translator:
    """
    Translates text to Persian with optimization and error handling.
    
    Features:
    - Thread-safe: Each thread gets its own GoogleTranslator instance
    - Cached: Duplicate texts are translated only once
    - Resilient: Automatic retry with exponential backoff on failures
    """

    def __init__(self, target_language: str = "fa", source_language: str = "auto"):
        """
        Initialize the translator with language settings.

        Args:
            target_language: ISO 639-1 code for target language
                            'fa' = Persian/Farsi (default)
            source_language: ISO 639-1 code for source language
                            'auto' = Automatic detection (default)
        
        Instance Attributes:
            _local: Thread-local storage for translator instances
            _cache: Dictionary mapping text hashes to translations
            _cache_lock: Lock for thread-safe cache access
        """
        self.target_language = target_language
        self.source_language = source_language
        
        # Thread-local storage ensures each thread has its own translator
        # This prevents race conditions in multi-threaded translation
        self._local = threading.local()
        
        # Translation cache: {md5_hash: translated_text}
        # Dramatically speeds up videos with repeated phrases
        self._cache: Dict[str, str] = {}
        self._cache_lock = threading.Lock()  # Protects cache from race conditions
        self._use_cache = getattr(cfg, "TRANSLATION_CACHE", True)
        
        logger.info(f"Translator initialized: {source_language} -> {target_language}")

    def _get_translator(self) -> GoogleTranslator:
        """
        Get or create a thread-local translator instance.
        
        Each thread gets its own GoogleTranslator to avoid conflicts
        when translating segments in parallel.
        
        Returns:
            GoogleTranslator instance for the current thread
        """
        translator = getattr(self._local, "translator", None)
        if translator is None:
            # First call from this thread - create new translator
            translator = GoogleTranslator(source=self.source_language, target=self.target_language)
            self._local.translator = translator
        return translator

    @staticmethod
    def _text_hash(text: str) -> str:
        """
        Generate a short hash key for caching translations.
        
        Uses MD5 for fast hashing - collision risk is acceptable
        for caching since a collision just means a cache miss.
        
        Args:
            text: Input text to hash
            
        Returns:
            32-character hexadecimal hash string
        """
        return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

    def translate_text(self, text: str, retry_count: int = None) -> str:
        """
        Translate a single text string with exponential-backoff retry.
        
        The exponential backoff strategy handles rate limiting:
        - Attempt 1: immediate
        - Attempt 2: wait 1s
        - Attempt 3: wait 2s
        - Attempt 4: wait 4s (capped at MAX_RETRY_DELAY)

        Args:
            text: Text to translate
            retry_count: Number of retries on failure (default from config)

        Returns:
            Translated text, or original text if all attempts fail
        """
        # Skip empty text
        if not text or not text.strip():
            return text

        stripped = text.strip()

        # Check cache first to avoid redundant API calls
        if self._use_cache:
            key = self._text_hash(stripped)
            with self._cache_lock:  # Thread-safe cache read
                if key in self._cache:
                    return self._cache[key]

        # Get retry settings from config
        if retry_count is None:
            retry_count = getattr(cfg, "TRANSLATION_RETRIES", 3)
        base_delay = getattr(cfg, "RETRY_BASE_DELAY", 1.0)
        max_delay = getattr(cfg, "MAX_RETRY_DELAY", 16.0)

        # Retry loop with exponential backoff
        for attempt in range(retry_count):
            try:
                # Make the API call
                translated = self._get_translator().translate(stripped)
                result = translated if translated else text

                # Store successful translation in cache
                if self._use_cache:
                    with self._cache_lock:  # Thread-safe cache write
                        self._cache[key] = result
                return result
                
            except Exception as e:
                # Calculate delay: 1s, 2s, 4s, 8s... up to max_delay
                delay = min(base_delay * (2 ** attempt), max_delay)
                
                if attempt < retry_count - 1:
                    # More attempts remaining - wait and retry
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed, "
                        f"retrying in {delay:.1f}s …"
                    )
                    time.sleep(delay)
                else:
                    # All attempts exhausted - return original text
                    logger.error(
                        f"Translation failed after {retry_count} attempts: {e}"
                    )
                    return text

    def translate_segments(
        self,
        segments: List[Dict],
        max_workers: int = 4,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Translate transcription segments in parallel for speed.
        
        Uses ThreadPoolExecutor to translate multiple segments
        simultaneously. Each thread uses its own translator instance.
        Results are sorted by timestamp after completion.

        Args:
            segments: List of transcription segment dicts with 'text' key
            max_workers: Number of parallel translation threads
            show_progress: Whether to display a progress bar

        Returns:
            List of segments with 'text' containing translation
            and 'original_text' containing the source text
        """
        logger.info(f"Translating {len(segments)} segments to Persian...")

        translated_segments = []

        # Create thread pool for parallel translation
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all translation tasks to the pool
            # Map each Future back to its source segment
            future_to_segment = {
                executor.submit(self.translate_text, seg["text"]): seg 
                for seg in segments
            }

            # Process completed translations as they finish
            iterator = as_completed(future_to_segment)
            if show_progress:
                iterator = tqdm(iterator, total=len(segments), desc="Translating", unit="segment")

            for future in iterator:
                segment = future_to_segment[future]
                try:
                    # Get translation result
                    translated_text = future.result()
                    
                    # Create new segment with both original and translated text
                    translated_segment = segment.copy()
                    translated_segment["original_text"] = segment["text"]
                    translated_segment["text"] = translated_text
                    translated_segments.append(translated_segment)
                    
                except Exception as e:
                    # On error, keep original text
                    logger.error(f"Error translating segment: {str(e)}")
                    translated_segment = segment.copy()
                    translated_segment["original_text"] = segment["text"]
                    translated_segments.append(translated_segment)

        # Parallel execution completes out of order, so re-sort by timestamp
        translated_segments.sort(key=lambda x: x["start"])

        logger.info("Translation complete")
        return translated_segments

    def translate_batch(self, texts: List[str], chunk_size: int = 50) -> List[str]:
        """
        Translate a batch of texts with chunking to avoid API limits.
        
        Google Translate has limits on batch size, so we split large
        batches into smaller chunks. If batch translation fails,
        falls back to translating each text individually.

        Args:
            texts: List of text strings to translate
            chunk_size: Maximum texts per API call (default 50)

        Returns:
            List of translated texts in the same order
        """
        translated = []

        # Process texts in chunks to avoid API limits
        for i in range(0, len(texts), chunk_size):
            chunk = texts[i:i + chunk_size]
            try:
                # Try batch translation for efficiency
                translated_chunk = self._get_translator().translate_batch(chunk)
                translated.extend(translated_chunk)
            except Exception as e:
                # Batch failed - fall back to one-by-one translation
                logger.warning(f"Batch translation failed, falling back to individual: {str(e)}")
                for text in chunk:
                    translated.append(self.translate_text(text))
            
            # Brief pause between chunks to avoid rate limiting
            time.sleep(0.5)

        return translated
