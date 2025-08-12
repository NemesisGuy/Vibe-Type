# vibe_type.py

import gui.tray_icon

# TODO: Import other core modules as needed

def main():
    """Main function to start VibeType."""
    print("Starting VibeType...")
    # TODO: Initialize core components (config, etc.)
    gui.tray_icon.create_tray_icon()
    print("VibeType stopped.")

if __name__ == "__main__":
    main()
