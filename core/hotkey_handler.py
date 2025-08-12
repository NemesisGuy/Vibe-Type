# core/hotkey_handler.py

from pynput import keyboard
import threading
import core.audio_capture
import core.transcription
import core.text_injection
import core.clipboard_manager
import core.transcript_saver
from core.config_manager import config_manager
from gui.tray_icon import icon

# --- State management ---
is_recording = False
listener_thread = None
hotkey_combination = set()
current_keys = set()

def parse_hotkey(hotkey_str):
    """Parses a hotkey string like 'Ctrl+Alt+Space' into a set of pynput keys."""
    # This is a simplified parser. A more robust solution might be needed.
    key_map = {
        'ctrl': keyboard.Key.ctrl, 'alt': keyboard.Key.alt, 'shift': keyboard.Key.shift,
        'space': keyboard.Key.space, 'esc': keyboard.Key.esc, 'cmd': keyboard.Key.cmd,
        'f1': keyboard.Key.f1, 'f2': keyboard.Key.f2, 'f3': keyboard.Key.f3, 'f4': keyboard.Key.f4,
    }

    keys = set()
    # Be case-insensitive with key names
    parts = [part.strip().lower() for part in hotkey_str.split('+')]

    for part in parts:
        if part in key_map:
            keys.add(key_map[part])
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            # Attempt to find the key by name for other special keys
            try:
                keys.add(keyboard.Key[part])
            except KeyError:
                print(f"Warning: Unknown key '{part}' in hotkey configuration.")

    return keys

def _transcribe_task():
    """The actual transcription process, run in a separate thread."""
    print("Transcription thread started.")
    transcribed_text = core.transcription.transcribe_audio("temp_recording.wav")
    print(f"Transcription result: {transcribed_text}")

    if transcribed_text:
        # Check config for what to do with the text
        if config_manager.get("auto_save_transcripts", True):
            core.transcript_saver.save_transcript(transcribed_text)

        output_mode = config_manager.get("output_mode", "inject")
        if output_mode == "inject":
            core.text_injection.inject_text(transcribed_text)
        elif output_mode == "clipboard":
            core.clipboard_manager.copy_to_clipboard(transcribed_text)
        elif output_mode == "both":
            core.clipboard_manager.copy_to_clipboard(transcribed_text)
            core.text_injection.inject_text(transcribed_text)

    if icon:
        icon.title = "VibeType - Idle"
    print("Transcription thread finished.")

def on_press(key):
    """Callback function for key presses."""
    global is_recording, hotkey_combination

    if key in hotkey_combination:
        current_keys.add(key)
        if all(k in current_keys for k in hotkey_combination):
            # Prevent re-triggering if keys are held down
            if len(current_keys) == len(hotkey_combination):
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

                    transcription_thread = threading.Thread(target=_transcribe_task)
                    transcription_thread.start()

def on_release(key):
    """Callback function for key releases."""
    global is_recording
    if key in hotkey_combination:
        try:
            current_keys.remove(key)
        except KeyError:
            pass

    # If the key release breaks the combo, reset recording state if needed
    if not all(k in current_keys for k in hotkey_combination):
        # This part is tricky. For a toggle-style hotkey, we might not want to do anything on release.
        # The current logic toggles on press, so release logic is mainly for key state management.
        pass

    if key == keyboard.Key.esc:
        # Optional: Stop listener with escape key
        if is_recording:
            core.audio_capture.stop_capture()
            is_recording = False
            print("Recording stopped with Esc.")
        return False

def _start_listener_thread():
    """Internal function to run the listener."""
    global hotkey_combination, listener_thread
    hotkey_str = config_manager.get("hotkey", "Ctrl+Alt+Space")
    hotkey_combination = parse_hotkey(hotkey_str)

    if not hotkey_combination:
        print("Error: Hotkey is not configured correctly. Listener not started.")
        return

    print(f"Starting hotkey listener for: {hotkey_str}")
    # The listener object
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()
    # Keep the thread alive, and allow the listener to be stopped
    listener.join()
    print("Hotkey listener thread stopped.")


def start_hotkey_listener():
    """Starts the hotkey listener in a separate thread."""
    global listener_thread
    if listener_thread is None or not listener_thread.is_alive():
        listener_thread = threading.Thread(target=_start_listener_thread, daemon=True)
        listener_thread.start()
        print("Hotkey listener thread started.")

def stop_hotkey_listener():
    """Stops the hotkey listener."""
    # This is a bit of a hack. Pynput listeners are hard to stop from another thread.
    # Returning False from a callback is the 'official' way.
    # We can inject a key press to trigger this.
    if listener_thread and listener_thread.is_alive():
        print("Stopping hotkey listener...")
        # Inject an 'esc' key press to stop the listener
        controller = keyboard.Controller()
        controller.press(keyboard.Key.esc)
        controller.release(keyboard.Key.esc)
        listener_thread.join(timeout=1) # Wait for the thread to die
        listener_thread = None
        print("Hotkey listener stopped.")

def restart_hotkey_listener():
    """Restarts the listener to apply new hotkey settings."""
    stop_hotkey_listener()
    # Use a timer to avoid race conditions
    threading.Timer(0.5, start_hotkey_listener).start()
