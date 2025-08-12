# vibe_type.py

import gui.tray_icon
import core.hotkey_handler

def main():
    """Main function to start VibeType."""
    print("Starting VibeType...")

    # Start the global hotkey listener
    core.hotkey_handler.start_hotkey_listener()

    # Create the system tray icon
    # This is a blocking call that will run until the app exits
    gui.tray_icon.create_tray_icon()

    print("VibeType stopped.")

if __name__ == "__main__":
    main()
