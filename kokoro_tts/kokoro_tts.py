import json
import os
import numpy as np
import soundfile as sf
from typing import List, Dict, Union, Optional
from kokoro_onnx import Kokoro, Tokenizer
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

# Import from core
from core.config_manager import load_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_FILES = [
    {"filename": "kokoro-v1.0.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx", "description": "Full Precision (FP32)"},
    {"filename": "kokoro-v1.0.fp16.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx", "description": "Half Precision (FP16)"},
    {"filename": "kokoro-v1.0.int8.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx", "description": "Quantized (INT8)"}
]
VOICES_FILE = "voices-v1.0.bin"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/" + VOICES_FILE
SAMPLE_RATE = 24000
LANGUAGE_CONFIG = {
    "English (US)": {"lang_code": "a", "g2p_british": False, "tokenizer_lang": "en-us"},
    "English (UK)": {"lang_code": "b", "g2p_british": True, "tokenizer_lang": "en-gb"},
    "Japanese": {"lang_code": "j", "tokenizer_lang": "ja"},
    "Spanish": {"lang_code": "e", "espeak_lang": "es", "tokenizer_lang": "es"},
    "French": {"lang_code": "f", "espeak_lang": "fr-fr", "tokenizer_lang": "fr-fr"},
    "Hindi": {"lang_code": "h", "espeak_lang": "hi", "tokenizer_lang": "hi"},
    "Italian": {"lang_code": "i", "espeak_lang": "it", "tokenizer_lang": "it"},
    "Portuguese (BR)": {"lang_code": "p", "espeak_lang": "pt-br", "tokenizer_lang": "pt-br"},
    "Mandarin Chinese": {"lang_code": "z", "tokenizer_lang": "zh"},
}

class KokoroTTS:
    def __init__(self, model_file: str = "kokoro-v1.0.fp16.onnx", model_dir: str = "models/kokoro", execution_provider: str = 'CUDA'):
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / model_file
        self.voices_path = self.model_dir / VOICES_FILE
        self.benchmark_dir = Path("benchmarks")
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        logger.info("KokoroTTS is initializing...")
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
        elif selected_provider == 'CPU':
            providers = ['CPUExecutionProvider']
        else:
            logger.warning(f"Provider '{execution_provider}' not available or not selected. Falling back to CPU.")
            providers = ['CPUExecutionProvider']

        try:
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=providers)
        except Exception as e:
            logger.error(f"Failed to create ONNX session with {providers}. Falling back to CPU. Error: {e}")
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])

        self.ALL_VOICES = sorted(self.kokoro.get_voices())
        self.kokoro_tokenizer = Tokenizer()
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
        logger.info(f"Creating new G2P pipeline for lang_code '{lang_code}'...")
        config = next((c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code or c.get('tokenizer_lang') == lang_code), None)
        if lang_code in ['a', 'b']:
            return en.G2P(british=config['g2p_british'])
        elif lang_code == 'j':
            return ja.JAG2P()
        elif lang_code == 'z':
            return zh.ChineseG2P()
        else:
            if config and 'espeak_lang' in config:
                return espeak.EspeakG2P(language=config['espeak_lang'])

        # Fallback for tokenizer_lang codes that don't map to a special G2P pipeline
        logger.warning(f"No specific G2P pipeline for lang_code '{lang_code}', falling back to kokoro-onnx tokenizer.")
        return self.kokoro_tokenizer

    def download_models(self) -> None:
        try:
            config = load_config()
            if config.get('privacy', {}).get('local_only_mode', False):
                logger.info("Local-Only Mode is enabled. Skipping model downloads.")
                return
        except Exception:
            pass
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
            config = LANGUAGE_CONFIG[language_name]
            lang_code = config["lang_code"]
            tokenizer_lang = config.get("tokenizer_lang", lang_code)
            phonemes = None
            try:
                g2p = self._get_g2p_pipeline(lang_code)
                result = g2p(text)
                if result:
                    phonemes = result[0] if isinstance(result, tuple) else result
            except Exception as e:
                logger.error(f"Misaki phonemizer failed for language '{language_name}'. Error: {e}")
                logger.info("Attempting to fall back to the built-in Kokoro tokenizer.")
            if phonemes is None:
                try:
                    phonemes = self.kokoro_tokenizer.phonemize(text, lang=tokenizer_lang)
                    logger.info("Successfully generated phonemes using the built-in Kokoro tokenizer.")
                except Exception as fallback_e:
                    logger.error(f"FATAL: Built-in Kokoro tokenizer also failed. Error: {fallback_e}")
                    return None
            if not phonemes:
                logger.warning(f"Could not generate phonemes for sentence: '{text}'")
                return None

            samples, _ = self.kokoro.create(phonemes, voice=voice_or_embedding, speed=speed, is_phonemes=True)
            return samples
        except Exception as e:
            logger.error(f"An unexpected error occurred during chunk synthesis: {e}")
            traceback.print_exc()
            return None

    def stream(self, sentences: List[str], language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0, device_index: Optional[int] = None, interrupt_event: Optional[threading.Event] = None):
        """Synthesizes and streams audio sentence by sentence."""
        for sentence in sentences:
            if interrupt_event and interrupt_event.is_set():
                logger.info("Stream interrupted.")
                break
            
            if not sentence.strip():
                continue

            audio_chunk = self._synthesize_chunk(sentence, language_name, voice_or_embedding, speed)
            
            if audio_chunk is not None and audio_chunk.size > 0:
                if interrupt_event and interrupt_event.is_set():
                    logger.info("Stream interrupted before playing audio chunk.")
                    break
                try:
                    sd.play(audio_chunk, samplerate=SAMPLE_RATE, device=device_index)
                    sd.wait()
                except Exception as e:
                    logger.error(f"Error playing audio chunk: {e}")
            elif audio_chunk is not None:
                 logger.warning("Synthesized audio chunk is empty.")

    def synthesize_to_memory(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> np.ndarray:
        logger.info(f"Synthesizing: '{text[:50]}...' (Lang: {language_name})")
        sentences = re.split(r'(?<=[.!?])\s+', text.replace('\n', ' '))
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
        return list(LANGUAGE_CONFIG.keys())

    def list_voices(self, language_name: Optional[str] = None) -> List[str]:
        if not language_name or language_name not in LANGUAGE_CONFIG:
            return self.ALL_VOICES
        lang_code = LANGUAGE_CONFIG[language_name]["lang_code"]
        if lang_code in ['a', 'b']:
            return self.ALL_VOICES
        if lang_code == 'j':
            return [v for v in self.ALL_VOICES if v.startswith('j')]
        if lang_code == 'z':
            return [v for v in self.ALL_VOICES if v.startswith('z')]
        return [v for v in self.ALL_VOICES if not v.startswith(('a', 'b', 'j', 'z'))]

    def list_models(self) -> List[str]:
        if not self.model_dir.exists():
            return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]

    def run_benchmark(self, text: str = "This is a benchmark test.", output_file: str = "benchmark_output.wav"):
        logger.info(f"Running benchmark with text: '{text}'")
        english_voices = self.list_
