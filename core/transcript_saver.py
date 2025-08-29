# core/transcript_saver.py

import os
from datetime import datetime
from tkinter import messagebox
from core.utils import get_config_path
from core.config_manager import load_config

def _get_log_dir():
    """Returns the directory where transcripts are stored."""
    config_dir = os.path.dirname(get_config_path())
    return os.path.join(config_dir, "logs")

def _enforce_transcript_limit():
    """Deletes the oldest transcripts if the total number exceeds the configured limit."""
    try:
        config = load_config()
        limit = config.get('history', {}).get('transcript_limit', 100) # Default to 100
        if limit <= 0: # 0 or less means no limit
            return

        log_dir = _get_log_dir()
        if not os.path.exists(log_dir):
            return

        transcripts = sorted(
            [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.startswith('transcript_') and f.endswith('.txt')],
            key=os.path.getmtime
        )

        if len(transcripts) > limit:
            num_to_delete = len(transcripts) - limit
            for i in range(num_to_delete):
                os.remove(transcripts[i])
                print(f"Deleted old transcript: {transcripts[i]}")
    except Exception as e:
        print(f"Error enforcing transcript limit: {e}")

def save_transcript(transcript_content: str):
    """
    Saves the given transcript content to a log file and enforces the history limit.
    """
    try:
        log_dir = _get_log_dir()
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(log_dir, f"transcript_{timestamp}.txt")

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(transcript_content)
        print(f"Transcript saved to: {filename}")

        # Enforce the limit after saving
        _enforce_transcript_limit()

    except Exception as e:
        print(f"Error saving transcript: {e}")

def clear_transcript_history():
    """Deletes all saved transcript files."""
    if not messagebox.askyesno("Confirm Clear History", "Are you sure you want to permanently delete all transcript history?"):
        return

    try:
        log_dir = _get_log_dir()
        if not os.path.exists(log_dir):
            messagebox.showinfo("Success", "History is already empty.")
            return

        for filename in os.listdir(log_dir):
            if filename.startswith('transcript_') and filename.endswith('.txt'):
                os.remove(os.path.join(log_dir, filename))
        
        messagebox.showinfo("Success", "Transcript history has been cleared.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to clear transcript history.\n\nError: {e}")
