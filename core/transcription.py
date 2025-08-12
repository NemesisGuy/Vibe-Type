# core/transcription.py

import whisper
from core.config_manager import config_manager

# --- Model Management ---
model = None

def load_whisper_model():
    """Loads the Whisper model specified in the config."""
    global model
    model_name = config_manager.get("whisper_model", "base")

    if model is not None and hasattr(model, 'name') and model.name == model_name:
        print(f"Whisper model '{model_name}' is already loaded.")
        return

    print(f"Loading Whisper model: {model_name}...")
    try:
        model = whisper.load_model(model_name)
        # Add the name attribute to the model object for later checks
        model.name = model_name
        print(f"Whisper model '{model_name}' loaded successfully.")
    except Exception as e:
        print(f"Error loading Whisper model '{model_name}': {e}")
        model = None

def transcribe_audio(audio_file_path):
    """
    Transcribes an audio file using the pre-loaded Whisper model.

    Args:
        audio_file_path (str): The path to the audio file to be transcribed.

    Returns:
        str: The transcribed text, or an error message if transcription fails.
    """
    if model is None:
        # Attempt to load the model if it's not loaded.
        load_whisper_model()
        if model is None:
            return "Whisper model not loaded. Transcription failed."

    print(f"Transcribing audio file: {audio_file_path}")
    try:
        result = model.transcribe(audio_file_path, fp16=False) # fp16=False for CPU-only
        transcribed_text = result['text']
        print(f"Transcription successful.")
        return transcribed_text
    except Exception as e:
        print(f"Error during transcription: {e}")
        return f"Error during transcription: {e}"

# Initial load of the model when the module is imported
load_whisper_model()
