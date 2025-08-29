# core/audio_capture.py

import pyaudio
import wave
import threading
from core.config_manager import load_config

# --- Globals ---
stop_recording_event = threading.Event()
recording_thread = None

# --- Private Functions ---
def _get_audio_parameters():
    """Loads audio parameters from the config."""
    config = load_config()
    return {
        "format": pyaudio.paInt16,
        "channels": 1,
        "rate": 16000,
        "chunk_size": 1024,
        "device_index": config.get('input_device_index')
    }

def _record_audio_task(output_filename: str):
    """The actual recording task, run in a separate thread."""
    params = _get_audio_parameters()
    audio = pyaudio.PyAudio()
    stream = None
    wave_file = None

    try:
        print(f"Starting recording on device index: {params['device_index']}")
        stream = audio.open(
            format=params["format"],
            channels=params["channels"],
            rate=params["rate"],
            input=True,
            frames_per_buffer=params["chunk_size"],
            input_device_index=params["device_index"]
        )
        
        wave_file = wave.open(output_filename, 'wb')
        wave_file.setnchannels(params["channels"])
        wave_file.setsampwidth(audio.get_sample_size(params["format"]))
        wave_file.setframerate(params["rate"])

        print("Recording started.")
        while not stop_recording_event.is_set():
            data = stream.read(params["chunk_size"])
            wave_file.writeframes(data)

        print("Recording stopped.")

    except Exception as e:
        print(f"An error occurred during recording: {e}")
    finally:
        if stream:
            stream.stop_stream()
            stream.close()
        if audio:
            audio.terminate()
        if wave_file:
            wave_file.close()
        print(f"Recording saved to {output_filename}")

# --- Public Functions ---
def start_capture(output_filename: str = "temp_recording.wav"):
    """Starts the audio recording in a separate thread."""
    global recording_thread
    if recording_thread and recording_thread.is_alive():
        print("Recording is already in progress.")
        return

    stop_recording_event.clear()
    recording_thread = threading.Thread(target=_record_audio_task, args=(output_filename,), daemon=True)
    recording_thread.start()

def stop_capture():
    """Stops the audio recording."""
    if not (recording_thread and recording_thread.is_alive()):
        print("No recording is currently in progress.")
        return

    stop_recording_event.set()
    recording_thread.join(timeout=2.0) # Wait for the thread to finish
    if recording_thread.is_alive():
        print("Warning: Recording thread did not terminate cleanly.")
