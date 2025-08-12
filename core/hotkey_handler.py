# core/hotkey_handler.py

from pynput import keyboard
import threading
import core.audio_capture
import core.transcription
from gui.tray_icon import icon

# --- State management ---
is_recording = False
listener_thread = None
hotkey_combination = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.KeyCode.from_char(' ')}
current_keys = set()

def on_press(key):
    """Callback function for key presses."""
    global is_recording
    if key in hotkey_combination:
        current_keys.add(key)
        if all(k in current_keys for k in hotkey_combination):
            if not is_recording:
                print("Hotkey activated - Starting dictation")
                core.audio_capture.start_capture()
                is_recording = True
                if icon:
                    icon.title = "VibeType - Listening"
            else:
                print("Hotkey activated - Stopping dictation")
                core.audio_capture.stop_capture()
                is_recording = False
                if icon:
                    icon.title = "VibeType - Transcribing"
                # TODO: This should be in a separate thread to not block the listener
                transcribed_text = core.transcription.transcribe_audio("temp_recording.wav")
                print(f"Transcription result: {transcribed_text}")
                if icon:
                    icon.title = "VibeType - Idle"


def on_release(key):
    """Callback function for key releases."""
    try:
        current_keys.remove(key)
    except KeyError:
        pass
    if key == keyboard.Key.esc:
        # Optional: Stop listener with escape key
        return False

def _start_listener():
    """Internal function to run the listener."""
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

def start_hotkey_listener():
    """Starts the hotkey listener in a separate thread."""
    global listener_thread
    if listener_thread is None or not listener_thread.is_alive():
        listener_thread = threading.Thread(target=_start_listener, daemon=True)
        listener_thread.start()
        print("Hotkey listener started.")

def stop_hotkey_listener():
    """Stops the hotkey listener."""
    # Pynput listeners run in their own threads and stopping them from the outside
    # is not straightforward. Since it's a daemon thread, it will exit when the main app exits.
    # For a graceful stop, we would need a more complex mechanism, e.g., raising an exception in the thread.
    # For now, we rely on the daemon nature of the thread.
    print("Hotkey listener is a daemon, it will stop with the main application.")
