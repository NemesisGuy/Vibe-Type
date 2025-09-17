# kokoro_tts.py
# FINAL, TRUE LANGUAGE-AWARE CHUNKING VERSION

print("RUNNING KOKORO_TTS.PY, TRUE LANGUAGE-AWARE CHUNKING VERSION")

import json, os, re, threading, requests, numpy as np, onnxruntime as ort, sounddevice as sd
from typing import List, Dict, Union, Optional, Generator
from kokoro_onnx import Kokoro
from misaki import en, ja, espeak, zh
from pathlib import Path
from queue import Queue
from tqdm import tqdm
from langdetect import detect, LangDetectException
import logging

# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
SAMPLE_RATE = 24000
PUNCTUATION_RE = r'(?<=[.!?。།、，,;:])\s*'
LANGUAGE_CONFIG = {
    "Auto-Detect": {},
    "English (US)": {"lang_code": "a", "detect_code": "en"},
    "Japanese": {"lang_code": "j", "detect_code": "ja"},
    "Mandarin Chinese": {"lang_code": "z", "detect_code": "zh-cn"},
    "Spanish": {"lang_code": "e", "espeak_lang": "es", "detect_code": "es"},
    "French": {"lang_code": "f", "espeak_lang": "fr-fr", "detect_code": "fr"},
    "Portuguese (BR)": {"lang_code": "p", "espeak_lang": "pt-br", "detect_code": "pt"},
    "Italian": {"lang_code": "i", "espeak_lang": "it", "detect_code": "it"},
    "Hindi": {"lang_code": "h", "espeak_lang": "hi", "detect_code": "hi"},
}
DETECT_CODE_MAP = {cfg["detect_code"]: name for name, cfg in LANGUAGE_CONFIG.items() if "detect_code" in cfg}

SHOW_PHONEMES_IN_LOGS = True  # Set to True to log phoneme details for each chunk

