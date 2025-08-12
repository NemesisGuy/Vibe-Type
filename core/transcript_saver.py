# core/transcript_saver.py

from datetime import datetime

def save_transcript(text, filename="transcripts.log"):
    """
    Appends the transcribed text with a timestamp to a log file.

    Args:
        text (str): The text to save.
        filename (str): The name of the file to save to.
    """
    if not text:
        return

    try:
        with open(filename, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {text}\n")
        print(f"Transcript saved to {filename}.")
    except IOError as e:
        print(f"Error saving transcript to {filename}: {e}")
