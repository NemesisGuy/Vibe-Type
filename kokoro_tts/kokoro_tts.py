# kokoro_tts.py
# FINAL, CORRECTED, AND SIMPLIFIED VERSION. THIS IS THE ONLY LOGICAL SOLUTION.
print("RUNNING KOKORO_TTS.PY, THE FINAL AND CORRECTED VERSION")

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
from langdetect import detect

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Gracefully import optional core module ---
try:
    from core.config_manager import load_config
except ImportError:
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

# --- Language config ---
LANGUAGE_CONFIG = {
    "Auto-Detect": {"lang_code": "auto"},
    "English (US)": {"lang_code": "a", "g2p_british": False, "detect_code": "en"},
    "English (UK)": {"lang_code": "b", "g2p_british": True, "detect_code": "en"},
    "Japanese": {"lang_code": "j", "detect_code": "ja"},
    "Spanish": {"lang_code": "e", "espeak_lang": "es", "detect_code": "es"},
    "French": {"lang_code": "f", "espeak_lang": "fr-fr", "detect_code": "fr"},
    "Hindi": {"lang_code": "h", "espeak_lang": "hi", "detect_code": "hi"},
    "Italian": {"lang_code": "i", "espeak_lang": "it", "detect_code": "it"},
    "Portuguese (BR)": {"lang_code": "p", "espeak_lang": "pt-br", "detect_code": "pt"},
    "Mandarin Chinese": {"lang_code": "z", "detect_code": "zh-cn"},
}