class KokoroTTS:
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

    def get_voice_embedding(self, voice_name: str) -> Optional[np.ndarray]:
        try: return self.kokoro.get_voice_style(voice_name)
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
        else:
            cfg = next((c for c in LANGUAGE_CONFIG.values() if c.get('lang_code') == lang_code and 'espeak_lang' in c), None)
            if cfg: pipeline = espeak.EspeakG2P(language=cfg['espeak_lang'])
        if pipeline: self.g2p_cache[lang_code] = pipeline
        return pipeline

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

    def _preprocess_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text).strip()

    # --- TRUE LANGUAGE-AWARE CHUNKING ---
    def _segment_by_language(self, text: str) -> List[tuple[str, str]]:
        # Improved segmentation: group runs of the same script, robust langdetect for Latin (incl. extended)
        latin_class = r'A-Za-z\u00C0-\u024F\u1E00-\u1EFF0-9'
        script_regex = re.compile(
            rf'([{latin_class} ,.;:!?"()\-\']+|'  # Latin (ASCII + extended) + spaces/punctuation
            r'[\u4e00-\u9fff]+|'  # Han (Chinese)
            r'[\u3040-\u30ff]+|' # Kana (Japanese)
            r'[\u0900-\u097F]+|' # Devanagari (Hindi)
            r'[\u0400-\u04FF]+|' # Cyrillic
            r'[.,;:!?"()\-\']+|'   # Standalone punctuation
            r'\s+)'                # Whitespace
        )
        segments = []
        for match in script_regex.finditer(text):
            seg = match.group(0)
            if seg.isspace():
                continue
            # Latin runs: use langdetect only for longer segments
            if re.match(rf'^[{latin_class} ,.;:!?"()\-\']+$', seg):
                if len(seg.strip()) < 12:
                    lang = 'English (US)'
                else:
                    try:
                        lang_code = detect(seg)
                        lang = DETECT_CODE_MAP.get(lang_code, 'English (US)')
                    except LangDetectException:
                        lang = 'English (US)'
            elif re.match(r'^[\u4e00-\u9fff]+$', seg):
                lang = 'Mandarin Chinese'
            elif re.match(r'^[\u3040-\u30ff]+$', seg):
                lang = 'Japanese'
            elif re.match(r'^[\u0900-\u097F]+$', seg):
                lang = 'Hindi'
            elif re.match(r'^[\u0400-\u04FF]+$', seg):
                lang = 'Russian'
            elif re.match(r'^[.,;:!?"()\-\']+$', seg):
                # Attach punctuation to previous segment if possible
                if segments:
                    prev_lang, prev_seg = segments[-1]
                    segments[-1] = (prev_lang, prev_seg + seg)
                    continue
                else:
                    lang = 'English (US)'
            else:
                lang = 'English (US)'
            segments.append((lang, seg))
        # Merge adjacent segments of same language
        merged = []
        for lang, seg in segments:
            if merged and merged[-1][0] == lang:
                merged[-1] = (lang, merged[-1][1] + seg)
            else:
                merged.append((lang, seg))
        logger.debug(f"Polyglot segmentation: {merged}")
        return merged

    def _generate_linguistic_chunks(self, text: str, max_sentences: int = 4) -> Generator[str, None, None]:
        sentences = [s.strip() for s in re.split(PUNCTUATION_RE, text) if s.strip()]
        for i in range(0, len(sentences), max_sentences):
            yield " ".join(sentences[i:i+max_sentences])

    def _synthesize_chunk(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> Optional[np.ndarray]:
        logger.info(f"_synthesize_chunk called with text: '{text}', language: '{language_name}'")
        # Allow Latin (basic+extended), digits, Han, Kana, Devanagari, Cyrillic
        if not re.search(r'[A-Za-z0-9\u00C0-\u024F\u1E00-\u1EFF\u4e00-\u9fff\u3040-\u30ff\u0900-\u097F\u0400-\u04FF]', text):
            logger.info(f"Skipping punctuation/symbol-only chunk: '{text}'")
            return None
        lang_code = LANGUAGE_CONFIG[language_name].get("lang_code")
        if not lang_code: return None
        g2p_engine = self._get_g2p_pipeline(lang_code)
        if not g2p_engine:
            logger.warning(f"No G2P engine for language '{language_name}'. Skipping.")
            return None
        try:
            phonemes = g2p_engine(text)
        except Exception as e:
            logger.warning(f"G2P failed for text: '{text}' (lang: {language_name}): {e}")
            return None
        if SHOW_PHONEMES_IN_LOGS:
            # Log phoneme string and token details
            if isinstance(phonemes, tuple) and len(phonemes) == 2 and isinstance(phonemes[1], list):
                logger.info(f"Phoneme string: {phonemes[0]}")
                for t in phonemes[1]:
                    logger.info(f"Token: '{getattr(t, 'text', '')}' | Phonemes: '{getattr(t, 'phonemes', '')}' | Whitespace: '{getattr(t, 'whitespace', '')}'")
            else:
                logger.info(f"Phoneme string: {phonemes}")
        if logger.isEnabledFor(logging.DEBUG):
            preview = (text[:60] + '…') if len(text) > 60 else text
            if isinstance(phonemes, tuple) and len(phonemes) == 2 and isinstance(phonemes[1], list):
                logger.debug(f"G2P ok ({language_name}): '{preview}' tokens={len(phonemes[1])}")
            else:
                logger.debug(f"G2P ok ({language_name}): '{preview}'")
        # --- Robustly handle None phonemes ---
        if phonemes is None:
            logger.warning(f"G2P returned None for text: '{text}' (lang: {language_name})")
            return None
        final_phonemes = phonemes[0] if isinstance(phonemes, tuple) else phonemes
        if isinstance(final_phonemes, list):
            filtered = [t for t in final_phonemes if getattr(t, 'phonemes', None) is not None]
            if not filtered:
                logger.warning(f"All tokens have None phonemes for text: '{text}' (lang: {language_name})")
                return None
            final_phonemes = ''.join(getattr(t, 'phonemes', '') + getattr(t, 'whitespace', '') for t in filtered)
        if not final_phonemes or final_phonemes.isspace(): return None
        return self.kokoro.create(final_phonemes, voice=voice_or_embedding, speed=speed, is_phonemes=True)[0]

    # --- STREAMING ---
    def stream(self, text: Union[str, List[str]], language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0, device_index: Optional[int] = None, interrupt_event: Optional[threading.Event] = None):
        if isinstance(text, list): text = " ".join(text)
        clean_text = self._preprocess_text(text)
        audio_queue = Queue(maxsize=20)

        def producer():
            segments = self._segment_by_language(clean_text) if language_name == "Auto-Detect" else [(language_name, clean_text)]
            for lang, seg_text in segments:
                if interrupt_event and interrupt_event.is_set(): break
                for chunk in self._generate_linguistic_chunks(seg_text):
                    if interrupt_event and interrupt_event.is_set(): break
                    logger.info(f"Synthesizing chunk ({lang}): '{chunk}'")
                    audio_chunk = self._synthesize_chunk(chunk, lang, voice_or_embedding, speed)
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
            except Exception as e: logger.error(f"Audio playback error: {e}")

        threads = [threading.Thread(target=producer, daemon=True), threading.Thread(target=consumer, daemon=True)]
        for t in threads: t.start()
        for t in threads: t.join()

    # --- MEMORY SYNTHESIS ---
    def synthesize_to_memory(self, text: str, language_name: str, voice_or_embedding: Union[str, np.ndarray], speed: float = 1.0) -> np.ndarray:
        clean_text = self._preprocess_text(text)
        segments = self._segment_by_language(clean_text) if language_name == "Auto-Detect" else [(language_name, clean_text)]
        audio_chunks = []
        for lang, seg in segments:
            for chunk in self._generate_linguistic_chunks(seg):
                audio_chunk = self._synthesize_chunk(chunk, lang, voice_or_embedding, speed)
                if audio_chunk is not None and audio_chunk.size > 0:
                    audio_chunks.append(audio_chunk)
        return np.concatenate(audio_chunks) if audio_chunks else np.array([], dtype=np.float32)

    # --- UTILITIES ---
    def list_languages(self) -> List[str]:
        return list(LANGUAGE_CONFIG.keys())

    def list_models(self) -> List[str]:
        if not self.model_dir.exists(): return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]

    def list_voices(self, language_name: Optional[str] = None) -> List[str]:
        if not language_name or language_name == "Auto-Detect" or language_name not in LANGUAGE_CONFIG:
            return self.ALL_VOICES
        lang_code = LANGUAGE_CONFIG[language_name].get("lang_code")
        if not lang_code: return self.ALL_VOICES
        filtered_voices = [v for v in self.ALL_VOICES if v.startswith(lang_code)]
        return filtered_voices if filtered_voices else self.ALL_VOICES
