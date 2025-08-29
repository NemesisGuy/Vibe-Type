# seamless_playback_demo.py (Corrected for new model path)

import os
from piper_engine import VibePiperTTS

# --- CONFIGURATION ---
MODELS_DIR = "../models/piper" # <-- UPDATED PATH TO GO UP ONE LEVEL

# --- APPLICATION LOGIC ---
if __name__ == "__main__":
    print("--- Initializing VibeType TTS Engine for Seamless Playback Demo ---")
    model_path = os.path.join(MODELS_DIR, "en_US-arctic-medium.onnx")
    tts_engine = VibePiperTTS(model_path=model_path)
    print("-" * 60)

    # A list of paragraphs to be read one after another without pausing
    story_paragraphs = [
        "Hello, and welcome to this demonstration.",
        "As you can hear, I am reading this first sentence.",
        "But while you were listening to that, the system was already preparing this second sentence.",
        "This creates a smooth, continuous flow of audio, which is perfect for reading longer texts.",
        "The final paragraph will now play, and the demo will conclude."
    ]

    print("Starting seamless playback. Please listen for any gaps between sentences...")

    # Call the new seamless streaming method
    tts_engine.stream_paragraphs_seamlessly(
        paragraphs=story_paragraphs,
        speaker_name='rms'
    )

    print("-" * 60)
    print("Demo complete. You should have heard a continuous stream of audio.")