# --- Reverse map for auto-detect ---
DETECT_CODE_MAP = {cfg["detect_code"]: name for name, cfg in LANGUAGE_CONFIG.items() if "detect_code" in cfg}
DETECT_CODE_MAP['en'] = 'English (US)'
DETECT_CODE_MAP['zh-cn'] = 'Mandarin Chinese'
DETECT_CODE_MAP['ja'] = 'Japanese'

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
                logger.warning(f"Provider '{execution_provider}' not available. Falling back to CPU.")
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
        try:
            return self.kokoro.get_voice_style(voice_name)
        except Exception as e:
            logger.error(f"Could not get embedding for voice '{voice_name}': {e}")
            return None

    def _get_g2p_pipeline(self, lang_code: str):
        if lang_code in self.g2p_cache:
            return self.g2p_cache[lang_code]

        logger.info(f"Initializing G2P for lang_code '{lang_code}'...")
        pipeline = None

        if lang_code == 'j':
            try:
                pipeline = ja.JAG2P()
            except Exception as e:
                raise RuntimeError(f"Japanese G2P failed to initialize: {e}")
        elif lang_code in ['a', 'b']:
            cfg = next((c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code), {})
            pipeline = en.G2P(british=cfg.get('g2p_british', False))
        elif lang_code == 'z':
            pipeline = zh.ZHG2P()
        else:
            cfg = next((c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code), {})
            if 'espeak_lang' in cfg:
                pipeline = espeak.EspeakG2P(language=cfg['espeak_lang'])

        if pipeline:
            self.g2p_cache[lang_code] = pipeline
            return pipeline

        raise RuntimeError(f"Could not initialize G2P pipeline for lang_code '{lang_code}'")

    def download_models(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_info = next((m for m in MODEL_FILES if m['filename'] == self.model_path.name), None)

        if model_info and not self.model_path.exists():
            logger.info(f"Downloading {model_info['filename']}...")
            self._download_file(model_info['url'], self.model_path, model_info['description'])

        if not self.voices_path.exists():
            logger.info(f"Downloading {VOICES_FILE}...")
            self._download_file(VOICES_URL, self.voices_path, "Voices file")

    def _download_file(self, url: str, dest: Path, description: str):
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
                os.remove(dest)
            raise

    def _synthesize_chunk(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> Optional[np.ndarray]:
        try:
            effective_language = language_name

            # --- FINAL FIX: Reliable Language Detection ---
            # The `langdetect` library is unreliable and often misidentifies CJK languages as English.
            # This logic provides a robust override. It checks for Japanese and Chinese character ranges
            # *before* falling back to the less reliable library, ensuring CJK text is always
            # processed by the correct engine.
            if language_name == "Auto-Detect":
                if re.search(r'[\u3040-\u30ff]', text): # Japanese Hiragana/Katakana
                    effective_language = "Japanese"
                elif re.search(r'[\u4e00-\u9fff]', text): # Common Chinese characters
                    effective_language = "Mandarin Chinese"
                else:
                    try:
                        detected_code = detect(text)
                        effective_language = DETECT_CODE_MAP.get(detected_code, "English (US)")
                    except Exception:
                        effective_language = "English (US)" # Default fallback
                logger.info(f"Language auto-detected as '{effective_language}' for chunk: '{text[:20]}...'")

            config = LANGUAGE_CONFIG[effective_language]
            lang_code = config["lang_code"]

            # Sanitization now only runs when English is correctly identified.
            sanitized_text = text
            if lang_code in ['a', 'b']:
                sanitized_text = re.sub(r'[^a-zA-Z0-9\s.,?!]', ' ', text)

            if not sanitized_text.strip():
                logger.warning(f"Text became empty after processing, skipping chunk: '{text[:50]}...'")
                return None

            g2p_engine = self._get_g2p_pipeline(lang_code)

            final_phonemes = ""
            try:
                phoneme_result = g2p_engine(sanitized_text)
                if isinstance(phoneme_result, tuple):
                    phoneme_result = phoneme_result[0]
                if phoneme_result is None:
                    phoneme_result = ""
                final_phonemes = phoneme_result
            except Exception as e:
                logger.error(f"CRITICAL: G2P engine failed for lang '{lang_code}' on text: '{sanitized_text}'. Error: {e}")
                traceback.print_exc()
                return None

            if not final_phonemes or final_phonemes.isspace():
                logger.warning(f"G2P produced empty output for text: '{sanitized_text}'")
                return None

            audio_samples, _ = self.kokoro.create(final_phonemes, voice=voice_or_embedding, speed=speed, is_phonemes=True)
            return audio_samples

        except Exception as e:
            logger.error(f"CRITICAL ERROR in _synthesize_chunk: {e}")
            traceback.print_exc()
            return None

    def stream(self, text: Union[str, List[str]], language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0, device_index: Optional[int] = None, interrupt_event: Optional[threading.Event] = None):
        if isinstance(text, list):
            text = " ".join(text)
        # --- SYNTAX ERROR FIX: Corrected the line below ---
        self.stream_progressive_chunking(text, language_name, voice_or_embedding, speed, device_index, interrupt_event)

    def stream_progressive_chunking(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float, device_index: Optional[int], interrupt_event: Optional[threading.Event], buffer_chunks: int = 3):
        audio_queue = Queue(maxsize=buffer_chunks)
        sentences = re.split(r'(?<=[.!?。།、，])\s*', text.replace('\n', ' '))

        def producer():
            for sentence in sentences:
                if interrupt_event and interrupt_event.is_set():
                    break
                if sentence.strip():
                    audio_chunk = self._synthesize_chunk(sentence, language_name, voice_or_embedding, speed)
                    if audio_chunk is not None and audio_chunk.size > 0:
                        audio_queue.put(audio_chunk)
            audio_queue.put(None)

        def consumer():
            try:
                with sd.OutputStream(samplerate=SAMPLE_RATE, device=device_index, channels=1, dtype='float32') as stream:
                    while True:
                        if interrupt_event and interrupt_event.is_set(): break
                        chunk = audio_queue.get()
                        if chunk is None: break
                        stream.write(chunk)
            except Exception as e:
                logger.error(f"Error during audio playback: {e}")

        producer_thread = threading.Thread(target=producer, daemon=True)
        consumer_thread = threading.Thread(target=consumer, daemon=True)
        producer_thread.start()
        consumer_thread.start()
        producer_thread.join()
        consumer_thread.join()

    def synthesize_to_memory(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> np.ndarray:
        logger.info(f"Synthesizing: '{text[:50]}...' (Lang: {language_name})")

        sentences = re.split(r'(?<=[.!?。།、，])\s*', text.replace('\n', ' '))
        # The robust language detection is now handled at the chunk level, so we just pass the user's selection.
        audio_chunks = [self._synthesize_chunk(s, language_name, voice_or_embedding, speed) for s in sentences if s.strip()]

        valid_chunks = [chunk for chunk in audio_chunks if chunk is not None]
        if not valid_chunks:
            logger.error("Synthesis failed: No audio could be generated.")
            return np.array([], dtype=np.float32)

        return np.concatenate(valid_chunks)

    def list_languages(self) -> List[str]:
        return list(LANGUAGE_CONFIG.keys())

    def list_voices(self, language_name: Optional[str] = None) -> List[str]:
        if not language_name or language_name not in LANGUAGE_CONFIG or language_name == "Auto-Detect":
            return self.ALL_VOICES
        lang_code = LANGUAGE_CONFIG[language_name]["lang_code"]
        if lang_code in ['a', 'b']:
            return [v for v in self.ALL_VOICES if not v.startswith(('j', 'z'))]
        filtered_voices = [v for v in self.ALL_VOICES if v.startswith(lang_code)]
        return filtered_voices if filtered_voices else self.ALL_VOICES

    def list_models(self) -> List[str]:
        if not self.model_dir.exists():
            return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]