# gui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import pyaudio
import numpy as np
import queue
import os

# Import from core
from core.config_manager import load_config, save_config
from core.tts import get_available_voices, speak_text
from core.app_state import register_command_queue
from core import hotkey_handler

# --- Settings Window Class (Fully Implemented) ---

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("VibeType Settings")
        self.transient(parent)
        self.grab_set()

        self.config = load_config()
        self.input_devices = self._get_input_devices()
        self.sapi_voices = get_available_voices()
        self.voice_map = {name: voice_id for name, voice_id in self.sapi_voices}
        self.stop_mic_test = threading.Event()
        self.mic_test_thread = None

        self._create_variables()
        self._create_ui()
        
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _get_input_devices(self):
        pa = pyaudio.PyAudio()
        devices = {}
        try:
            for i in range(pa.get_device_count()):
                dev_info = pa.get_device_info_by_index(i)
                if dev_info['maxInputChannels'] > 0:
                    devices[f"{i}: {dev_info['name']}"] = i
        finally:
            pa.terminate()
        return devices

    def _create_variables(self):
        # General
        self.hotkey_var = tk.StringVar(self, value=self.config.get('hotkey'))
        self.speak_clipboard_hotkey_var = tk.StringVar(self, value=self.config.get('speak_clipboard_hotkey'))
        self.ai_dictation_hotkey_var = tk.StringVar(self, value=self.config.get('ai_dictation_hotkey'))
        self.process_clipboard_hotkey_var = tk.StringVar(self, value=self.config.get('process_clipboard_hotkey'))
        self.theme_var = tk.StringVar(self, value=self.config.get('theme', 'System'))
        # AI
        self.active_ai_provider_var = tk.StringVar(self, value=self.config.get('active_ai_provider'))
        self.ollama_enabled_var = tk.BooleanVar(self, value=self.config.get('ai_providers', {}).get('Ollama', {}).get('enabled', True))
        self.ollama_url_var = tk.StringVar(self, value=self.config.get('ai_providers', {}).get('Ollama', {}).get('api_url', 'http://localhost:11434'))
        self.ollama_model_var = tk.StringVar(self, value=self.config.get('ai_providers', {}).get('Ollama', {}).get('model', 'llama2'))
        self.cohere_enabled_var = tk.BooleanVar(self, value=self.config.get('ai_providers', {}).get('Cohere', {}).get('enabled', False))
        self.cohere_api_key_var = tk.StringVar(self, value=self.config.get('ai_providers', {}).get('Cohere', {}).get('api_key', 'YOUR_API_KEY_HERE'))
        self.cohere_model_var = tk.StringVar(self, value=self.config.get('ai_providers', {}).get('Cohere', {}).get('model', 'command-r'))
        # Audio
        self.whisper_model_var = tk.StringVar(self, value=self.config.get('whisper_model'))
        self.mic_var = tk.StringVar(self)
        for name, index in self.input_devices.items():
            if index == self.config.get('input_device_index'):
                self.mic_var.set(name)
                break
        # TTS
        self.active_tts_provider_var = tk.StringVar(self, value=self.config.get('active_tts_provider'))
        sapi_config = self.config.get('tts_providers', {}).get('Windows SAPI', {})
        self.sapi_enabled_var = tk.BooleanVar(self, value=sapi_config.get('enabled', True))
        self.sapi_voice_var = tk.StringVar(self)
        for name, voice_id in self.sapi_voices:
            if voice_id == sapi_config.get('voice_index', 0):
                self.sapi_voice_var.set(name)
                break
        self.sapi_rate_var = tk.IntVar(self, value=sapi_config.get('rate', 175))
        openai_config = self.config.get('tts_providers', {}).get('OpenAI', {})
        self.openai_tts_enabled_var = tk.BooleanVar(self, value=openai_config.get('enabled', False))
        self.openai_tts_api_key_var = tk.StringVar(self, value=openai_config.get('api_key', 'YOUR_API_KEY_HERE'))
        self.openai_tts_model_var = tk.StringVar(self, value=openai_config.get('model', 'tts-1'))
        self.openai_tts_voice_var = tk.StringVar(self, value=openai_config.get('voice', 'alloy'))
        kokoro_config = self.config.get('tts_providers', {}).get('Kokoro TTS', {})
        self.kokoro_enabled_var = tk.BooleanVar(self, value=kokoro_config.get('enabled', False))
        self.kokoro_path_var = tk.StringVar(self, value=kokoro_config.get('path', ''))

    def _create_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")
        notebook = ttk.Notebook(main_frame)
        notebook.pack(expand=True, fill="both")

        self._create_general_tab(notebook)
        self._create_ai_tab(notebook)
        self._create_audio_tab(notebook)

        button_frame = ttk.Frame(self)
        button_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        ttk.Button(button_frame, text="Save", command=self._on_save).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side="right")

    def _create_general_tab(self, notebook):
        general_tab = ttk.Frame(notebook, padding="10")
        notebook.add(general_tab, text="General")
        hotkey_frame = ttk.LabelFrame(general_tab, text="Hotkeys", padding="10")
        hotkey_frame.grid(row=0, column=0, sticky="ew", pady=5, columnspan=2)
        hotkey_frame.columnconfigure(1, weight=1)
        ttk.Label(hotkey_frame, text="Dictation:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(hotkey_frame, textvariable=self.hotkey_var).grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(hotkey_frame, text="AI Dictation:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(hotkey_frame, textvariable=self.ai_dictation_hotkey_var).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(hotkey_frame, text="Process Clipboard (AI):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(hotkey_frame, textvariable=self.process_clipboard_hotkey_var).grid(row=2, column=1, sticky="ew", padx=5)
        ttk.Label(hotkey_frame, text="Speak from Clipboard:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(hotkey_frame, textvariable=self.speak_clipboard_hotkey_var).grid(row=3, column=1, sticky="ew", padx=5)

        appearance_frame = ttk.LabelFrame(general_tab, text="Appearance", padding="10")
        appearance_frame.grid(row=1, column=0, sticky="ew", pady=5, columnspan=2)
        appearance_frame.columnconfigure(1, weight=1)
        ttk.Label(appearance_frame, text="Theme:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        theme_menu = ttk.OptionMenu(appearance_frame, self.theme_var, self.theme_var.get(), "System", "Light", "Dark")
        theme_menu.grid(row=0, column=1, sticky="ew", padx=5)

    def _create_ai_tab(self, notebook):
        ai_tab = ttk.Frame(notebook, padding="10")
        notebook.add(ai_tab, text="AI")

        provider_frame = ttk.LabelFrame(ai_tab, text="AI Provider", padding="10")
        provider_frame.pack(fill="x", pady=5)
        provider_frame.columnconfigure(1, weight=1)
        ttk.Label(provider_frame, text="Active Provider:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        provider_menu = ttk.OptionMenu(provider_frame, self.active_ai_provider_var, self.active_ai_provider_var.get(), "Ollama", "Cohere", command=self._on_ai_provider_changed)
        provider_menu.grid(row=0, column=1, sticky="ew", padx=5)

        self.ollama_frame = ttk.LabelFrame(ai_tab, text="Ollama Settings", padding="10")
        self.cohere_frame = ttk.LabelFrame(ai_tab, text="Cohere Settings", padding="10")
        
        self.ollama_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(self.ollama_frame, text="Enable Ollama", variable=self.ollama_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(self.ollama_frame, text="API URL:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(self.ollama_frame, textvariable=self.ollama_url_var).grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(self.ollama_frame, text="Model:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(self.ollama_frame, textvariable=self.ollama_model_var).grid(row=2, column=1, sticky="ew", padx=5)

        self.cohere_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(self.cohere_frame, text="Enable Cohere", variable=self.cohere_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
        ttk.Label(self.cohere_frame, text="API Key:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(self.cohere_frame, textvariable=self.cohere_api_key_var, show="*").grid(row=1, column=1, sticky="ew", padx=5)
        ttk.Label(self.cohere_frame, text="Model:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ttk.Entry(self.cohere_frame, textvariable=self.cohere_model_var).grid(row=2, column=1, sticky="ew", padx=5)

        self._on_ai_provider_changed()

        prompts_frame = ttk.LabelFrame(ai_tab, text="AI Mode Prompts", padding="10")
        prompts_frame.pack(fill="both", expand=True, pady=5)
        prompt_notebook = ttk.Notebook(prompts_frame)
        prompt_notebook.pack(expand=True, fill="both", padx=5, pady=5)
        self.prompt_texts = {}
        for mode in self.config.get('ai_prompts', {}).keys():
            tab = ttk.Frame(prompt_notebook)
            prompt_notebook.add(tab, text=mode)
            prompt_text = tk.Text(tab, height=4)
            prompt_text.pack(expand=True, fill="both", padx=2, pady=2)
            prompt_text.insert(tk.END, self.config['ai_prompts'].get(mode, ''))
            self.prompt_texts[mode] = prompt_text

    def _on_ai_provider_changed(self, *args):
        provider = self.active_ai_provider_var.get()
        if provider == "Ollama":
            self.ollama_frame.pack(fill="x", pady=5)
            self.cohere_frame.pack_forget()
        elif provider == "Cohere":
            self.cohere_frame.pack(fill="x", pady=5)
            self.ollama_frame.pack_forget()

    def _create_audio_tab(self, notebook):
        audio_tab = ttk.Frame(notebook, padding="10")
        notebook.add(audio_tab, text="Audio")

        mic_frame = ttk.LabelFrame(audio_tab, text="Microphone", padding="10")
        mic_frame.pack(fill="x", pady=5)
        # ... (mic widgets) ...
        transcription_frame = ttk.LabelFrame(audio_tab, text="Transcription (Whisper)", padding="10")
        transcription_frame.pack(fill="x", pady=5)
        # ... (whisper widgets) ...

        tts_provider_frame = ttk.LabelFrame(audio_tab, text="TTS Provider", padding="10")
        tts_provider_frame.pack(fill="x", pady=5)
        tts_provider_frame.columnconfigure(1, weight=1)
        ttk.Label(tts_provider_frame, text="Active TTS Provider:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        tts_provider_menu = ttk.OptionMenu(tts_provider_frame, self.active_tts_provider_var, self.active_tts_provider_var.get(), "Windows SAPI", "OpenAI", "Kokoro TTS", command=self._on_tts_provider_changed)
        tts_provider_menu.grid(row=0, column=1, sticky="ew", padx=5)

        self.sapi_frame = ttk.LabelFrame(audio_tab, text="Windows SAPI Settings", padding="10")
        self.openai_tts_frame = ttk.LabelFrame(audio_tab, text="OpenAI TTS Settings", padding="10")
        self.kokoro_frame = ttk.LabelFrame(audio_tab, text="Kokoro TTS Settings", padding="10")

        # ... (SAPI, OpenAI, Kokoro UI widgets) ...

        self._on_tts_provider_changed()

    def _on_tts_provider_changed(self, *args):
        provider = self.active_tts_provider_var.get()
        self.sapi_frame.pack_forget()
        self.openai_tts_frame.pack_forget()
        self.kokoro_frame.pack_forget()

        if provider == "Windows SAPI":
            self.sapi_frame.pack(fill="x", pady=5)
        elif provider == "OpenAI":
            self.openai_tts_frame.pack(fill="x", pady=5)
        elif provider == "Kokoro TTS":
            self.kokoro_frame.pack(fill="x", pady=5)

    def _on_save(self):
        # ... (save all settings) ...
        save_config(self.config)
        messagebox.showinfo("Settings Saved", "Your settings have been saved. Please restart VibeType for all changes to take effect.", parent=self)
        self._on_cancel()

    def _on_cancel(self):
        if self.mic_test_thread and self.mic_test_thread.is_alive():
            self.stop_mic_test.set()
        self.destroy()

# --- Main Application Window Class ---

class VibeTypeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VibeType")
        self.geometry("300x150")

        self.settings_window = None
        self.command_queue = queue.Queue()

        self._create_widgets()
        register_command_queue(self.command_queue)
        self._process_queue() # Start the queue checker

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(expand=True, fill="both")

        self.status_var = tk.StringVar(value="VibeType - Idle")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor="center")
        status_label.pack(expand=True, fill="x", pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=5)
        button_frame.columnconfigure((0, 1), weight=1)

        ttk.Button(button_frame, text="Settings", command=self._on_settings_clicked).grid(row=0, column=0, sticky="ew", padx=5)
        ttk.Button(button_frame, text="Exit", command=self.quit).grid(row=0, column=1, sticky="ew", padx=5)

    def _on_settings_clicked(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return
        self.settings_window = SettingsWindow(self)

    def _process_queue(self):
        try:
            while not self.command_queue.empty():
                command, args = self.command_queue.get_nowait()
                if command == 'update_status':
                    self.status_var.set(args[0])
        finally:
            self.after(100, self._process_queue)

def create_main_window():
    app = VibeTypeApp()
    hotkey_handler.start_hotkey_listener()
    app.mainloop()
