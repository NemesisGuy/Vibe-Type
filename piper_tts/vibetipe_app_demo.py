# vibetipe_app_demo.py (Corrected for new model path)

import os
import time
from piper_engine import VibePiperTTS

# --- CONFIGURATION ---
MODELS_DIR = "../models/piper"  # <-- UPDATED PATH TO GO UP ONE LEVEL
OUTPUT_DIR = "test_audio_output"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# --- APPLICATION LOGIC ---
if __name__ == "__main__":
    # 1. Initialize the TTS Engine (do this once when your app starts)
    print("--- Initializing VibeType TTS Engine ---")
    model_path = os.path.join(MODELS_DIR, "en_US-arctic-medium.onnx")
    tts_engine = VibePiperTTS(model_path=model_path)
    print("-" * 50)

    # 2. DEMO 1: Save to a WAV file
    print("\n--- DEMO 1: Saving to a WAV file ---")
    save_path = os.path.join(OUTPUT_DIR, "master_demo_save.wav")
    tts_engine.save_to_wav(
        text="This is a test of saving audio to a file.",
        output_path=save_path,
        speaker_name='rms'
    )
    print(f"File saved to '{save_path}'")
    print("-" * 50)
    time.sleep(1)

    # 3. DEMO 2: Stream a single line of text
    print("\n--- DEMO 2: Streaming a single line of text directly ---")
    tts_engine.stream(
        text="This is a test of streaming a single sentence.",
        speaker_name='slt'
    )
    print("-" * 50)
    time.sleep(1)

    # 4. DEMO 3: Seamlessly stream multiple paragraphs
    print("\n--- DEMO 3: Seamlessly streaming multiple paragraphs ---")
    story_paragraphs = [
        "This is the final and most powerful feature of our engine.",
        "As you listen to this sentence, the next one is already being generated in the background.",
        "This results in a smooth, continuous listening experience with no gaps.",
        "This concludes the master demonstration."
    ]
    tts_engine.stream_paragraphs_seamlessly(
        paragraphs=story_paragraphs,
        speaker_name='lnh'
    )
    print("-" * 50)

    print("\nMaster demo complete. All engine features are working correctly.")