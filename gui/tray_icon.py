# gui/tray_icon.py

from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw
import core.audio_capture
import gui.settings_window
import threading

# Global state for the icon
icon = None

def create_image(width, height, color1, color2):
    # Create a dummy image for the icon
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        (width // 2, 0, width, height // 2),
        fill=color2)
    dc.rectangle(
        (0, height // 2, width // 2, height),
        fill=color2)

    return image

def start_dictation(icon):
    print("Starting dictation...")
    core.audio_capture.start_capture()
    icon.title = "VibeType - Listening"

def stop_dictation(icon):
    print("Stopping dictation...")
    core.audio_capture.stop_capture()
    icon.title = "VibeType - Idle"

def show_settings(icon):
    # Run the settings window in a separate thread to avoid blocking the tray icon
    settings_thread = threading.Thread(target=gui.settings_window.create_settings_window)
    settings_thread.start()

def exit_app(icon):
    print("Exiting VibeType...")
    icon.stop()

def create_tray_icon():
    """Creates and manages the system tray icon using pystray."""
    global icon
    
    # Create a dummy icon image
    image = create_image(64, 64, 'black', 'white')

    menu = (
        item('Start Dictation', lambda: start_dictation(icon)),
        item('Stop Dictation', lambda: stop_dictation(icon)),
        item('Settings', lambda: show_settings(icon)),
        item('Exit', lambda: exit_app(icon))
    )

    icon = pystray.Icon("VibeType", image, "VibeType - Idle", menu)
    icon.run()
