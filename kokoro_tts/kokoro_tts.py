# kokoro_tts.py
import json
import os
import numpy as np
import soundfile as sf
from typing import List, Dict, Union, Optional
from kokoro_onnx import Kokoro
from misaki import en, ja, espeak, zh
from pathlib import Path
import logging
import requests
from tqdm import tqdm
import onnxruntime as ort
import traceback
import re
import threading
import sounddevice as sd
from queue import Queue

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Gracefully import optional core module ---
try:
    from core.config_manager import load_config
except ImportError:
    # If core is not available, create a dummy function to avoid errors
    def load_config():
        return {}
    logger.info("Running in standalone mode. 'core.config_manager' not found.")


# --- Constants ---
MODEL_FILES = [
    {"filename": "kokoro-v1.0.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx", "description": "Full Precision (FP32)"},
    {"filename": "kokoro-v1.0.fp16.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx", "description": "Half Precision (FP16)"},
    {"filename": "kokoro-v1.0.int8.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx", "description": "Quantized (INT8)"}
]
VOICES_FILE = "voices-v1.0.bin"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/" + VOICES_FILE
SAMPLE_RATE = 24000

# This config links the UI to the correct misaki phonemizer codes.
LANGUAGE_CONFIG = {
    "English (US)": {"lang_code": "a", "g2p_british": False},
    "English (UK)": {"lang_code": "b", "g2p_british": True},
    "Japanese": {"lang_code": "j"},
    "Spanish": {"lang_code": "e", "espeak_lang": "es"},
    "French": {"lang_code": "f", "espeak_lang": "fr-fr"},
    "Hindi": {"lang_code": "h", "espeak_lang": "hi"},
    "Italian": {"lang_code": "i", "espeak_lang": "it"},
    "Portuguese (BR)": {"lang_code": "p", "espeak_lang": "pt-br"},
    "Mandarin Chinese": {"lang_code": "z"},
}


