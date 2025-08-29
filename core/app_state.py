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

def _processing_task(is_ai_task: bool):
    _update_status("Transcribing")
    transcribed_text = core.transcription.transcribe_audio("temp_recording.wav")
    print(f"Transcription result: {transcribed_text}")

    if transcribed_text and "error" not in transcribed_text.lower():
        config = load_config()
        final_text = transcribed_text

        if is_ai_task and config.get('ai_providers', {}).get(config.get('active_ai_provider'), {}).get('enabled'):
            _update_status("AI Processing")
            active_provider = config.get('active_ai_provider', 'Unknown')
            active_mode = config.get('active_prompt', 'Unknown')
            increment_usage("ai_provider_usage", active_provider)
            increment_usage("ai_mode_usage", active_mode)
            final_text = core.ai.get_ai_response(transcribed_text)
            print(f"Final text after AI processing: {final_text}")
        
        if config.get('enable_text_injection', True):
            core.text_injection.inject_text(final_text)
        
        core.clipboard_manager.copy_to_clipboard(final_text)
        core.transcript_saver.save_transcript(f"Original: {transcribed_text}\nAI: {final_text}")

        if config.get('audio', {}).get('speak_transcription_result', True):
            active_tts_provider = config.get('active_tts_provider', 'Unknown')
            if config.get('tts_providers', {}).get(active_tts_provider, {}).get('enabled'):
                _update_status("Speaking")
                increment_usage("tts_engine_usage", active_tts_provider)
                text_for_speech = _strip_markdown_for_speech(final_text)
                core.tts.speak_text(text_for_speech)
    
    _update_status("Idle")
    print("Processing thread finished.")

def _speak_clipboard_task():
    try:
        clipboard_text = core.clipboard_manager.get_clipboard_content()
        if clipboard_text:
            config = load_config()
            active_tts_provider = config.get('active_tts_provider', 'Unknown')
            increment_usage("tts_engine_usage", active_tts_provider)
            text_for_speech = _strip_markdown_for_speech(clipboard_text)
            print(f"Speaking from clipboard: '{text_for_speech[:50]}...'")
            _update_status("Speaking")
            core.tts.speak_text(text_for_speech)
        else:
            print("Clipboard is empty or access is disabled. Nothing to speak.")
        _update_status("Idle")
    except Exception as e:
        print(f"Error in speak-from-clipboard task: {e}")
        _update_status("Idle")

def _read_selected_text_task():
    """Saves clipboard, copies selected text, speaks it, and restores clipboard."""
    original_clipboard = core.clipboard_manager.get_clipboard_content()
    try:
        core.clipboard_manager.copy_to_clipboard('') # Clear clipboard to ensure we get the new selection
        pyautogui.hotkey('ctrl', 'c')
        
        selected_text = None
        # Robustly wait for the clipboard to update
        for _ in range(10):
            time.sleep(0.05)
            selected_text = core.clipboard_manager.get_clipboard_content()
            if selected_text:
                break

        if selected_text:
            config = load_config()
            active_tts_provider = config.get('active_tts_provider', 'Unknown')
            increment_usage("tts_engine_usage", active_tts_provider)
            text_for_speech = _strip_markdown_for_speech(selected_text)
            print(f"Reading selected text: '{text_for_speech[:50]}...'")
            _update_status("Speaking")
            core.tts.speak_text(text_for_speech)
        else:
            core.tts.speak_text("No text selected or clipboard access disabled.")
        
        time.sleep(1) # Give a moment for speech to start

    except Exception as e:
        print(f"ERROR in read_selected_text_task: {e}")
        core.tts.speak_text("Error reading selected text.")
    finally:
        if original_clipboard is not None:
            core.clipboard_manager.copy_to_clipboard(original_clipboard)
        _update_status("Idle")

def _process_clipboard_task():
    try:
        _update_status("AI Processing Clipboard")
        clipboard_text = core.clipboard_manager.get_clipboard_content()
        if not clipboard_text:
            print("Clipboard is empty or access is disabled. Nothing to process.")
            _update_status("Idle")
            return

        config = load_config()
        active_provider = config.get('active_ai_provider', 'Unknown')
        active_mode = config.get('active_prompt', 'Unknown')
        increment_usage("ai_provider_usage", active_provider)
        increment_usage("ai_mode_usage", active_mode)
        final_text = core.ai.get_ai_response(clipboard_text)
        print(f"Final text after AI processing: {final_text}")
        
        if config.get('enable_text_injection', True):
            core.text_injection.inject_text(final_text)

        core.clipboard_manager.copy_to_clipboard(final_text)
        core.transcript_saver.save_transcript(f"Original: {clipboard_text}\nAI: {final_text}")

        if config.get('audio', {}).get('speak_transcription_result', True):
            active_tts_provider = config.get('active_tts_provider', 'Unknown')
            if config.get('tts_providers', {}).get(active_tts_provider, {}).get('enabled'):
                _update_status("Speaking")
                increment_usage("tts_engine_usage", active_tts_provider)
                text_for_speech = _strip_markdown_for_speech(final_text)
                core.tts.speak_text(text_for_speech)
        
        _update_status("Idle")
    except Exception as e:
        print(f"Error in process-clipboard task: {e}")
        _update_status("Idle")

# --- Public Functions ---
def toggle_dictation(is_ai_dictation: bool = False):
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
        processing_thread = threading.Thread(target=_processing_task, args=(is_ai_dictation_session,))
        processing_thread.start()

def speak_from_clipboard():
    increment_usage("hotkey_usage", "speak_from_clipboard")
    threading.Thread(target=_speak_clipboard_task, daemon=True).start()

def process_clipboard_with_ai():
    increment_usage("hotkey_usage", "process_clipboard_with_ai")
    threading.Thread(target=_process_clipboard_task, daemon=True).start()

def explain_selected_text():
    increment_usage("hotkey_usage", "explain_selected_text")
    threading.Thread(target=_process_clipboard_task, daemon=True).start()

def read_selected_text():
    increment_usage("hotkey_usage", "read_selected_text")
    threading.Thread(target=_read_selected_text_task, daemon=True).start()

def start_voice_conversation():
    increment_usage("hotkey_usage", "start_voice_conversation")
    toggle_dictation(is_ai_dictation=True)

def register_command_queue(q):
    global command_queue
    command_queue = q

def register_status_callback(callback):
    """Registers a callback function to receive status updates."""
    global status_callback
    status_callback = callback
