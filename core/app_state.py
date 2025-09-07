# core/app_state.py

import threading
import re
import pyautogui
import time

# Import from core
import core.audio_capture
import core.transcription
import core.text_injection
import core.clipboard_manager
import core.transcript_saver
import core.tts
import core.ai
from core.config_manager import load_config
from core.analytics import increment_usage

# --- State & Command Queue ---
is_recording = False
is_ai_dictation_session = False
command_queue = None  # The GUI will set this queue.
status_callback = None # For tray icon updates

print("--- core/app_state.py: LATEST STABLE VERSION IS RUNNING ---") # DIAGNOSTIC

def _strip_markdown_for_speech(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'#+\s', '', text)
    text = re.sub(r'-\s', '', text)
    text = re.sub(r'>\s', '', text)
    return text

def _update_status(status: str):
    print(f"Status update: {status}")
    if status_callback:
        status_callback(f"VibeType - {status}")

def _submit_to_ai(text: str, mode: str):
    """Helper function to handle the common logic of sending text to the AI and processing the response."""
    config = load_config()
    _update_status("AI Processing")
    active_provider = config.get('active_ai_provider', 'Unknown')
    increment_usage("ai_provider_usage", active_provider)
    increment_usage("ai_mode_usage", mode)

    final_text = core.ai.get_ai_response(text, mode=mode)
    print(f"Final text after AI processing: {final_text}")

    if config.get('enable_text_injection', True):
        core.text_injection.inject_text(final_text)

    core.clipboard_manager.copy_to_clipboard(final_text)
    core.transcript_saver.save_transcript(f"Original: {text}\nAI: {final_text}")

    # Use the 'speak_response' setting from the Ollama provider config
    if config.get('ai_providers', {}).get('Ollama', {}).get('speak_response', True):
        active_tts_provider = config.get('active_tts_provider', 'Unknown')
        if config.get('tts_providers', {}).get(active_tts_provider, {}).get('enabled'):
            _update_status("Speaking")
            increment_usage("tts_engine_usage", active_tts_provider)
            text_for_speech = _strip_markdown_for_speech(final_text)
            core.tts.speak_text(text_for_speech)

def _processing_task(is_ai_task: bool, mode_override: str = None):
    _update_status("Transcribing")
    transcribed_text = core.transcription.transcribe_audio("temp_recording.wav")
    print(f"Transcription result: {transcribed_text}")

    if transcribed_text and "error" not in transcribed_text.lower():
        config = load_config()
        final_text = transcribed_text

        if is_ai_task:
            mode = mode_override if mode_override else config.get('active_prompt', 'Chat')
            _submit_to_ai(transcribed_text, mode)
        else:
            # Standard dictation: just inject/copy/save/speak the transcript
            if config.get('enable_text_injection', True):
                core.text_injection.inject_text(final_text)
            
            core.clipboard_manager.copy_to_clipboard(final_text)
            core.transcript_saver.save_transcript(f"Original: {transcribed_text}")

            if config.get('audio', {}).get('speak_transcription_result', True):
                active_tts_provider = config.get('active_tts_provider', 'Unknown')
                if config.get('tts_providers', {}).get(active_tts_provider, {}).get('enabled'):
                    _update_status("Speaking")
                    increment_usage("tts_engine_usage", active_tts_provider)
                    text_for_speech = _strip_markdown_for_speech(final_text)
                    core.tts.speak_text(text_for_speech)
    
    _update_status("Idle")
    print("Processing thread finished.")

def _read_smart_task():
    """Saves clipboard, copies selected text, speaks it. If no text is selected, it speaks the original clipboard content."""
    original_clipboard = core.clipboard_manager.get_clipboard_content()
    try:
        core.clipboard_manager.copy_to_clipboard('') # Clear clipboard to ensure we get the new selection
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1) # Wait for clipboard to update
        selected_text = core.clipboard_manager.get_clipboard_content()

        text_to_speak = None
        source = ""
        if selected_text:
            text_to_speak = selected_text
            source = "selected text"
        elif original_clipboard:
            text_to_speak = original_clipboard
            source = "clipboard"

        if text_to_speak:
            config = load_config()
            active_tts_provider = config.get('active_tts_provider', 'Unknown')
            increment_usage("tts_engine_usage", active_tts_provider)
            text_for_speech = _strip_markdown_for_speech(text_to_speak)
            print(f"Reading from {source}: '{text_for_speech[:50]}...'")
            _update_status("Speaking")
            core.tts.speak_text(text_for_speech)
        else:
            core.tts.speak_text("No text selected and clipboard is empty.")
        
        time.sleep(1) # Give a moment for speech to start

    except Exception as e:
        print(f"ERROR in _read_smart_task: {e}")
        core.tts.speak_text("Error reading text.")
    finally:
        if original_clipboard is not None:
            core.clipboard_manager.copy_to_clipboard(original_clipboard)
        _update_status("Idle")