class KokoroTTS:
    def __init__(self, model_file: str = "kokoro-v1.0.fp16.onnx", model_dir: str = "models/kokoro", execution_provider: str = 'CUDA'):
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / model_file
        self.voices_path = self.model_dir / VOICES_FILE
        self.benchmark_dir = Path("benchmarks")
        self.g2p_cache = {}

        logger.info("KokoroTTS is initializing...")
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        self.download_models()

        available_providers = ort.get_available_providers()
        logger.info(f"Available ONNX providers: {available_providers}")

        self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))

        providers = []
        selected_provider = execution_provider.upper()
        if selected_provider == 'CUDA' and 'CUDAExecutionProvider' in available_providers:
            providers = ['CUDAExecutionProvider']
        elif selected_provider == 'TENSORRT' and 'TensorrtExecutionProvider' in available_providers:
            providers = ['TensorrtExecutionProvider']
        else:
            if selected_provider not in ['CPU']:
                logger.warning(f"Provider '{execution_provider}' not available or not selected. Falling back to CPU.")
            providers = ['CPUExecutionProvider']

        try:
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=providers)
        except Exception as e:
            logger.error(f"Failed to create ONNX session with {providers}. Falling back to CPU. Error: {e}")
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])

        self.ALL_VOICES = sorted(self.kokoro.get_voices())
        logger.info(f"KokoroTTS initialized with model: {self.model_path}")
        logger.info(f"Actively using ONNX providers: {self.kokoro.sess.get_providers()}")

    def get_voice_embedding(self, voice_name: str) -> Optional[np.ndarray]:
        """Retrieves the voice embedding for a given voice name."""
        try:
            return self.kokoro.get_voice_style(voice_name)
        except Exception as e:
            logger.error(f"Could not get embedding for voice '{voice_name}': {e}")
            return None

    def _get_g2p_pipeline(self, lang_code: str):
        """Initializes and caches the correct Misaki G2P pipeline for each language."""
        if lang_code in self.g2p_cache:
            return self.g2p_cache[lang_code]

        logger.info(f"Initializing G2P for lang_code '{lang_code}'...")
        pipeline = None

        # Specific handling for Japanese to ensure dictionary is present
        if lang_code == 'j':
            try:
                import unidic
                # Verify that the dictionary path exists to provide a helpful error message
                mecabrc_path = os.path.join(unidic.DICDIR, "mecabrc")
                if not os.path.exists(mecabrc_path):
                    raise RuntimeError(
                        "CRITICAL: Japanese dictionary not found!\n"
                        f"Required file not found: {mecabrc_path}\n"
                        "This means the 'unidic' dictionary failed to download during installation.\n"
                        "Please fix your environment by MANUALLY downloading the dictionary.\n"
                        "Run this command in your terminal and then restart the application:\n\n"
                        "    python -m unidic download\n"
                    )
                # Set MECABRC for misaki to find the correct dictionary
                os.environ["MECABRC"] = mecabrc_path
                pipeline = ja.JAG2P()
            except ImportError:
                raise RuntimeError("Japanese support requires 'unidic'. Please run 'pip install misaki[ja]' or 'pip install unidic'.")

        elif lang_code in ['a', 'b']:
            cfg = next((c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code), {})
            pipeline = en.G2P(british=cfg.get('g2p_british', False))
        elif lang_code == 'z':
            pipeline = zh.ZHG2P()
        else: # For espeak-supported languages
            cfg = next((c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code), {})
            if 'espeak_lang' in cfg:
                pipeline = espeak.EspeakG2P(language=cfg['espeak_lang'])

        if pipeline:
            self.g2p_cache[lang_code] = pipeline
            return pipeline

        raise RuntimeError(f"Could not initialize G2P pipeline for lang_code '{lang_code}'")

    def download_models(self) -> None:
        """Downloads model and voice files if they don't exist, respecting local-only mode."""
        try:
            config = load_config()
            if config.get('privacy', {}).get('local_only_mode', False):
                logger.info("Local-Only Mode is enabled. Skipping model downloads.")
                return
        except Exception:
            pass  # Fail silently if config loading fails

        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_info = next((m for m in MODEL_FILES if m['filename'] == self.model_path.name), None)

        if model_info and not self.model_path.exists():
            logger.info(f"Downloading {model_info['filename']}...")
            self._download_file(model_info['url'], self.model_path, model_info['description'])

        if not self.voices_path.exists():
            logger.info(f"Downloading {VOICES_FILE}...")
            self._download_file(VOICES_URL, self.voices_path, "Voices file")

    def _download_file(self, url: str, dest: Path, description: str):
        """Helper to download a file with a progress bar."""
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(dest, 'wb') as f, tqdm(total=total_size, unit='iB', unit_scale=True, desc=description) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        size = f.write(chunk)
                        bar.update(size)
        except Exception as e:
            logger.error(f"Failed to download {dest.name}: {e}")
            if dest.exists():
                os.remove(dest) # Clean up partial download
            raise

    def _synthesize_chunk(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> Optional[np.ndarray]:
        """Synthesizes a single chunk of text to audio samples."""
        try:
            config = LANGUAGE_CONFIG[language_name]
            lang_code = config["lang_code"]

            # Step 1: Use the correct, dedicated misaki phonemizer.
            g2p = self._get_g2p_pipeline(lang_code)

            # Step 2: Get the phonemes.
            result = g2p(text)
            phonemes = result[0] if isinstance(result, tuple) else result

            if not phonemes:
                logger.warning(f"Could not generate phonemes for sentence: '{text}'")
                return None

            # Step 3: Use the kokoro object to generate audio from phonemes.
            samples, _ = self.kokoro.create(phonemes, voice=voice_or_embedding, speed=speed, is_phonemes=True)
            return samples
        except Exception as e:
            logger.error(f"An unexpected error occurred during chunk synthesis: {e}")
            traceback.print_exc()
            return None

    def stream(self, text: Union[str, List[str]], language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0, device_index: Optional[int] = None, interrupt_event: Optional[threading.Event] = None):
        """
        Public method to stream TTS audio.
        This method takes text, and uses the progressive chunking streamer to play it back.
        It handles both a single string and a list of sentences as input.
        """
        if isinstance(text, list):
            text = " ".join(text)

        self.stream_progressive_chunking(
            text,
            language_name,
            voice_or_embedding,
            speed=speed,
            device_index=device_index,
            interrupt_event=interrupt_event
        )

    def stream_progressive_chunking(
            self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray],
            speed: float = 1.0, device_index: Optional[int] = None,
            interrupt_event: Optional[threading.Event] = None, buffer_chunks: int = 3):
        """Synthesizes and streams audio with progressive chunking and smooth buffered playback."""
        # Use more comprehensive splitters for different languages
        sentences = re.split(r'(?<=[.!?。།、，])\s*', text.replace('\n', ' '))
        audio_queue = Queue(maxsize=buffer_chunks)

        def producer():
            sentence_idx = 0
            chunk_size = 1
            while sentence_idx < len(sentences):
                if interrupt_event and interrupt_event.is_set():
                    logger.info("Producer interrupted.")
                    break

                chunk_sentences = sentences[sentence_idx : sentence_idx + chunk_size]
                chunk_text = " ".join(chunk_sentences).strip()

                if not chunk_text: # Skip empty chunks
                    sentence_idx += chunk_size
                    continue

                logger.info(f"Synthesizing chunk (size {len(chunk_sentences)}): '{chunk_text[:50]}...'")
                audio_chunk = self._synthesize_chunk(chunk_text, language_name, voice_or_embedding, speed)

                if audio_chunk is not None and audio_chunk.size > 0:
                    audio_queue.put(audio_chunk)

                sentence_idx += chunk_size
                chunk_size = min(chunk_size * 2, 8) # Exponential growth with a cap

            audio_queue.put(None)  # Sentinel to indicate the end of audio

        def consumer():
            try:
                # Use an output stream for continuous playback without gaps
                with sd.OutputStream(samplerate=SAMPLE_RATE, device=device_index, channels=1, dtype='float32') as stream:
                    while True:
                        if interrupt_event and interrupt_event.is_set():
                            logger.info("Consumer interrupted.")
                            break

                        audio_chunk = audio_queue.get()
                        if audio_chunk is None:
                            break

                        stream.write(audio_chunk)
            except Exception as e:
                logger.error(f"Error during buffered playback: {e}")

        # Use daemon threads so they don't block program exit
        producer_thread = threading.Thread(target=producer, daemon=True)
        consumer_thread = threading.Thread(target=consumer, daemon=True)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

    def synthesize_to_memory(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> np.ndarray:
        """Synthesizes full text to an in-memory numpy array."""
        logger.info(f"Synthesizing: '{text[:50]}...' (Lang: {language_name})")
        sentences = re.split(r'(?<=[.!?。།、，])\s*', text.replace('\n', ' '))
        audio_chunks = []
        for sentence in sentences:
            if not sentence.strip():
                continue
            audio_chunk = self._synthesize_chunk(sentence, language_name, voice_or_embedding, speed)
            if audio_chunk is not None:
                audio_chunks.append(audio_chunk)

        if not audio_chunks:
            logger.error("Synthesis failed: No audio could be generated for any sentence.")
            return np.array([], dtype=np.float32)

        return np.concatenate(audio_chunks)

    def list_languages(self) -> List[str]:
        """Returns a list of supported language names."""
        return list(LANGUAGE_CONFIG.keys())

    def list_voices(self, language_name: Optional[str] = None) -> List[str]:
        """Filters voices based on the selected language, defaulting to all if none match."""
        if not language_name or language_name not in LANGUAGE_CONFIG:
            return self.ALL_VOICES

        lang_code = LANGUAGE_CONFIG[language_name]["lang_code"]

        # English voices are not prefixed, but are the default set.
        if lang_code in ['a', 'b']:
            return [v for v in self.ALL_VOICES if not v.startswith(('j', 'z'))]

        # Language-specific filtering
        filtered_voices = [v for v in self.ALL_VOICES if v.startswith(lang_code)]

        if not filtered_voices:
            logger.warning(f"No voices found for language '{language_name}' (code: {lang_code}). Returning all voices.")
            return self.ALL_VOICES

        return filtered_voices

    def list_models(self) -> List[str]:
        """Lists available ONNX model files in the model directory."""
        if not self.model_dir.exists():
            return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]