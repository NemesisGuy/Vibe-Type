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

class VibePiperTTS:
    """
    A complete Piper TTS engine for the VibeType application,
    supporting saving, streaming, and true seamless paragraph streaming.
    """
    def __init__(self, model_path: str):
        # ... (init code is the same as before, no changes needed)
        config_path = f"{model_path}.json"
        if not os.path.exists(model_path): raise FileNotFoundError(f"Model file not found: {model_path}")
        if not os.path.exists(config_path): raise FileNotFoundError(f"Config file not found: {config_path}")
        print(f"Initializing VibePiperTTS with model: {os.path.basename(model_path)}")
        with open(config_path, 'r', encoding='utf-8') as fp:
            self.config: dict = json.load(fp)
        self.sample_rate: int = self.config['audio']['sample_rate']
        self.phoneme_id_map: dict = self.config['phoneme_id_map']
        self._voices: dict = self.config.get('speaker_id_map', {})
        EspeakWrapper.set_library(espeakng_loader.get_library_path())
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
        self.sess = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        self.sess_inputs_names = [i.name for i in self.sess.get_inputs()]
        print("Engine ready.")

    def _get_speaker_id(self, speaker_name: str) -> int | None:
        # ... (this helper method is the same)
        if not speaker_name: return None
        if not self._voices: return None
        if speaker_name not in self._voices: raise ValueError(f"Speaker '{speaker_name}' not found. Available: {list(self._voices.keys())}")
        return self._voices[speaker_name]

    def _synthesize_raw(self, text: str, speaker_id: int = None):
        # ... (core synthesis is the same)
        inference_cfg = self.config['inference']
        length_scale, noise_scale, noise_w = inference_cfg['length_scale'], inference_cfg['noise_scale'], inference_cfg['noise_w']
        phonemes_str = phonemize(text)
        phonemes = list(phonemes_str)
        phonemes.insert(0, _BOS)
        ids = self._phoneme_to_ids(phonemes)
        inputs = self._create_input(ids, length_scale, noise_w, noise_scale, speaker_id or 0)
        samples = self.sess.run(None, inputs)[0].squeeze((0,1)).squeeze()
        return samples, self.sample_rate

    def save_to_wav(self, text: str, output_path: str, speaker_name: str = None):
        """Synthesizes audio and saves it to a WAV file."""
        speaker_id = self._get_speaker_id(speaker_name)
        samples, sample_rate = self._synthesize_raw(text, speaker_id)
        sf.write(output_path, samples, sample_rate)

    def stream(self, text: str, speaker_name: str = None):
        """Synthesizes a single piece of text and plays it directly."""
        speaker_id = self._get_speaker_id(speaker_name)
        samples, sample_rate = self._synthesize_raw(text, speaker_id)
        sd.play(samples, sample_rate)
        sd.wait()

    def stream_paragraphs_seamlessly(self, paragraphs: list[str], speaker_name: str = None):
        """
        Synthesizes and plays a list of paragraphs with no gaps.
        It pre-synthesizes the next paragraph while the current one is playing.
        """
        audio_queue = queue.Queue()
        speaker_id = self._get_speaker_id(speaker_name)

        def player_thread_func():
            """This function runs in a separate thread and just plays audio from the queue."""
            while True:
                audio_chunk = audio_queue.get()
                if audio_chunk is None:  # Sentinel value to signal the end
                    break
                samples, sample_rate = audio_chunk
                sd.play(samples, sample_rate)
                sd.wait()

        player = threading.Thread(target=player_thread_func)
        player.start()

        # Prime the queue with the first paragraph to start playback immediately
        print("Synthesizing paragraph 1...")
        first_audio = self._synthesize_raw(paragraphs[0], speaker_id)
        audio_queue.put(first_audio)
        print("-> Playing paragraph 1...")

        # Loop through the rest of the paragraphs, synthesizing in the background
        for i, text in enumerate(paragraphs[1:]):
            print(f"   (Pre-synthesizing paragraph {i+2} in the background...)")
            next_audio = self._synthesize_raw(text, speaker_id)
            audio_queue.put(next_audio)
            print(f"-> Playing paragraph {i+2}...")

        # All paragraphs are in the queue, add the sentinel and wait for the player to finish
        audio_queue.put(None)
        player.join()
        print("Seamless playback complete.")

    # --- Internal helper methods ---
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