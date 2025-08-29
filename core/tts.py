# core/tts.py

import threading
import pythoncom
import win32com.client
from playsound import playsound
from openai import OpenAI
import subprocess
import pyaudio
import numpy as np
import wave
import os
import webbrowser
import time
import json

from core.config_manager import load_config, save_config
from core.utils import get_resource_path
from kokoro_tts.kokoro_tts import KokoroTTS, SAMPLE_RATE as KOKORO_SAMPLE_RATE
from piper_tts.piper_tts import PiperTTS

# --- Globals ---
sapi_initialization_event = threading.Event()
available_sapi_voices_cache = []
kokoro_tts_instance = None
piper_tts_instance = None

# --- Private Helpers (Initialization with Fallback) ---

def _initialize_kokoro_tts():
    """Initializes the Kokoro TTS instance."""
    global kokoro_tts_instance
    if kokoro_tts_instance is not None:
        return

    print("Attempting to initialize Kokoro TTS...")
    try:
        config = load_config()
        kokoro_config = config.get('tts_providers', {}).get('Kokoro TTS', {})
        kokoro_tts_instance = KokoroTTS(
            model_dir=kokoro_config.get('model_dir'),
            model_file=kokoro_config.get('model_file')
        )
        print("Kokoro TTS initialized successfully.")
    except Exception as e:
        print(f"FATAL: Could not initialize Kokoro TTS engine: {e}")
        kokoro_tts_instance = None

def _initialize_piper_tts():
    """Initializes the Piper TTS instance with a graceful fallback to CPU."""
    global piper_tts_instance
    if piper_tts_instance is not None:
        return

    print("Attempting to initialize Piper TTS...")
    config = load_config()
    piper_config = config.get('tts_providers', {}).get('Piper TTS', {})
    hardware_config = config.get('hardware', {})
    model_file = piper_config.get('model')

    if not model_file:
        print("No Piper model configured.")
        return

    model_path = get_resource_path(os.path.join("models", "piper", model_file))
    preferred_provider = hardware_config.get('piper_execution_provider', 'CPU')

    try:
        print(f"Trying Piper TTS with provider: {preferred_provider}")
        piper_tts_instance = PiperTTS(
            model_path=model_path,
            execution_provider=preferred_provider
        )
        print("Piper TTS initialized successfully.")
    except Exception as e:
        print(f"WARN: Failed to initialize Piper TTS with {preferred_provider}: {e}")
        if preferred_provider != 'CPU':
            print("Attempting fallback to CPU for Piper TTS...")
            try:
                piper_tts_instance = PiperTTS(
                    model_path=model_path,
                    execution_provider='CPU'
                )
                print("Piper TTS initialized successfully on CPU fallback.")
            except Exception as e_cpu:
                print(f"FATAL: Could not initialize Piper TTS engine on CPU fallback: {e_cpu}")
                piper_tts_instance = None
        else:
            piper_tts_instance = None

def _sapi_worker():
    """A dedicated worker for caching SAPI voices."""
    global available_sapi_voices_cache
    speaker = None
    try:
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        voices = speaker.GetVoices()
        available_sapi_voices_cache = [(voices.Item(i).GetDescription(), i) for i in range(voices.Count)]
    except Exception as e:
        print(f"FATAL: Could not initialize SAPI voice engine: {e}")
    finally:
        sapi_initialization_event.set()
        if speaker: pythoncom.CoUninitialize()

def _play_pyaudio_stream(audio_data, sample_rate, channels=1, device_index=None):
    if audio_data is None or audio_data.size == 0:
        print("Error: No audio data to play.")
        return
    
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=device_index
        )
        stream.write(audio_data.astype(np.float32).tobytes())
        stream.stop_stream()
        stream.close()
    except Exception as e:
        print(f"Error during PyAudio playback: {e}")
    finally:
        pa.terminate()

# --- Public API ---

def get_available_sapi_voices():
    if not sapi_initialization_event.wait(timeout=10.0):
        print("Warning: SAPI voice cache initialization timed out.")
    return available_sapi_voices_cache or []

def get_kokoro_voices():
    _initialize_kokoro_tts()
    return kokoro_tts_instance.list_voices() if kokoro_tts_instance else []

def get_kokoro_models():
    _initialize_kokoro_tts()
    return kokoro_tts_instance.list_models() if kokoro_tts_instance else []

def get_piper_model_files():
    models_path = get_resource_path("models/piper")
    if not os.path.exists(models_path):
        return []
    return [f for f in os.listdir(models_path) if f.endswith('.onnx')]

