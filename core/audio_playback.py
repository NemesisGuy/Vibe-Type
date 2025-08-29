# core/audio_playback.py

import winsound
import threading

def play_audio_file(file_path: str):
    """
    Plays the specified .wav file in a separate thread.
    Uses the built-in winsound library for maximum stability on Windows.
    """
    def _play():
        try:
            print(f"Playing audio file: {file_path}")
            winsound.PlaySound(file_path, winsound.SND_FILENAME)
            print("Finished playing audio file.")
        except Exception as e:
            print(f"Error playing audio file: {e}")

    # Run in a daemon thread so it doesn't block the main application
    threading.Thread(target=_play, daemon=True).start()
