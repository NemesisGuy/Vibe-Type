# core/text_injection.py

from pynput.keyboard import Controller
import time

# Initialize the keyboard controller
keyboard = Controller()

def inject_text(text):
    """
    Injects the given text by simulating keyboard presses.

    Args:
        text (str): The text to be injected.
    """
    if not text:
        return

    print(f"Injecting text: {text}")
    try:
        # Optional: Add a small delay to ensure the hotkey is released
        # and the correct window is focused before typing.
        time.sleep(0.1)

        # Simulate typing the text
        keyboard.type(text)
        print("Text injection successful.")
    except Exception as e:
        print(f"Error during text injection: {e}")