def get_voices_for_piper_model(model_file: str):
    if not model_file:
        return []
    try:
        model_path = get_resource_path(os.path.join("models", "piper", model_file))
        config_path = f"{model_path}.json"
        with open(config_path, 'r', encoding='utf-8') as fp:
            config = json.load(fp)
        speaker_map = config.get('speaker_id_map', {})
        return list(speaker_map.keys())
    except Exception as e:
        print(f"Could not load voices for model {model_file}: {e}")
        return []

def get_output_devices():
    pa = pyaudio.PyAudio()
    devices = {}
    try:
        for i in range(pa.get_device_count()):
            dev_info = pa.get_device_info_by_index(i)
            if dev_info['maxOutputChannels'] > 0:
                devices[f"{i}: {dev_info['name']}"] = i
    except Exception as e:
        print(f"Could not query audio devices: {e}")
        return {"No devices found": -1}
    finally:
        pa.terminate()
    return devices

def play_test_sound(device_index=None):
    speak_text("This is a test of the text to speech system.", override_device_index=device_index)

def trigger_kokoro_model_download():
    """Triggers the download of Kokoro TTS models in a separate thread."""
    def task():
        print("Starting Kokoro TTS model download...")
        _initialize_kokoro_tts()
        if kokoro_tts_instance:
            kokoro_tts_instance.download_models()
            print("Kokoro TTS model download finished.")
        else:
            print("Kokoro TTS instance not available. Download failed.")
    threading.Thread(target=task, daemon=True).start()

def trigger_kokoro_benchmark():
    """Triggers a Kokoro TTS benchmark run."""
    def task():
        _initialize_kokoro_tts()
        if kokoro_tts_instance:
            kokoro_tts_instance.run_benchmark()
    threading.Thread(target=task, daemon=True).start()

def open_benchmark_folder():
    """Opens the benchmark folder in the system's file explorer."""
    path = os.path.abspath("kokoro_tts/benchmarks")
    try:
        os.makedirs(path, exist_ok=True)
        webbrowser.open(path)
    except Exception as e:
        print(f"Could not open benchmarks folder: {e}")

def test_sapi_voice(text: str, voice_index: int, rate: int, volume: int):
    def task():
        if voice_index is None:
            print("Error: No SAPI voice selected for testing.")
            return

        print(f"Testing SAPI voice index {voice_index} at rate {rate} and volume {volume}...")
        try:
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            voices = speaker.GetVoices()
            if 0 <= voice_index < voices.Count:
                speaker.Voice = voices.Item(voice_index)
                speaker.Rate = rate
                speaker.Volume = volume
                speaker.Speak(text)
            else:
                print(f"Error: SAPI voice index {voice_index} is out of range.")
        except Exception as e:
            print(f"An unexpected error occurred during SAPI voice test: {e}")
        finally:
            pythoncom.CoUninitialize()
    threading.Thread(target=task, daemon=True).start()

def test_openai_voice(text: str, voice: str, api_key: str, speed: float):
    """A dedicated function to test a specific OpenAI voice."""
    def task():
        if not api_key:
            print("OpenAI API key is not set. Cannot test voice.")
            return
            
        print(f"Testing OpenAI voice '{voice}': '{text[:50]}...'")
        try:
            client = OpenAI(api_key=api_key)
            
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                speed=speed
            )
            
            temp_file = get_resource_path("temp_openai_speech.mp3")
            response.stream_to_file(temp_file)
            playsound(temp_file)
            os.remove(temp_file)

        except Exception as e:
            print(f"An unexpected error occurred during OpenAI voice test: {e}")
    threading.Thread(target=task, daemon=True).start()

def test_kokoro_voice(text: str, voice: str, device_index: int = None):
    """A dedicated function to test a specific Kokoro voice on a specific device."""
    def task():
        _initialize_kokoro_tts()
        if not kokoro_tts_instance:
            print("Kokoro TTS is not initialized. Cannot speak.")
            return

        print(f"Testing Kokoro voice '{voice}' on device {device_index}: '{text[:50]}...'")
        script = [{"text": text, "voice": voice}]
        try:
            audio_data = kokoro_tts_instance.synthesize_to_memory(script)
            _play_pyaudio_stream(audio_data, KOKORO_SAMPLE_RATE, device_index=device_index)
        except Exception as e:
            print(f"An unexpected error occurred during Kokoro voice test: {e}")

    threading.Thread(target=task, daemon=True).start()

