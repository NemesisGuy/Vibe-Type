# gui/settings_window.py

import PySimpleGUI as sg
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')

def load_config():
    """Loads the configuration from config.json."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default values if file doesn't exist or is empty/corrupted
        return {
            "hotkey": "Ctrl+Shift+Space",
            "whisper_model": "base",
            "piper_tts_enabled": True,
            "ollama_api_url": "http://localhost:11434",
            "api_key": "",
            "language": "en"
        }

def save_config(config):
    """Saves the configuration to config.json."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def create_settings_window():
    """Creates and displays the settings window."""
    config = load_config()

    whisper_models = ['tiny', 'base', 'small', 'medium', 'large']

    layout = [
        [sg.Text("VibeType Settings")],
        [sg.Text("Hotkey"), sg.Input(config.get('hotkey', ''), key='-HOTKEY-')],
        [sg.Text("Whisper Model"), sg.Combo(whisper_models, default_value=config.get('whisper_model', 'base'), key='-WHISPER_MODEL-')],
        [sg.Checkbox("Enable Piper TTS", default=config.get('piper_tts_enabled', True), key='-PIPER_TTS-')],
        [sg.Text("Ollama API URL"), sg.Input(config.get('ollama_api_url', ''), key='-OLLAMA_URL-')],
        [sg.Text("API Key"), sg.Input(config.get('api_key', ''), key='-API_KEY-')],
        [sg.Text("Language"), sg.Input(config.get('language', 'en'), key='-LANGUAGE-')],
        [sg.Button("Save"), sg.Button("Cancel")]
    ]

    window = sg.Window("Settings", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "Save":
            config['hotkey'] = values['-HOTKEY-']
            config['whisper_model'] = values['-WHISPER_MODEL-']
            config['piper_tts_enabled'] = values['-PIPER_TTS-']
            config['ollama_api_url'] = values['-OLLAMA_URL-']
            config['api_key'] = values['-API_KEY-']
            config['language'] = values['-LANGUAGE-']
            save_config(config)
            break

    window.close()
