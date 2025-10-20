# core/audio_capture.py

import pyaudio
import wave
import threading
import sys
from typing import Any, Dict

from core.config_manager import load_config

# --- Globals ---
stop_recording_event = threading.Event()
recording_thread = None

# --- Private Functions ---
def _coerce_device_info(device_info: Any) -> Dict[str, Any]:
    """Normalise persisted device info into a consistent mapping."""

    default_info: Dict[str, Any] = {
        "index": 0,
        "loopback": False,
        "channels": 1,
        "default_rate": 16000,
    }

    if isinstance(device_info, dict):
        info = default_info.copy()
        info.update({
            "index": device_info.get("index", 0),
            "loopback": bool(device_info.get("loopback", False)),
            "channels": max(1, int(device_info.get("channels", 1) or 1)),
        })
        if "default_rate" in device_info:
            try:
                info["default_rate"] = int(float(device_info["default_rate"]))
            except (TypeError, ValueError):
                pass
        if "rate" in device_info:
            try:
                info["rate"] = int(float(device_info["rate"]))
            except (TypeError, ValueError):
                pass
        return info

    try:
        index_value = int(device_info)
    except (TypeError, ValueError):
        index_value = 0
    return {"index": index_value, "loopback": False, "channels": 1, "default_rate": 16000}


def _get_audio_parameters(device_info: Any = None):
    """Loads audio parameters from the config, optionally overriding the device selection."""

    config = load_config()
    selected_info = device_info if device_info is not None else (
        config.get('input_device') or config.get('input_device_index')
    )
    info = _coerce_device_info(selected_info)

    # Loopback capture generally provides at least stereo output; default to 2 channels in that case.
    channels = max(1, int(info.get("channels", 1)))
    if info.get("loopback", False):
        channels = max(channels, 2)

    default_rate = 44100 if info.get("loopback", False) else 16000
    rate = info.get("rate") or info.get("default_rate") or default_rate
    try:
        rate_value = int(float(rate))
    except (TypeError, ValueError):
        rate_value = default_rate

    return {
        "format": pyaudio.paInt16,
        "channels": channels,
        "rate": rate_value,
        "chunk_size": 1024,
        "device_index": int(info.get("index", 0) or 0),
        "loopback": bool(info.get("loopback", False)),
    }


def _record_audio_task(output_filename: str, device_info: Any = None):
    """The actual recording task, run in a separate thread."""
    params = _get_audio_parameters(device_info=device_info)
    audio = pyaudio.PyAudio()
    stream = None
    wave_file = None

    try:
        print(f"Starting recording on device index: {params['device_index']}")
        stream_kwargs = dict(
            format=params["format"],
            channels=params["channels"],
            rate=params["rate"],
            input=True,
            frames_per_buffer=params["chunk_size"],
            input_device_index=params["device_index"],
        )
        if params.get("loopback") and sys.platform.startswith("win"):
            stream_kwargs["as_loopback"] = True  # type: ignore[assignment]
        stream = audio.open(**stream_kwargs)
        
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
def start_capture(output_filename: str = "temp_recording.wav", device_info: Any = None):
    """Starts the audio recording in a separate thread."""
    global recording_thread
    if recording_thread and recording_thread.is_alive():
        print("Recording is already in progress.")
        return

    stop_recording_event.clear()
    recording_thread = threading.Thread(
        target=_record_audio_task,
        args=(output_filename, device_info),
        daemon=True,
    )
    recording_thread.start()

def stop_capture():
    """Stops the audio recording."""
    global recording_thread
    if not (recording_thread and recording_thread.is_alive()):
        print("No recording is currently in progress.")
        return

    stop_recording_event.set()
    recording_thread.join(timeout=2.0) # Wait for the thread to finish
    if recording_thread.is_alive():
        print("Warning: Recording thread did not terminate cleanly.")
    else:
        recording_thread = None


def get_input_devices():
    """Enumerate available input-capable audio devices."""

    devices: Dict[str, Dict[str, Any]] = {}
    audio = pyaudio.PyAudio()
    try:
        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            name = info.get('name', f'Device {index}')
            max_input = int(info.get('maxInputChannels', 0) or 0)
            default_rate = int(float(info.get('defaultSampleRate', 16000) or 16000))
            if max_input > 0:
                label = f"{index}: {name}"
                devices[label] = {
                    "index": index,
                    "loopback": False,
                    "channels": max(1, max_input),
                    "default_rate": default_rate,
                }

        if sys.platform.startswith("win"):
            for index in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(index)
                name = info.get('name', f'Device {index}')
                max_output = int(info.get('maxOutputChannels', 0) or 0)
                default_rate = int(float(info.get('defaultSampleRate', 44100) or 44100))
                if max_output > 0:
                    label = f"{index}: {name} (Loopback)"
                    devices[label] = {
                        "index": index,
                        "loopback": True,
                        "channels": max(2, max_output),
                        "default_rate": default_rate,
                    }
    except Exception as exc:
        print(f"An error occurred while listing input devices: {exc}")
        if not devices:
            devices["No input devices found"] = {"index": -1, "loopback": False, "channels": 1}
    finally:
        audio.terminate()
    return devices