def _process_text_from_selection_or_clipboard_task(mode_override: str = None):
    """Task to get text from selection or clipboard and process it with AI."""
    try:
        # 1. Get text to process
        original_clipboard = core.clipboard_manager.get_clipboard_content()
        core.clipboard_manager.copy_to_clipboard('')
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1)
        text_to_process = core.clipboard_manager.get_clipboard_content()
        source = "selected text"

        # Fallback to clipboard if no text was selected
        if not text_to_process and original_clipboard:
            text_to_process = original_clipboard
            source = "clipboard"
        
        # Restore clipboard
        if original_clipboard is not None:
            core.clipboard_manager.copy_to_clipboard(original_clipboard)

        if not text_to_process:
            print("No text selected or in clipboard. Nothing to process.")
            _update_status("Idle")
            return

        # 2. Process it
        print(f"Processing {source} with AI...")
        config = load_config()
        mode = mode_override if mode_override else config.get('active_prompt', 'Chat')
        _submit_to_ai(text_to_process, mode)
        
        _update_status("Idle")
    except Exception as e:
        print(f"Error in _process_text_from_selection_or_clipboard_task: {e}")
        _update_status("Idle")

# --- Public Functions ---
def toggle_dictation(is_ai_dictation: bool = False, mode_override: str = None):
    global is_recording, is_ai_dictation_session
    increment_usage("hotkey_usage", "toggle_dictation")
    if not is_recording:
        print("Starting dictation...")
        is_ai_dictation_session = is_ai_dictation
        core.audio_capture.start_capture()
        is_recording = True
        _update_status("Listening")
    else:
        print("Stopping dictation...")
        core.audio_capture.stop_capture()
        is_recording = False
        processing_thread = threading.Thread(target=_processing_task, args=(is_ai_dictation_session, mode_override))
        processing_thread.start()

def speak_from_clipboard():
    increment_usage("hotkey_usage", "speak_from_clipboard")
    threading.Thread(target=_read_smart_task, daemon=True).start()

def process_clipboard_with_ai():
    """Processes selected text or clipboard content with the user's active AI prompt."""
    increment_usage("hotkey_usage", "process_clipboard_with_ai")
    threading.Thread(target=_process_text_from_selection_or_clipboard_task, args=(None,), daemon=True).start()

def explain_selected_text():
    """Processes selected text or clipboard content with the 'Explain' AI prompt."""
    increment_usage("hotkey_usage", "explain_selected_text")
    threading.Thread(target=_process_text_from_selection_or_clipboard_task, args=("Explain",), daemon=True).start()

def summarize_text():
    """Processes selected text or clipboard content with the 'Summarize' AI prompt."""
    increment_usage("hotkey_usage", "summarize_text")
    threading.Thread(target=_process_text_from_selection_or_clipboard_task, args=("Summarize",), daemon=True).start()

def correct_text():
    """Processes selected text or clipboard content with the 'Correct' AI prompt."""
    increment_usage("hotkey_usage", "correct_text")
    threading.Thread(target=_process_text_from_selection_or_clipboard_task, args=("Correct",), daemon=True).start()

def read_selected_text():
    increment_usage("hotkey_usage", "read_selected_text")
    threading.Thread(target=_read_smart_task, daemon=True).start()

def start_voice_conversation():
    """Starts a voice conversation using the 'Chat' AI prompt."""
    increment_usage("hotkey_usage", "start_voice_conversation")
    toggle_dictation(is_ai_dictation=True, mode_override="Chat")

def interrupt_speech():
    """Interrupts any ongoing or queued speech."""
    increment_usage("hotkey_usage", "interrupt_speech")
    core.tts.stop_speech()

def register_command_queue(q):
    global command_queue
    command_queue = q

def register_status_callback(callback):
    """Registers a callback function to receive status updates."""
    global status_callback
    status_callback = callback
