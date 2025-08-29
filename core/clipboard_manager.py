# core/clipboard_manager.py

import pyperclip
from .config_manager import load_config

def copy_to_clipboard(text: str):
    """
    Copies the given text to the system clipboard, if not disabled by privacy settings.
    """
    config = load_config()
    if config.get('privacy', {}).get('clipboard_privacy', False):
        print("Clipboard access is disabled in settings.")
        return

    try:
        pyperclip.copy(text)
        print(f"Copied to clipboard: '{text[:50]}...'")
    except Exception as e:
        print(f"Error copying to clipboard: {e}")

def get_clipboard_content() -> str | None:
    """
    Reads text from the system clipboard, if not disabled by privacy settings.
    Returns the clipboard text or None if access is disabled or clipboard is empty.
    """
    config = load_config()
    if config.get('privacy', {}).get('clipboard_privacy', False):
        print("Clipboard access is disabled in settings.")
        return None
    
    try:
        return pyperclip.paste()
    except Exception as e:
        print(f"Error reading from clipboard: {e}")
        return None
