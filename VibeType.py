# vibe_type.py

import tkinter as tk
import gui.theme_manager
from gui.tray_app import TrayApplication
from core import hotkey_handler

def main():
    """Main function to start VibeType with the correct, stable initialization order."""
    print("Starting VibeType...")

    # 1. Create the single, shared root window.
    root = tk.Tk()

    # 2. Apply the theme to this specific root window.
    gui.theme_manager.apply_theme(root)

    # 3. Hide the root window so the app is tray-only.
    root.withdraw()

    # 4. Create the application instance, passing it the themed root window.
    app = TrayApplication(root)

    # 5. Start the background hotkey listener.
    print("Starting hotkey listener...")
    hotkey_handler.start_hotkey_listener()

    # 6. Run the main application loop.
    print("Starting application main loop...")
    app.run()

    print("VibeType stopped.")

if __name__ == "__main__":
    main()

