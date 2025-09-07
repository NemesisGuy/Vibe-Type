"""
VibeType - Kokoro TTS Voice Blending Example

This script provides a clear, isolated example of how to perform voice blending
using the kokoro-onnx library. It demonstrates the core concept of retrieving
voice embeddings, combining them with weighted averages, and using the resulting
custom embedding to synthesize speech.

This allows for experimentation with voice blending mechanics separately from the
main application's complexity.

Usage:
1. Make sure you have the necessary models in the `models/kokoro` directory.
2. Run the script from the project root:
   python kokoro_tts/voice_blending_example.py
3. An 'audio_blend_example.wav' file will be created in the project root.
"""
import os
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
import logging

# --- 1. Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "models/kokoro"
MODEL_FILE = "kokoro-v1.0.fp16.onnx"  # Using fp16 as a good balance
VOICES_FILE = "voices-v1.0.bin"

MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILE)
VOICES_PATH = os.path.join(MODEL_DIR, VOICES_FILE)

OUTPUT_FILENAME = "audio_blend_example.wav"

# --- 2. Initialization ---
logger.info("Loading Kokoro TTS model and voices...")
if not os.path.exists(MODEL_PATH) or not os.path.exists(VOICES_PATH):
    logger.error(f"Model or voices file not found in '{MODEL_DIR}'. Please ensure they are downloaded.")
    exit()

kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
logger.info("Model loaded successfully.")

# --- 3. Voice Blending Logic ---
logger.info("Performing voice blend...")
# Get the raw voice style embeddings for two different voices.
voice_1_embedding: np.ndarray = kokoro.get_voice_style("af_sky")
voice_2_embedding: np.ndarray = kokoro.get_voice_style("am_adam")

# Create a new voice by blending the two embeddings.
# Here, we are creating a 70/30 mix.
blended_voice_embedding = np.add(voice_1_embedding * 0.5, voice_2_embedding * 0.5)

# --- 4. Synthesis and Output ---
logger.info("Synthesizing audio with the blended voice...")
samples, sample_rate = kokoro.create(
    "Hello, this is a demonstration of a custom blended voice.The sky above the port was the color of television, tuned to a dead channel. ",
    voice=blended_voice_embedding, # Pass the blended embedding directly
    speed=1.0,
    lang="en-us",
)

sf.write(OUTPUT_FILENAME, samples, sample_rate)
logger.info(f"Successfully created blended audio file: '{OUTPUT_FILENAME}'")