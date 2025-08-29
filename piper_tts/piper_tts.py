# piper_engine.py (with seamless streaming)

import os
import json
import onnxruntime as ort
import numpy as np
import sounddevice as sd
import soundfile as sf
from piper_onnx import phonemize
from phonemizer.backend.espeak.wrapper import EspeakWrapper
import espeakng_loader
import threading
import queue

_BOS, _EOS, _PAD = "^", "$", "_"

class PiperTTS:
    """
    A complete Piper TTS engine for the VibeType application,
    supporting saving, streaming, and true seamless paragraph streaming.
    """
    def __init__(self, model_path: str, execution_provider: str = 'CPUExecutionProvider'):
        config_path = f"{model_path}.json"
        if not os.path.exists(model_path): raise FileNotFoundError(f"Model file not found: {model_path}")
        if not os.path.exists(config_path): raise FileNotFoundError(f"Config file not found: {config_path}")
        print(f"Initializing PiperTTS with model: {os.path.basename(model_path)}")
        with open(config_path, 'r', encoding='utf-8') as fp:
            self.config: dict = json.load(fp)
        self.sample_rate: int = self.config['audio']['sample_rate']
        self.phoneme_id_map: dict = self.config['phoneme_id_map']
        self._voices: dict = self.config.get('speaker_id_map', {})
        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        self.sess = ort.InferenceSession(model_path, providers=[f"{execution_provider}ExecutionProvider"])
        self.sess_inputs_names = [i.name for i in self.sess.get_inputs()]
        print(f"Engine ready. Using: {execution_provider}")

    def list_voices(self) -> list[str]:
        """Returns a list of available voices."""
        return list(self._voices.keys())

    def _get_speaker_id(self, speaker_name: str) -> int | None:
        if not speaker_name: return None
        if not self._voices: return None
        if speaker_name not in self._voices: raise ValueError(f"Speaker '{speaker_name}' not found. Available: {list(self._voices.keys())}")
        return self._voices[speaker_name]

    def _synthesize_raw(self, text: str, speaker_id: int = None, length_scale: float = None):
        inference_cfg = self.config['inference']
        # Use provided length_scale or fall back to config
        final_length_scale = length_scale if length_scale is not None else inference_cfg['length_scale']
        noise_scale, noise_w = inference_cfg['noise_scale'], inference_cfg['noise_w']
        
        phonemes_str = phonemize(text)
        phonemes = list(phonemes_str)
        phonemes.insert(0, _BOS)
        ids = self._phoneme_to_ids(phonemes)
        inputs = self._create_input(ids, final_length_scale, noise_w, noise_scale, speaker_id or 0)
        samples = self.sess.run(None, inputs)[0].squeeze((0,1)).squeeze()
        return samples, self.sample_rate

    def synthesize_to_memory(self, text: str, speaker_name: str = None, length_scale: float = None):
        """Synthesizes audio and returns it as a numpy array."""
        speaker_id = self._get_speaker_id(speaker_name)
        return self._synthesize_raw(text, speaker_id, length_scale=length_scale)

    def save_to_wav(self, text: str, output_path: str, speaker_name: str = None, length_scale: float = None):
        """Synthesizes audio and saves it to a WAV file."""
        samples, sample_rate = self.synthesize_to_memory(text, speaker_name, length_scale=length_scale)
        sf.write(output_path, samples, sample_rate)

    def stream(self, text: str, speaker_name: str = None, length_scale: float = None):
        """Synthesizes a single piece of text and plays it directly."""
        samples, sample_rate = self.synthesize_to_memory(text, speaker_name, length_scale=length_scale)
        sd.play(samples, sample_rate)
        sd.wait()

    def _phoneme_to_ids(self, phonemes: list[str]) -> list[int]:
        ids = [self.phoneme_id_map[_BOS][0]]
        for p in phonemes:
            if p in self.phoneme_id_map:
                ids.extend(self.phoneme_id_map[p])
                ids.extend(self.phoneme_id_map[_PAD])
        ids.extend(self.phoneme_id_map[_EOS])
        return ids

    def _create_input(self, ids: list[int], length_scale, noise_w, noise_scale, sid: int) -> dict:
        ids = np.expand_dims(np.array(ids, dtype=np.int64), 0)
        length = np.array([ids.shape[1]], dtype=np.int64)
        scales = np.array([noise_scale, length_scale, noise_w],dtype=np.float32)
        if 'sid' in self.sess_inputs_names:
            sid = np.array([sid], dtype=np.int64)
            return {'input': ids, 'input_lengths': length, 'scales': scales, 'sid': sid}
        else:
            return {'input': ids, 'input_lengths': length, 'scales': scales}
