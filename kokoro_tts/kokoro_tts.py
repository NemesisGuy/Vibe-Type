# kokoro_tts.py
# FINAL VERSION - ALL METHODS RESTORED

import json, os, re, threading, requests, numpy as np, onnxruntime as ort, sounddevice as sd
from typing import List, Union, Optional, Generator
from kokoro_onnx import Kokoro
from misaki import en, ja, zh
from pathlib import Path
from queue import Queue
from tqdm import tqdm
import logging

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
SAMPLE_RATE = 24000
PUNCTUATION_RE = r'(?<=[.!?。།、，,;:])\s*'
LANGUAGE_CONFIG = {
    "Auto-Detect": {}, "English (US)": {"lang_code": "a"},
    "Japanese": {"lang_code": "j"}, "Mandarin Chinese": {"lang_code": "z"}
}

class KokoroTTS:
    """Main class for Kokoro Text-to-Speech synthesis."""
    def __init__(self, model_file: str = "kokoro-v1.0.fp16.onnx", model_dir: str = "models/kokoro", execution_provider: str = 'CUDA'):
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / model_file
        self.voices_path = self.model_dir / "voices-v1.0.bin"
        self.g2p_cache = {}

        logger.info("KokoroTTS is initializing...")
        self.download_models()

        self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
        providers = [p for p in [execution_provider.upper() + 'ExecutionProvider', 'CPUExecutionProvider'] if p in ort.get_available_providers()]
        try:
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=providers)
        except Exception as e:
            logger.error(f"Failed session with {providers}. Falling back to CPU. Error: {e}")
            self.kokoro.sess = ort.InferenceSession(str(self.model_path), providers=['CPUExecutionProvider'])

        self.ALL_VOICES = sorted(self.kokoro.get_voices())
        logger.info(f"KokoroTTS initialized with model: {self.model_path} using providers: {self.kokoro.sess.get_providers()}")

    # --- Core Methods ---

    def get_voice_embedding(self, voice_name: str) -> Optional[np.ndarray]:
        try:
            return self.kokoro.get_voice_style(voice_name)
        except Exception as e:
            logger.error(f"Could not get embedding for voice '{voice_name}': {e}")
            return None

    def _get_g2p_pipeline(self, lang_code: str):
        if lang_code in self.g2p_cache: return self.g2p_cache[lang_code]
        logger.info(f"Initializing G2P for lang_code '{lang_code}'...")
        pipeline = None
        if lang_code == 'j': pipeline = ja.JAG2P()
        elif lang_code == 'a': pipeline = en.G2P()
        elif lang_code == 'z': pipeline = zh.ZHG2P()
        if pipeline: self.g2p_cache[lang_code] = pipeline
        return pipeline

    def _synthesize_chunk(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> Optional[np.ndarray]:
        if not text or not re.search(r'\w', text): return None
        try:
            lang_code = LANGUAGE_CONFIG[language_name]["lang_code"]
            g2p_engine = self._get_g2p_pipeline(lang_code)
            try:
                phoneme_result = g2p_engine(text)
            except (TypeError, IndexError):
                logger.error(f"G2P engine failed. Skipping chunk: '{text[:80]}...'")
                return None
            final_phonemes = phoneme_result[0] if isinstance(phoneme_result, tuple) else phoneme_result
            if not final_phonemes or final_phonemes.isspace(): return None
            return self.kokoro.create(final_phonemes, voice=voice_or_embedding, speed=speed, is_phonemes=True)[0]
        except Exception as e:
            logger.error(f"Synthesis error for lang '{language_name}': {e}")
            return None

    # --- Streaming and Synthesis Methods ---

    def stream(self, text: Union[str, List[str]], language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0, device_index: Optional[int] = None, interrupt_event: Optional[threading.Event] = None):
        if isinstance(text, list): text = " ".join(text)
        clean_text = self._preprocess_text(text)

        audio_queue = Queue(maxsize=20)

        def producer():
            fragment_generator = self._generate_monolingual_fragments(clean_text) if language_name == "Auto-Detect" else [(language_name, clean_text)]
            for lang, fragment_text in fragment_generator:
                if interrupt_event and interrupt_event.is_set(): break
                for chunk_text in self._generate_linguistic_chunks(fragment_text):
                    if interrupt_event and interrupt_event.is_set(): break
                    logger.info(f"Synthesizing chunk ({lang}): '{chunk_text}'")
                    audio_chunk = self._synthesize_chunk(chunk_text, lang, voice_or_embedding, speed)
                    if audio_chunk is not None and audio_chunk.size > 0: audio_queue.put(audio_chunk)
            audio_queue.put(None)

        def consumer():
            try:
                with sd.OutputStream(samplerate=SAMPLE_RATE, device=device_index, channels=1, dtype='float32') as stream:
                    while True:
                        if interrupt_event and interrupt_event.is_set(): break
                        chunk = audio_queue.get()
                        if chunk is None: break
                        stream.write(chunk)
            except Exception as e: logger.error(f"Audio playback error: {e}")

        threads = [threading.Thread(target=producer, daemon=True), threading.Thread(target=consumer, daemon=True)]
        for t in threads: t.start()
        for t in threads: t.join()

    def synthesize_to_memory(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> np.ndarray:
        clean_text = self._preprocess_text(text)
        fragment_generator = self._generate_monolingual_fragments(clean_text) if language_name == "Auto-Detect" else [(language_name, clean_text)]
        audio_chunks = []
        for lang, fragment_text in fragment_generator:
            for chunk_text in self._generate_linguistic_chunks(fragment_text):
                audio_chunk = self._synthesize_chunk(chunk_text, lang, voice_or_embedding, speed)
                if audio_chunk is not None:
                    audio_chunks.append(audio_chunk)

        valid_chunks = [c for c in audio_chunks if c is not None and c.size > 0]
        return np.concatenate(valid_chunks) if valid_chunks else np.array([], dtype=np.float32)

    # --- Text Processing Helpers ---

    def _preprocess_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    def _generate_monolingual_fragments(self, text: str) -> Generator[tuple[str, str], None, None]:
        fragments = re.findall(r'[\u3040-\u30ff\u4e00-\u9fff]+|[^\u3040-\u30ff\u4e00-\u9fff]+', text)
        for fragment in fragments:
            fragment = fragment.strip()
            if not fragment: continue
            if re.search(r'[\u3040-\u30ff]', fragment):
                yield "Japanese", fragment
            elif re.search(r'[\u4e00-\u9fff]', fragment):
                yield "Mandarin Chinese", fragment
            else:
                yield "English (US)", fragment

    def _generate_linguistic_chunks(self, text: str) -> Generator[str, None, None]:
        sentences = [s.strip() for s in re.split(PUNCTUATION_RE, text.strip()) if s.strip()]
        if not sentences: return
        yield sentences.pop(0)
        buffer, chunk_count, growth_targets, steady_state_target = [], 1, {1: 2, 2: 4}, 8
        for sentence in sentences:
            buffer.append(sentence)
            target_size = growth_targets.get(chunk_count, steady_state_target)
            if len(buffer) >= target_size:
                yield " ".join(buffer); buffer = []; chunk_count += 1
        if buffer: yield " ".join(buffer)

    # --- Model and Voice Listing Methods (Restored) ---

    def list_languages(self) -> List[str]:
        """Returns a list of supported language names."""
        return list(LANGUAGE_CONFIG.keys())

    def list_voices(self, language_name: Optional[str] = None) -> List[str]:
        """Filters voices based on the selected language."""
        if not language_name or language_name == "Auto-Detect" or language_name not in LANGUAGE_CONFIG:
            return self.ALL_VOICES
        lang_code = LANGUAGE_CONFIG[language_name].get("lang_code")
        if not lang_code: return self.ALL_VOICES
        filtered_voices = [v for v in self.ALL_VOICES if v.startswith(lang_code)]
        return filtered_voices if filtered_voices else self.ALL_VOICES

    def list_models(self) -> List[str]:
        """Lists available ONNX model files in the model directory."""
        if not self.model_dir.exists(): return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]

    # --- File Download Helper ---

    def download_models(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        if not self.model_path.exists():
            url = f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{self.model_path.name}"
            self._download_file(url, self.model_path)
        if not self.voices_path.exists():
            self._download_file(f"https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{self.voices_path.name}", self.voices_path)

    def _download_file(self, url: str, dest: Path):
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                with open(dest, 'wb') as f, tqdm(total=total_size, unit='iB', unit_scale=True, desc=dest.name) as bar:
                    for chunk in r.iter_content(chunk_size=8192):
                        bar.update(f.write(chunk))
        except Exception as e:
            logger.error(f"Failed to download {dest.name}: {e}")
            if dest.exists(): os.remove(dest)
            raise
