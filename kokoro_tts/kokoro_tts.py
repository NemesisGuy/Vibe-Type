import json
import os
import numpy as np
import soundfile as sf
from typing import List, Dict, Union, Optional
from kokoro_onnx import Kokoro, Tokenizer
from pathlib import Path
import logging
import asyncio
import requests
import time
import psutil
import csv
from datetime import datetime
from tqdm import tqdm

# Import from core
from core.config_manager import load_config

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MODEL_FILES = [
    {"filename": "kokoro-v1.0.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx", "description": "Full Precision (FP32)"},
    {"filename": "kokoro-v1.0.fp16.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx", "description": "Half Precision (FP16)"},
    {"filename": "kokoro-v1.0.int8.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx", "description": "Quantized (INT8)"}
]
VOICES_FILE = "voices-v1.0.bin"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/" + VOICES_FILE
SAMPLE_RATE = 24000

class KokoroTTS:
    def __init__(self,
                 model_file: str = "kokoro-v1.0.int8.onnx",
                 model_dir: str = "kokoro_tts/models",
                 lang_code: str = "en-us"):
        self.model_dir = Path(model_dir)
        self.model_path = self.model_dir / model_file
        self.voices_path = self.model_dir / VOICES_FILE
        self.lang_code = lang_code
        self.benchmark_dir = Path("kokoro_tts/benchmarks")
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)

        self.download_models()

        self.tokenizer = Tokenizer()
        # Corrected: Removed execution_provider from Kokoro constructor
        self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
        self.available_voices = self.kokoro.get_voices()
        self.audio_queue = asyncio.Queue(maxsize=20)
        logger.info(f"KokoroTTS initialized with model: {self.model_path}, voices: {self.voices_path}")

    def download_models(self) -> None:
        """Download model and voices from GitHub if not present."""
        config = load_config()
        if config.get('privacy', {}).get('local_only_mode', False):
            logger.info("Local-Only Mode is enabled. Skipping model downloads.")
            return

        self.model_dir.mkdir(parents=True, exist_ok=True)

        for model_info in MODEL_FILES:
            model_path = self.model_dir / model_info["filename"]
            if not model_path.exists():
                logger.info(f"Downloading {model_info['filename']}...")
                try:
                    with requests.get(model_info["url"], stream=True) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        with open(model_path, 'wb') as f, tqdm(
                                total=total_size, unit='iB', unit_scale=True, desc=model_info["filename"]
                        ) as bar:
                            for chunk in r.iter_content(chunk_size=8192):
                                size = f.write(chunk)
                                bar.update(size)
                except Exception as e:
                    logger.error(f"Failed to download {model_info['filename']}: {e}")
                    raise

        if not self.voices_path.exists():
            logger.info(f"Downloading {VOICES_FILE}...")
            try:
                with requests.get(VOICES_URL, stream=True) as r:
                    r.raise_for_status()
                    with open(self.voices_path, 'wb') as f:
                        f.write(r.content)
            except Exception as e:
                logger.error(f"Failed to download {VOICES_FILE}: {e}")
                raise

    def _validate_line(self, line: Dict) -> None:
        if "voice" in line and line["voice"] not in self.available_voices:
            raise ValueError(f"Invalid voice: {line['voice']} in line: {line['text']}")

    def _chunk_script(self, script: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
        return [script[i:i + chunk_size] for i in range(0, len(script), chunk_size)]

    async def _generate_chunk(self, chunk: List[Dict]) -> Optional[np.ndarray]:
        try:
            audio_chunks = []
            for line in chunk:
                text = line["text"]
                voice = line.get("voice", "en_us_cmu_arctic_slt")
                if voice not in self.available_voices:
                    logger.warning(f"Voice '{voice}' not available. Skipping line: {text[:30]}...")
                    continue

                phonemes = self.tokenizer.phonemize(text, lang=self.lang_code)
                if not phonemes:
                    logger.warning(f"Could not phonemize text: {text[:30]}... Skipping.")
                    continue

                samples, _ = await asyncio.to_thread(self.kokoro.create, phonemes, voice=voice, is_phonemes=True)
                if samples is not None:
                    audio_chunks.append(samples.astype(np.float32))
            
            return np.concatenate(audio_chunks) if audio_chunks else None
        except Exception as e:
            logger.error(f"Error in _generate_chunk: {e}")
            return None

    async def _generate_all_chunks_async(self, script: List[Dict], chunk_size: int) -> List[np.ndarray]:
        chunks = self._chunk_script(script, chunk_size)
        tasks = [self._generate_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        return [res for res in results if res is not None and res.size > 0]

    def synthesize_to_memory(self, script: Union[str, List[Dict]], chunk_size: int = 10) -> np.ndarray:
        try:
            if isinstance(script, str):
                script = [{"text": script, "voice": "en_us_cmu_arctic_slt"}]

            for line in script:
                self._validate_line(line)

            audio_segments = asyncio.run(self._generate_all_chunks_async(script, chunk_size))

            if audio_segments:
                final_audio = np.concatenate(audio_segments)
                max_val = np.max(np.abs(final_audio))
                if max_val > 0:
                    final_audio /= max_val
                return final_audio
            else:
                logger.warning("No audio generated from script.")
                return np.array([], dtype=np.float32)
        except Exception as e:
            logger.error(f"Error during synthesis: {e}")
            return np.array([], dtype=np.float32)

    def list_voices(self) -> List[str]:
        return sorted(self.available_voices)

    def list_models(self) -> List[str]:
        if not self.model_dir.exists():
            return []
        return [f.name for f in self.model_dir.glob("*.onnx") if f.is_file()]

    def run_benchmark(self, text: str = "This is a benchmark test.", output_file: str = "benchmark_output.wav"):
        logger.info(f"Running Kokoro TTS benchmark with text: '{text}'")
        script = [{"text": text, "voice": "en_us_cmu_arctic_slt"}]
        self.synthesize_wav(script, str(self.benchmark_dir / output_file))
        logger.info("Benchmark run complete.")

    def synthesize_wav(self, script: Union[str, List[Dict]], output_path: str, chunk_size: int = 10) -> None:
        final_audio = self.synthesize_to_memory(script, chunk_size)
        if final_audio.size > 0:
            sf.write(output_path, final_audio, SAMPLE_RATE)
            logger.info(f"Audio saved to {output_path}")
        else:
            logger.warning("No audio generated, WAV file not created.")
