# core/clipboard_manager.py

import pyperclip

def copy_to_clipboard(text):
    """
    Copies the given text to the system clipboard.

    Args:
        text (str): The text to be copied.
    """
    if not text:
        return

    try:
        pyperclip.copy(text)
        print("Text copied to clipboard.")
    except pyperclip.PyperclipException as e:
        print(f"Error copying to clipboard: {e}")
        print("Please ensure you have a clipboard utility installed, such as xclip or xsel on Linux.")
