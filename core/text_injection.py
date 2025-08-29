# core/text_injection.py

from pynput.keyboard import Controller, Key
import pyperclip
import time

def inject_text(text: str):
    """
    Injects text using pynput for keyboard control, which can be more reliable
    than pyautogui on some systems.
    """
    if not text:
        print("No text to inject.")
        return

    print(f"Injecting text via pynput and clipboard: '{text}'")
    keyboard = Controller()

    try:
        # Save the current clipboard content
        original_clipboard = pyperclip.paste()

        # Copy the new text to the clipboard
        pyperclip.copy(text)

        # Give the clipboard a moment to update
        time.sleep(0.1)

        # Use pynput to simulate a paste command (Ctrl+V)
        print("Sending paste command via pynput...")
        with keyboard.pressed(Key.ctrl):
            keyboard.press('v')
            keyboard.release('v')
        print("Paste command sent.")

        # Restore the original clipboard content after a short delay
        time.sleep(0.5)
        pyperclip.copy(original_clipboard)
        print("Original clipboard content restored.")

    except Exception as e:
        print(f"An error occurred during pynput text injection: {e}")
        print("This could be a permissions issue with pynput.")
