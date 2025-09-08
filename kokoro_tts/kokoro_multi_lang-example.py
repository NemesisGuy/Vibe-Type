# kokoro_multi_lang-example.py - this is a example of a working lang select, with the japanese ect all working corelky
import gradio as gr
import numpy as np
import os
from kokoro_onnx import Kokoro
from misaki import en, ja, espeak # <-- The correct, official phonemizers

# --- 1. Master Configuration ---
MODEL_PATH = "onnx/english/kokoro-v1.0.onnx"
VOICES_PATH = "onnx/english/voices-v1.0.bin"
SAMPLE_RATE = 24000

# This config links the UI to the correct misaki phonemizer codes.
LANGUAGE_CONFIG = {
    "English (US)": {"lang_code": "a", "g2p_british": False, "example": "The quick brown fox jumps over the lazy dog."},
    "English (UK)": {"lang_code": "b", "g2p_british": True, "example": "A shining example of a true gentleman."},
    "Japanese": {"lang_code": "j", "example": "すべての人間は、生まれながらにして自由であり、かつ、尊厳"},
    "Spanish": {"lang_code": "e", "espeak_lang": "es", "example": "Esto es una prueba."},
    "French": {"lang_code": "f", "espeak_lang": "fr-fr", "example": "Ceci est un test."},
    "Hindi": {"lang_code": "h", "espeak_lang": "hi", "example": "यह एक परीक्षण है।"},
    "Italian": {"lang_code": "i", "espeak_lang": "it", "example": "Questa è una prova."},
    "Portuguese (BR)": {"lang_code": "p", "espeak_lang": "pt-br", "example": "Isto é um teste."},
}

# --- 2. Correct Initialization ---
# Use kokoro-onnx ONLY for loading, and misaki ONLY for phonemizing.
g2p_cache = {}

try:
    print("Loading Kokoro model and voices... This may take a moment.")
    if not os.path.exists(MODEL_PATH): raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    if not os.path.exists(VOICES_PATH): raise FileNotFoundError(f"Voices not found: {VOICES_PATH}")
    
    # This is the ONLY thing we use kokoro-onnx for.
    kokoro = Kokoro(MODEL_PATH, VOICES_PATH)
    ALL_VOICES = sorted(kokoro.get_voices())
    print(f"Model and {len(ALL_VOICES)} voices loaded successfully.")
    
except Exception as e:
    raise RuntimeError(f"Failed to initialize the Kokoro library. Error: {e}")

# --- 3. Correct Phonemizer and Synthesis Logic ---

def get_g2p_pipeline(lang_code: str):
    """Initializes and caches the correct Misaki G2P pipeline for each language."""
    if lang_code in g2p_cache: return g2p_cache[lang_code]
    
    print(f"Initializing G2P for lang_code '{lang_code}'...")
    if lang_code in ['a', 'b']:
        cfg = next(c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code)
        pipeline = en.G2P(british=cfg['g2p_british'])
    elif lang_code == 'j':
        pipeline = ja.JAG2P()
    else: # e, f, h, i, p use espeak
        cfg = next(c for c in LANGUAGE_CONFIG.values() if c['lang_code'] == lang_code)
        pipeline = espeak.EspeakG2P(language=cfg['espeak_lang'])
        
    g2p_cache[lang_code] = pipeline
    return pipeline

def update_voices_and_text(language_name: str):
    """Correctly filters the voices based on the selected language."""
    config = LANGUAGE_CONFIG[language_name]
    lang_code = config["lang_code"]
    filtered_voices = [v for v in ALL_VOICES if v.startswith(lang_code)]
    if not filtered_voices:
        gr.Warning(f"No voices found for language code '{lang_code}'. Showing all voices.")
        filtered_voices = ALL_VOICES
    return gr.Dropdown(choices=filtered_voices, value=filtered_voices[0]), config["example"]

def generate_speech(text: str, language_name: str, voice_name: str, speed: float):
    if not all([text, language_name, voice_name]):
        return (SAMPLE_RATE, np.zeros(0)), "Error: Missing input."
    try:
        config = LANGUAGE_CONFIG[language_name]
        lang_code = config["lang_code"]
        
        # Step 1: Use the correct, dedicated misaki phonemizer.
        g2p = get_g2p_pipeline(lang_code)
        
        # Step 2: Get the phonemes. misaki has different return types, so we handle it.
        result = g2p(text)
        phonemes = result[0] if isinstance(result, tuple) else result
        
        if not phonemes:
            return (SAMPLE_RATE, np.zeros(0)), "Error: Could not generate phonemes."
        
        # Step 3: Use the kokoro object to generate audio from the correct phonemes.
        samples, _ = kokoro.create(phonemes, voice=voice_name, speed=speed, is_phonemes=True)
        
        if samples.size == 0:
            return (SAMPLE_RATE, np.zeros(0)), "Warning: Generated audio was empty."
            
        return (SAMPLE_RATE, samples), phonemes
    except Exception as e:
        raise gr.Error(str(e))

# --- 4. Gradio Interface ---

with gr.Blocks(title="Kokoro TTS") as app:
    gr.Markdown("# Kokoro Multi-Lingual TTS Demo")
    gr.Markdown("Using the v1.0 ONNX model, `kokoro-onnx` for loading, and `misaki` for phonemization.")
    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(label="Input Text", lines=5)
            lang_selector = gr.Dropdown(choices=list(LANGUAGE_CONFIG.keys()), label="Language", value="English (US)")
            with gr.Row():
                voice_selector = gr.Dropdown(label="Voice")
                speed_slider = gr.Slider(minimum=0.5, maximum=2.0, value=1.0, step=0.1, label="Speed")
            generate_button = gr.Button("Generate Audio", variant="primary")
        with gr.Column(scale=1):
            audio_output = gr.Audio(label="Generated Speech", autoplay=True)
            phoneme_output = gr.Textbox(label="Generated Phonemes", interactive=False)
            
    app.load(fn=update_voices_and_text, inputs=lang_selector, outputs=[voice_selector, text_input])
    lang_selector.change(fn=update_voices_and_text, inputs=lang_selector, outputs=[voice_selector, text_input])
    generate_button.click(fn=generate_speech, inputs=[text_input, lang_selector, voice_selector, speed_slider], outputs=[audio_output, phoneme_output])

if __name__ == "__main__":
    app.launch()