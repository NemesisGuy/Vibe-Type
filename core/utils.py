# core/utils.py

import sys
import os

def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, ensuring correct path separators.
    This works for both development and for a PyInstaller bundle.
    """
    try:
        # PyInstaller creates a temporary folder and stores its path in _MEIPASS.
        base_path = sys._MEIPASS
    except AttributeError:
        # Not running in a PyInstaller bundle, so the base path is the project root.
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Join the paths and then normalize them to use the correct OS-specific separator.
    # This fixes the mixed slash issue (e.g., 'C:/path/to/bin/whisper').
    return os.path.normpath(os.path.join(base_path, relative_path))

def get_config_path() -> str:
    """
    Get the path to the user-specific configuration file.
    This should be in a writable directory, like the user's home folder.
    """
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".VibeType")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.normpath(os.path.join(config_dir, "config.json"))