def test_piper_voice(text: str, model_file: str, voice_name: str = None, length_scale: float = 1.0, device_index: int = None):
    """A dedicated function to test a specific Piper voice on a specific device."""
    def task():
        print(f"Testing Piper model '{model_file}' with voice '{voice_name}' on device {device_index}...")
        try:
            config = load_config()
            hardware_config = config.get('hardware', {})
            model_path = get_resource_path(os.path.join("models", "piper", model_file))
            
            piper_instance = PiperTTS(
                model_path=model_path,
                execution_provider=hardware_config.get('piper_execution_provider', 'CPU')
            )
            
            audio_data, sample_rate = piper_instance.synthesize_to_memory(text, speaker_name=voice_name, length_scale=length_scale)
            _play_pyaudio_stream(audio_data, sample_rate, device_index=device_index)
        except Exception as e:
            print(f"An unexpected error occurred during Piper voice test: {e}")
    threading.Thread(target=task, daemon=True).start()

def _speak_sapi(text: str, config: dict, device_index: int = None):
    try:
        sapi_config = config.get('tts_providers', {}).get('Windows SAPI', {})
        voice_index = sapi_config.get('voice_index', 0)
        rate = sapi_config.get('rate', 0)
        volume = sapi_config.get('volume', 100)
        
        pythoncom.CoInitialize()
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        voices = speaker.GetVoices()
        
        if voice_index is not None and 0 <= voice_index < voices.Count:
            speaker.Voice = voices.Item(voice_index)
        else:
            print(f"Warning: SAPI voice index {voice_index} is invalid. Using default voice.")
        
        speaker.Rate = rate
        speaker.Volume = volume
        speaker.Speak(text)

    except Exception as e:
        print(f"An unexpected error occurred with SAPI TTS: {e}")
    finally:
        pythoncom.CoUninitialize()

def _speak_openai(text: str, config: dict, device_index: int = None):
    try:
        openai_config = config.get('tts_providers', {}).get('OpenAI', {})
        api_key = openai_config.get('api_key')
        if not api_key:
            print("OpenAI API key is not configured.")
            return

        client = OpenAI(api_key=api_key)
        voice = openai_config.get('voice', 'alloy')
        speed = openai_config.get('speed', 1.0)
        
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text,
            speed=speed
        )
        
        temp_file = get_resource_path("temp_openai_speech.mp3")
        response.stream_to_file(temp_file)
        playsound(temp_file)
        os.remove(temp_file)

    except Exception as e:
        print(f"An unexpected error occurred with OpenAI TTS: {e}")

def _speak_kokoro(text: str, config: dict, device_index: int = None):
    _initialize_kokoro_tts()
    if not kokoro_tts_instance:
        print("Kokoro TTS is not initialized. Cannot speak.")
        return

    try:
        kokoro_config = config.get('tts_providers', {}).get('Kokoro TTS', {})
        voice = kokoro_config.get('voice', 'en_us_cmu_arctic_slt')
        script = [{"text": text, "voice": voice}]
        audio_data = kokoro_tts_instance.synthesize_to_memory(script)
        _play_pyaudio_stream(audio_data, KOKORO_SAMPLE_RATE, device_index=device_index)
    except Exception as e:
        print(f"An unexpected error occurred with Kokoro TTS: {e}")

def _speak_piper(text: str, config: dict, device_index: int = None):
    _initialize_piper_tts()
    if not piper_tts_instance:
        print("Piper TTS is not initialized. Cannot speak.")
        return

    try:
        piper_config = config.get('tts_providers', {}).get('Piper TTS', {})
        speaker_name = piper_config.get('voice') 
        length_scale = piper_config.get('length_scale', 1.0)

        audio_data, sample_rate = piper_tts_instance.synthesize_to_memory(
            text, 
            speaker_name=speaker_name,
            length_scale=length_scale
        )
        _play_pyaudio_stream(audio_data, sample_rate, device_index=device_index)

    except Exception as e:
        print(f"An unexpected error occurred with Piper TTS: {e}")

def speak_text(text: str, override_device_index: int = None):
    def task():
        if not text:
            return

        config = load_config()
        provider = config.get('active_tts_provider', 'Windows SAPI')
        provider_config = config.get('tts_providers', {}).get(provider, {})

        if not provider_config.get('enabled'):
            print(f"TTS provider '{provider}' is disabled.")
            return

        device_index = override_device_index
        if device_index is None:
            device_index = config.get('audio', {}).get('output_device_index')

        print(f"Speaking via {provider} on device {device_index}: '{text[:50]}...'")

        engine_map = {
            'Windows SAPI': _speak_sapi,
            'OpenAI': _speak_openai,
            'Kokoro TTS': _speak_kokoro,
            'Piper TTS': _speak_piper
        }
        
        speak_function = engine_map.get(provider)
        if speak_function:
            speak_function(text, config, device_index=device_index)
        else:
            print(f"Error: Unknown TTS provider '{provider}'.")

    threading.Thread(target=task, daemon=True).start()

# --- Start SAPI Initialization ---
sapi_init_thread = threading.Thread(target=_sapi_worker, daemon=True)
sapi_init_thread.start()
