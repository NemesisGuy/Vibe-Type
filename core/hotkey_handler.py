# core/hotkey_handler.py

from pynput import keyboard
import threading
import traceback

# Import from core
from core.config_manager import load_config
from core.app_state import (
    toggle_dictation, 
    speak_from_clipboard, 
    process_clipboard_with_ai,
    explain_selected_text,
    read_selected_text,
    start_voice_conversation
)

listener_thread = None

def _sanitize_hotkey_string(hotkey_string: str) -> str:
    """
    Converts a user-friendly hotkey string into the format required by pynput.
    Example: "alt + shift + a" -> "<alt>+<shift>+a"
    """
    if not hotkey_string:
        return None
    # If it already seems to be in the correct format, just return it
    if '<' in hotkey_string and '>' in hotkey_string:
        return hotkey_string.lower()
    
    # Otherwise, parse and format it
    sanitized_parts = []
    parts = hotkey_string.split('+')
    for part in parts:
        part = part.strip().lower()
        if len(part) > 1:
            sanitized_parts.append(f"<{part}>")
        else:
            sanitized_parts.append(part)
            
    return '+'.join(sanitized_parts)

def _start_listener():
    """Initializes the pynput listener with all configured hotkeys from the config file."""
    try:
        config = load_config()
        
        action_map = {
            "toggle_dictation": lambda: toggle_dictation(is_ai_dictation=False),
            "ai_dictation": lambda: toggle_dictation(is_ai_dictation=True),
            "speak_clipboard": speak_from_clipboard,
            "process_clipboard": process_clipboard_with_ai,
            "explain_text": explain_selected_text,
            "read_text": read_selected_text,
            "voice_conversation": start_voice_conversation,
        }

        hotkeys_to_listen = {}
        configured_hotkeys = config.get('hotkeys', {})

        for action_name, action_func in action_map.items():
            hotkey_list = configured_hotkeys.get(action_name, [])
            for hotkey_string in hotkey_list:
                sanitized_hotkey = _sanitize_hotkey_string(hotkey_string)
                if sanitized_hotkey:
                    if sanitized_hotkey in hotkeys_to_listen:
                        print(f"Warning: Duplicate hotkey '{sanitized_hotkey}' detected. It will only be mapped to the first action found.")
                    else:
                        hotkeys_to_listen[sanitized_hotkey] = action_func

        if not hotkeys_to_listen:
            print("No hotkeys configured. Listener will not start.")
            return

        print(f"Attempting to start GlobalHotKeys listener for: {list(hotkeys_to_listen.keys())}")
        
        with keyboard.GlobalHotKeys(hotkeys_to_listen) as h:
            h.join()
            
    except Exception as e:
        print(f"FATAL ERROR in hotkey listener thread: {e}")
        traceback.print_exc()

def start_hotkey_listener():
    """Starts the global hotkey listener in a separate daemon thread."""
    global listener_thread
    if listener_thread is None or not listener_thread.is_alive():
        print("Starting hotkey listener thread...")
        listener_thread = threading.Thread(target=_start_listener, daemon=True)
        listener_thread.start()
    else:
        print("Hotkey listener already running.")
