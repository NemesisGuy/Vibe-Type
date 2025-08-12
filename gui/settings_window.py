# gui/settings_window.py

import PySimpleGUI as sg
import sounddevice as sd
import threading
from core.config_manager import config_manager
from core.hotkey_handler import restart_hotkey_listener
from core.transcription import load_whisper_model

def get_audio_devices():
    """Gets a list of available audio input devices."""
    try:
        devices = sd.query_devices()
        input_devices = [device['name'] for device in devices if device['max_input_channels'] > 0]
        return ["Default"] + input_devices
    except Exception as e:
        print(f"Could not get audio devices: {e}")
        return ["Default"]

def create_settings_window():
    """Creates and displays the settings window, managing application configuration."""

    # --- Data for UI ---
    whisper_models = ['tiny', 'base', 'small', 'medium'] # Removed 'large' as it's too big for most local setups
    output_modes = ['inject', 'clipboard', 'both']
    audio_devices = get_audio_devices()

    # --- Initial values from ConfigManager ---
    # Use 'Default' if no specific mic is set
    default_mic = config_manager.get('mic_device') or 'Default'
    if default_mic not in audio_devices:
        default_mic = "Default"

    current_config = {
        'hotkey': config_manager.get('hotkey', 'Ctrl+Alt+Space'),
        'whisper_model': config_manager.get('whisper_model', 'base'),
        'output_mode': config_manager.get('output_mode', 'inject'),
        'mic_device': default_mic,
        'auto_save': config_manager.get('auto_save_transcripts', True)
    }

    # --- UI Layout ---
    sg.theme('DarkBlue3')

    layout = [
        [sg.Text("VibeType Settings", font=("Helvetica", 16))],

        [sg.Frame("Audio & Transcription", [
            [sg.Text("Microphone", size=(15,1)), sg.Combo(audio_devices, default_value=current_config['mic_device'], key='-MIC-', readonly=True)],
            [sg.Text("Whisper Model", size=(15,1)), sg.Combo(whisper_models, default_value=current_config['whisper_model'], key='-MODEL-', readonly=True)],
        ])],

        [sg.Frame("Controls & Output", [
            [sg.Text("Activation Hotkey", size=(15,1)), sg.Input(current_config['hotkey'], key='-HOTKEY-')],
            [sg.Text("Output Mode", size=(15,1)), sg.Combo(output_modes, default_value=current_config['output_mode'], key='-OUTPUT-', readonly=True)],
            [sg.Checkbox("Auto-save transcripts to log file", default=current_config['auto_save'], key='-AUTOSAVE-')],
        ])],

        [sg.Button("Save"), sg.Button("Cancel")]
    ]

    window = sg.Window("Settings", layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "Save":
            # --- Check for changes that require restarts ---
            hotkey_changed = values['-HOTKEY-'] != config_manager.get('hotkey')
            model_changed = values['-MODEL-'] != config_manager.get('whisper_model')

            # --- Update config using ConfigManager ---
            config_manager.set('hotkey', values['-HOTKEY-'])
            config_manager.set('whisper_model', values['-MODEL-'])
            config_manager.set('output_mode', values['-OUTPUT-'])
            config_manager.set('mic_device', values['-MIC-'])
            config_manager.set('auto_save_transcripts', values['-AUTOSAVE-'])
            config_manager.save_config()

            sg.popup_auto_close("Settings saved!", auto_close_duration=2)

            # --- Apply changes ---
            if hotkey_changed:
                sg.popup_auto_close("Hotkey changed. Restarting listener...", auto_close_duration=2)
                restart_hotkey_listener()

            if model_changed:
                sg.popup_auto_close("Whisper model changed. This will be applied on next transcription.", auto_close_duration=3)
                # The transcription module will load the new model on its next run.
                # For immediate effect, we can call load_whisper_model() here in a thread.
                threading.Thread(target=load_whisper_model, daemon=True).start()

            break

    window.close()
