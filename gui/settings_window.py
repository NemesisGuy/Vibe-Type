# gui/settings_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
import json
import requests
import re
import shutil
import threading
import copy
import datetime as dt
from pathlib import Path
from typing import Any, Dict

# Import from core
from core.config_manager import load_config, save_config
from core.app_state import (
    register_mcp_log_callback,
    start_mcp,
    stop_mcp,
    restart_mcp,
    is_mcp_running,
    set_mcp_auto_start,
    get_mcp_log_history,
    clear_mcp_log_history,
)
from core.tts import (
    get_available_sapi_voices, get_kokoro_voices, get_output_devices,
    play_test_sound, speak_text, trigger_kokoro_model_download,
    open_benchmark_folder, get_kokoro_models, trigger_kokoro_benchmark,
    test_kokoro_voice, get_piper_model_files, get_voices_for_piper_model,
    test_sapi_voice, test_piper_voice, test_openai_voice, get_kokoro_languages,
    test_zipvoice_voice, get_zipvoice_samples, export_zipvoice_profile
)
from core.ai import test_ollama_connection, send_webhook_test, get_ai_response, get_ollama_models
from core.model_manager import delete_piper_model, import_piper_models
from core.transcript_saver import clear_transcript_history, open_transcript_history_folder
from core.analytics import load_analytics_data, reset_analytics_data
from core.performance_monitor import get_performance_metrics
from core.api_manager import start_api_server, stop_api_server, restart_api_server, is_api_running
from core.audio_capture import (
    start_capture as start_audio_capture,
    stop_capture as stop_audio_capture,
    get_input_devices,
)
from core.transcription import transcribe_audio
from core.zipvoice_manager import (
    blend_voice_profiles,
    open_zipvoice_samples_folder,
    ensure_samples_directory,
    ensure_profiles_directory,
    list_saved_profiles,
    open_zipvoice_profiles_folder,
    profile_path_for_name,
    delete_voice_profile,
)

def create_settings_window(parent: tk.Tk, on_save_callback=None):
    config = load_config()
    window = tk.Toplevel(parent)
    window.title("VibeType Settings")
    window.grab_set()

    # --- Style and Theme Setup ---
    style = ttk.Style(window)
    theme = config.get("theme", "System")
    try:
        if theme == "System" and os.name == 'nt':
            style.theme_use('vista')
        else:
            style.theme_use('default')

        theme_bg = style.lookup('TFrame', 'background')
        theme_fg = style.lookup('TLabel', 'foreground')
        entry_bg = style.lookup('TEntry', 'fieldbackground')
        button_bg = style.lookup('TButton', 'background')

        if theme == "Dark":
            theme_bg = "#2b2b2b"
            theme_fg = "#ffffff"
            entry_bg = "#3c3c3c"
            button_bg = "#555555"

        elif theme == "Light":
            theme_bg = "#ffffff"
            theme_fg = "#000000"
            entry_bg = "#ffffff"
            button_bg = "#f0f0f0"

        style_map = {
            '.': {'background': theme_bg, 'foreground': theme_fg},
            'TFrame': {'background': theme_bg},
            'TLabel': {'background': theme_bg, 'foreground': theme_fg},
            'TLabelFrame': {'background': theme_bg, 'foreground': theme_fg},
            'TLabelFrame.Label': {'background': theme_bg, 'foreground': theme_fg},
            'TCheckbutton': {'background': theme_bg, 'foreground': theme_fg, 'indicatorbackground': entry_bg, 'selectcolor': entry_bg},
            'TRadiobutton': {'background': theme_bg, 'foreground': theme_fg},
            'TNotebook': {'background': theme_bg},
            'TNotebook.Tab': {'background': theme_bg, 'foreground': theme_fg},
            'TScrollbar': {'background': theme_bg, 'troughcolor': entry_bg},
            'TEntry': {'fieldbackground': entry_bg, 'foreground': theme_fg, 'insertcolor': theme_fg},
            'TButton': {'foreground': theme_fg, 'background': button_bg},
        }
        for widget_style, options in style_map.items():
            style.configure(widget_style, **options)
            
        style.map("TNotebook.Tab", background=[("selected", entry_bg)], foreground=[("selected", theme_fg)])
        style.map('TButton', background=[('active', entry_bg)])
        style.configure("Conflict.TEntry", foreground="#000000", fieldbackground="#ffcccc")
        window.configure(background=theme_bg)

    except tk.TclError as e:
        print(f"Error applying theme: {e}. Falling back to basic colors.")
        theme_bg = "#2b2b2b" if theme == "Dark" else "#f0f0f0"
        window.configure(background=theme_bg)

    # --- Data and Maps ---
    output_devices = get_output_devices()
    input_devices = get_input_devices()
    sapi_voices = get_available_sapi_voices()
    sapi_voice_map = {desc: index for desc, index in sapi_voices}
    sapi_index_map = {index: desc for desc, index in sapi_voices}
    output_device_map = {name: index for name, index in output_devices.items()}
    output_index_map = {index: name for name, index in output_devices.items()}
    input_device_map = {name: info for name, info in input_devices.items()}

    # --- Helper Functions (defined early to avoid NameError) ---
    def get_selected_device_index():
        return output_device_map.get(speaker_desc_var.get())

    # --- Variables ---
    theme_var = tk.StringVar(window, value=config.get('theme', 'System'))
    enable_text_injection_var = tk.BooleanVar(window, value=config.get('enable_text_injection'))
    
    api_config = config.get('api', {})
    api_enabled_var = tk.BooleanVar(window, value=api_config.get('enabled', False))
    api_auto_start_var = tk.BooleanVar(window, value=api_config.get('auto_start', False))
    api_port_var = tk.IntVar(window, value=api_config.get('port', 5000))

    ollama_config = config.get('ai_providers', {}).get('Ollama', {})
    ollama_enabled_var = tk.BooleanVar(window, value=ollama_config.get('enabled', False))
    ollama_url_var = tk.StringVar(window, value=ollama_config.get('api_url', ''))
    ollama_model_var = tk.StringVar(window, value=ollama_config.get('model', ''))
    ai_speak_response_var = tk.BooleanVar(window, value=ollama_config.get('speak_response', True))
    use_thinking_fillers_var = tk.BooleanVar(window, value=ollama_config.get('use_thinking_fillers', False))
    webhook_enabled_var = tk.BooleanVar(window, value=ollama_config.get('webhook_enabled', False))
    webhook_url_var = tk.StringVar(window, value=ollama_config.get('webhook_url', ''))

    active_tts_provider_var = tk.StringVar(window, value=config.get('active_tts_provider'))
    
    sapi_config = config.get('tts_providers', {}).get('Windows SAPI', {})
    initial_sapi_voice_desc = sapi_index_map.get(sapi_config.get('voice_index', 0))
    sapi_voice_desc_var = tk.StringVar(window, value=initial_sapi_voice_desc)
    sapi_rate_var = tk.IntVar(window, value=sapi_config.get('rate', 0))
    sapi_volume_var = tk.IntVar(window, value=sapi_config.get('volume', 100))

    openai_config = config.get('tts_providers', {}).get('OpenAI', {})
    openai_enabled_var = tk.BooleanVar(window, value=openai_config.get('enabled', False))
    openai_api_key_var = tk.StringVar(window, value=openai_config.get('api_key', ''))
    openai_voice_var = tk.StringVar(window, value=openai_config.get('voice', 'alloy'))
    openai_speed_var = tk.DoubleVar(window, value=openai_config.get('speed', 1.0))

    kokoro_config = config.get('tts_providers', {}).get('Kokoro TTS', {})
    kokoro_enabled_var = tk.BooleanVar(window, value=kokoro_config.get('enabled', False))
    kokoro_model_file_var = tk.StringVar(window, value=kokoro_config.get('model_file'))
    kokoro_language_var = tk.StringVar(window, value=kokoro_config.get('language', 'English (US)'))
    kokoro_voice_var = tk.StringVar(window, value=kokoro_config.get('voice'))
    kokoro_enable_blending_var = tk.BooleanVar(window, value=kokoro_config.get('enable_voice_blending', False))
    kokoro_voice_2_var = tk.StringVar(window, value=kokoro_config.get('voice_2'))
    kokoro_voice_3_var = tk.StringVar(window, value=kokoro_config.get('voice_3'))
    kokoro_voice_4_var = tk.StringVar(window, value=kokoro_config.get('voice_4'))
    kokoro_voice_5_var = tk.StringVar(window, value=kokoro_config.get('voice_5'))
    kokoro_enable_voice_2_var = tk.BooleanVar(window, value=kokoro_config.get('enable_voice_2', False))
    kokoro_enable_voice_3_var = tk.BooleanVar(window, value=kokoro_config.get('enable_voice_3', False))
    kokoro_enable_voice_4_var = tk.BooleanVar(window, value=kokoro_config.get('enable_voice_4', False))
    kokoro_enable_voice_5_var = tk.BooleanVar(window, value=kokoro_config.get('enable_voice_5', False))
    kokoro_voice_weight_1_var = tk.DoubleVar(window, value=kokoro_config.get('voice_weight_1', 1.0))
    kokoro_voice_weight_2_var = tk.DoubleVar(window, value=kokoro_config.get('voice_weight_2', 1.0))
    kokoro_voice_weight_3_var = tk.DoubleVar(window, value=kokoro_config.get('voice_weight_3', 1.0))
    kokoro_voice_weight_4_var = tk.DoubleVar(window, value=kokoro_config.get('voice_weight_4', 1.0))
    kokoro_voice_weight_5_var = tk.DoubleVar(window, value=kokoro_config.get('voice_weight_5', 1.0))

    piper_config = config.get('tts_providers', {}).get('Piper TTS', {})
    piper_enabled_var = tk.BooleanVar(window, value=piper_config.get('enabled', False))
    piper_model_file_var = tk.StringVar(window, value=piper_config.get('model'))
    piper_voice_var = tk.StringVar(window, value=piper_config.get('voice'))
    piper_length_scale_var = tk.DoubleVar(window, value=piper_config.get('length_scale', 1.0))

    zipvoice_config = config.get('tts_providers', {}).get('ZipVoice TTS', {})
    zipvoice_samples = get_zipvoice_samples()
    zipvoice_samples_map = {sample.name: sample for sample in zipvoice_samples}
    zipvoice_display_to_name = {sample.display_name: sample.name for sample in zipvoice_samples}
    zipvoice_name_to_display = {sample.name: sample.display_name for sample in zipvoice_samples}

    default_zipvoice_sample = zipvoice_config.get('sample_name')
    if not default_zipvoice_sample or default_zipvoice_sample not in zipvoice_samples_map:
        default_zipvoice_sample = zipvoice_samples[0].name if zipvoice_samples else ""

    try:
        zipvoice_speed_value = float(zipvoice_config.get('speed', 1.0) or 1.0)
    except (TypeError, ValueError):
        zipvoice_speed_value = 1.0

    zipvoice_enabled_var = tk.BooleanVar(window, value=zipvoice_config.get('enabled', False))
    zipvoice_sample_var = tk.StringVar(window, value=default_zipvoice_sample)
    zipvoice_sample_display_var = tk.StringVar(
        window,
        value=zipvoice_name_to_display.get(default_zipvoice_sample, "No samples found" if not zipvoice_samples else zipvoice_samples[0].display_name)
    )
    zipvoice_model_var = tk.StringVar(window, value=zipvoice_config.get('model_name', 'zipvoice'))
    zipvoice_backend_var = tk.StringVar(window, value=(zipvoice_config.get('backend') or 'torch').lower())
    zipvoice_speed_var = tk.DoubleVar(window, value=zipvoice_speed_value)
    zipvoice_prompt_preview_var = tk.StringVar(window, value="")
    zipvoice_prompt_mode_default = zipvoice_config.get('prompt_mode', 'sample') or 'sample'
    if zipvoice_prompt_mode_default not in {"sample", "profile"}:
        zipvoice_prompt_mode_default = "sample"
    zipvoice_prompt_mode_var = tk.StringVar(window, value=zipvoice_prompt_mode_default)
    seed_config_value = zipvoice_config.get('seed')
    if isinstance(seed_config_value, int):
        seed_default = str(seed_config_value)
    else:
        seed_default = str(seed_config_value).strip() if isinstance(seed_config_value, str) else ""
    zipvoice_seed_var = tk.StringVar(window, value=seed_default)
    selected_profile_path = zipvoice_config.get('custom_prompt_profile', '') or ''
    inferred_profile_name = zipvoice_config.get('profile_name') or (Path(selected_profile_path).stem if selected_profile_path else "")
    zipvoice_profile_selection_var = tk.StringVar(window, value=inferred_profile_name)
    zipvoice_selected_profile_path_var = tk.StringVar(window, value=selected_profile_path)
    default_profile_name = inferred_profile_name or (default_zipvoice_sample or "my_voice")
    zipvoice_profile_name_var = tk.StringVar(window, value=default_profile_name)
    zipvoice_profile_status_var = tk.StringVar(window, value="")
    zipvoice_profiles_map: Dict[str, Dict[str, Any]] = {}
    zipvoice_blend_primary_var = tk.StringVar(window, value="")
    zipvoice_blend_secondary_var = tk.StringVar(window, value="")
    zipvoice_blend_weight_var = tk.DoubleVar(window, value=0.5)
    zipvoice_blend_name_var = tk.StringVar(window, value="blend_candidate")
    zipvoice_blend_status_var = tk.StringVar(window, value="")

    hardware_config = config.get('hardware', {})
    kokoro_execution_provider_var = tk.StringVar(window, value=hardware_config.get('kokoro_execution_provider', 'CPU'))
    piper_execution_provider_var = tk.StringVar(window, value=hardware_config.get('piper_execution_provider', 'CPU'))
    whisper_execution_provider_var = tk.StringVar(window, value=hardware_config.get('whisper_execution_provider', 'CPU'))

    audio_config = config.get('audio', {})
    initial_output_device_desc = output_index_map.get(audio_config.get('output_device_index'))

    stored_input_device = config.get('input_device')
    if not isinstance(stored_input_device, dict):
        stored_input_device = {
            'index': config.get('input_device_index', 0),
            'loopback': False,
        }

    def _matches_device(info: dict, stored: dict) -> bool:
        return (
            int(info.get('index', -1)) == int(stored.get('index', -1))
            and bool(info.get('loopback', False)) == bool(stored.get('loopback', False))
        )

    initial_input_device_desc = None
    for device_label, info in input_device_map.items():
        if _matches_device(info, stored_input_device):
            initial_input_device_desc = device_label
            break
    if initial_input_device_desc is None and input_device_map:
        initial_input_device_desc = next(iter(input_device_map.keys()))
    speaker_desc_var = tk.StringVar(window, value=initial_output_device_desc)
    speak_transcription_var = tk.BooleanVar(window, value=audio_config.get('speak_transcription_result', True))
    zipvoice_input_device_var = tk.StringVar(window, value=initial_input_device_desc)

    history_config = config.get('history', {})
    transcript_limit_var = tk.IntVar(window, value=history_config.get('transcript_limit', 100))

    hotkeys_vars = {action: [tk.StringVar(window, value=hk) for hk in hotkeys] for action, hotkeys in config.get('hotkeys', {}).items()}

    user_experience_config = config.get('user_experience', {})
    show_status_overlay_var = tk.BooleanVar(window, value=user_experience_config.get('show_status_overlay', True))

    privacy_config = config.get('privacy', {})
    clipboard_privacy_var = tk.BooleanVar(window, value=privacy_config.get('clipboard_privacy', False))
    local_only_mode_var = tk.BooleanVar(window, value=privacy_config.get('local_only_mode', False))
    enable_hotkeys_var = tk.BooleanVar(window, value=privacy_config.get('enable_hotkeys', True))
    enable_microphone_var = tk.BooleanVar(window, value=privacy_config.get('enable_microphone', True))

    # --- UI Layout ---
    main_frame = ttk.Frame(window, padding="10")
    main_frame.pack(expand=True, fill="both")
    notebook = ttk.Notebook(main_frame)
    notebook.pack(expand=True, fill="both")

    # --- Tabs ---
    tabs = {name: ttk.Frame(notebook, padding="10") for name in ["⚙️ General", "⌨️ Hotkeys", "🤖 AI", "🎤 Audio I/O", "🔊 Windows SAPI", "🤖 OpenAI TTS", "❤️ Kokoro TTS", "🐍 Piper TTS", "🧬 ZipVoice TTS", "🎙️ ZipVoice Samples", "🛠️ Hardware", "📦 Models", "🔐 Security & Privacy", "📊 Analytics", "🌐 API", "🛠️ MCP"]}
    for name, tab_frame in tabs.items():
        notebook.add(tab_frame, text=name)

    # --- General Tab ---
    ux_frame = ttk.LabelFrame(tabs["⚙️ General"], text="User Experience", padding="10")
    ux_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    ttk.Checkbutton(ux_frame, text="Show Status Overlay", variable=show_status_overlay_var).pack(anchor="w")
    ttk.Checkbutton(ux_frame, text="Enable Automatic Text Injection", variable=enable_text_injection_var).pack(anchor="w")

    appearance_frame = ttk.LabelFrame(tabs["⚙️ General"], text="Appearance", padding="10")
    appearance_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    appearance_frame.columnconfigure(1, weight=1)
    ttk.Label(appearance_frame, text="Theme:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(appearance_frame, theme_var, theme_var.get(), "System", "Light", "Dark").grid(row=0, column=1, sticky="ew", padx=5)

    history_frame = ttk.LabelFrame(tabs["⚙️ General"], text="History & Cache", padding="10")
    history_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    history_frame.columnconfigure(1, weight=1)
    ttk.Label(history_frame, text="Transcript History Limit (0 for unlimited):").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(history_frame, textvariable=transcript_limit_var, width=10).grid(row=0, column=1, sticky="w", padx=5)
    
    history_buttons_frame = ttk.Frame(history_frame)
    history_buttons_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky='w')
    ttk.Button(history_buttons_frame, text="View History", command=open_transcript_history_folder).pack(side="left", padx=5)
    ttk.Button(history_buttons_frame, text="Clear Transcript History", command=clear_transcript_history).pack(side="left", padx=5)

    # --- Hotkeys Tab ---
    hotkey_canvas = tk.Canvas(tabs["⌨️ Hotkeys"], bg=theme_bg, highlightthickness=0)
    hotkey_scrollbar = ttk.Scrollbar(tabs["⌨️ Hotkeys"], orient="vertical", command=hotkey_canvas.yview)
    hotkey_scrollable_frame = ttk.Frame(hotkey_canvas)
    hotkey_scrollable_frame.bind("<Configure>", lambda e: hotkey_canvas.configure(scrollregion=hotkey_canvas.bbox("all")))
    hotkey_canvas.create_window((0, 0), window=hotkey_scrollable_frame, anchor="nw")
    hotkey_canvas.configure(yscrollcommand=hotkey_scrollbar.set)
    hotkey_canvas.pack(side="left", fill="both", expand=True)
    hotkey_scrollbar.pack(side="right", fill="y")

    # Configure grid columns for horizontal wrapping
    max_columns = 3
    for i in range(max_columns):
        hotkey_scrollable_frame.columnconfigure(i, weight=1)
    
    action_frames, all_hotkey_entries = {}, []
    def check_for_conflicts():
        all_hotkeys = [entry.get() for entry in all_hotkey_entries if entry.get()]
        conflicts = {hk for hk in all_hotkeys if all_hotkeys.count(hk) > 1}
        for entry in all_hotkey_entries:
            entry.configure(style="Conflict.TEntry" if entry.get() in conflicts else "TEntry")

    def _redraw_action_frame(action):
        frame = action_frames[action]
        for widget in frame.winfo_children():
            widget.destroy()
        
        hotkey_vars_list = hotkeys_vars[action]
        for j, hotkey_var in enumerate(hotkey_vars_list):
            entry = ttk.Entry(frame, textvariable=hotkey_var)
            entry.grid(row=j, column=0, sticky="ew", padx=5, pady=2)
            entry.bind("<KeyRelease>", lambda e: check_for_conflicts())
            all_hotkey_entries.append(entry)
            remove_button = ttk.Button(frame, text="-", width=2, command=lambda a=action, v=hotkey_var: remove_hotkey(a, v))
            remove_button.grid(row=j, column=1, padx=5)
        add_button = ttk.Button(frame, text="+", width=2, command=lambda a=action: add_hotkey(a))
        add_button.grid(row=len(hotkey_vars_list), column=1, padx=5)
        check_for_conflicts()

    def add_hotkey(action):
        hotkeys_vars[action].append(tk.StringVar(window))
        _redraw_action_frame(action)

    def remove_hotkey(action, var_to_remove):
        hotkeys_vars[action].remove(var_to_remove)
        all_hotkey_entries[:] = [e for e in all_hotkey_entries if e.getvar(e['textvariable']) != var_to_remove.get()]
        _redraw_action_frame(action)

    # Grid layout for hotkey action frames
    row, col = 0, 0
    for action, hotkeys in hotkeys_vars.items():
        action_frame = ttk.LabelFrame(hotkey_scrollable_frame, text=action.replace('_', ' ').title(), padding="10")
        action_frame.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
        action_frame.columnconfigure(0, weight=1)
        action_frames[action] = action_frame
        _redraw_action_frame(action)
        
        col += 1
        if col >= max_columns:
            col = 0
            row += 1
            
    check_for_conflicts()

    # --- AI Tab ---
    ollama_frame = ttk.LabelFrame(tabs["🤖 AI"], text="AI Processing (Ollama)", padding="10")
    ollama_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    ollama_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(ollama_frame, text="Enable Ollama AI Processing", variable=ollama_enabled_var).grid(row=0, column=0, columnspan=3, sticky="w", padx=5)
    ttk.Label(ollama_frame, text="API URL:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(ollama_frame, textvariable=ollama_url_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
    
    ttk.Label(ollama_frame, text="Model Name:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    model_frame = ttk.Frame(ollama_frame)
    model_frame.grid(row=2, column=1, columnspan=2, sticky="ew")
    model_frame.columnconfigure(0, weight=1)
    ollama_model_menu = ttk.OptionMenu(model_frame, ollama_model_var, ollama_model_var.get() or "Select a model")
    ollama_model_menu.grid(row=0, column=0, sticky="ew", padx=5)

    def refresh_ollama_models():
        api_url = ollama_url_var.get()
        models = get_ollama_models(api_url)
        menu = ollama_model_menu["menu"]
        menu.delete(0, "end")
        if models:
            for model in models:
                menu.add_command(label=model, command=lambda value=model: ollama_model_var.set(value))
            if not ollama_model_var.get() or ollama_model_var.get() not in models:
                ollama_model_var.set(models[0])
        else:
            ollama_model_var.set("No models found")

    refresh_button = ttk.Button(model_frame, text="🔄", command=refresh_ollama_models, width=3)
    refresh_button.grid(row=0, column=1, padx=(0, 5))
    refresh_ollama_models() # Initial population

    test_button = ttk.Button(ollama_frame, text="Test Connection", command=lambda: test_ollama_connection(ollama_url_var.get()))
    test_button.grid(row=3, column=0, columnspan=3, pady=5)

    # Add thinking fillers checkbox
    ttk.Checkbutton(ollama_frame, text="Use thinking fillers (speaks phrases while AI processes)", variable=use_thinking_fillers_var).grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=2)

    ai_modes_frame = ttk.LabelFrame(tabs["🤖 AI"], text="AI Modes", padding="10")
    ai_modes_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    ai_modes_frame.columnconfigure(0, weight=1)

    ai_notebook = ttk.Notebook(ai_modes_frame)
    ai_notebook.pack(expand=True, fill="both", pady=5, padx=5)

    ai_mode_tabs = {}
    ai_prompt_entries = {}
    default_prompts = {
        "Summarize": "Summarize the following text, focusing on the key points and main ideas. Be concise and clear. Be concise , your response will be spoken via TTS exactly as you reply",
        "Explain": "Be concise, you are a helpful ai voice assistant , your response will be spoken via TTS exactly as you reply Explain the following text in simple and easy-to-understand terms. Use analogies or examples if helpful. Be concise , your response will be spoken via TTS exactly as you reply",
        "Correct": "Correct any grammatical errors, spelling mistakes, or typos in the following text. Preserve the original meaning. Be concise , your response will be spoken via TTS exactly as you reply",
        "Chat": "You are a helpful AI assistant. Respond to the user's query in a conversational and informative manner. Be concise , your response will be spoken via TTS exactly as you reply"
    }
    for mode in ["Summarize", "Explain", "Correct", "Chat"]:
        tab = ttk.Frame(ai_notebook, padding="10")
        ai_notebook.add(tab, text=mode)
        ai_mode_tabs[mode] = tab

        prompt_label = ttk.Label(tab, text=f"System Prompt for {mode} Mode:")
        prompt_label.pack(anchor="w")

        prompt_text = tk.Text(tab, height=8, width=60, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        prompt_text.pack(expand=True, fill="both", pady=(5,0))
        ai_prompt_entries[mode] = prompt_text

    for mode, text_widget in ai_prompt_entries.items():
        prompt = config.get('ai_providers', {}).get('Ollama', {}).get('prompts', {}).get(mode, default_prompts.get(mode, ''))
        text_widget.insert("1.0", prompt)

    ai_output_frame = ttk.LabelFrame(tabs["🤖 AI"], text="AI Output", padding="10")
    ai_output_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    ai_output_frame.columnconfigure(0, weight=1)
    ttk.Checkbutton(ai_output_frame, text="Automatically speak AI responses", variable=ai_speak_response_var).pack(anchor="w")

    output_hooks_frame = ttk.LabelFrame(tabs["🤖 AI"], text="Output Hooks (Webhook)", padding="10")
    output_hooks_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
    output_hooks_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(output_hooks_frame, text="Enable Webhook", variable=webhook_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Label(output_hooks_frame, text="Webhook URL:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(output_hooks_frame, textvariable=webhook_url_var).grid(row=1, column=1, sticky="ew", padx=5)
    ttk.Button(output_hooks_frame, text="Send Test Payload", command=lambda: send_webhook_test(webhook_url_var.get())).grid(row=2, column=0, columnspan=2, pady=5)

    # --- Security & Privacy Tab ---
    privacy_frame = ttk.LabelFrame(tabs["🔐 Security & Privacy"], text="Clipboard Settings", padding="10")
    privacy_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    privacy_frame.columnconfigure(0, weight=1)
    ttk.Checkbutton(privacy_frame, text="Disable all clipboard functionality (read/write)", variable=clipboard_privacy_var).pack(anchor="w")

    network_frame = ttk.LabelFrame(tabs["🔐 Security & Privacy"], text="Network Settings", padding="10")
    network_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    network_frame.columnconfigure(0, weight=1)
    ttk.Checkbutton(network_frame, text="Enable Local-Only Mode (disables all network requests)", variable=local_only_mode_var).pack(anchor="w")

    permissions_frame = ttk.LabelFrame(tabs["🔐 Security & Privacy"], text="Permission Controls", padding="10")
    permissions_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    permissions_frame.columnconfigure(0, weight=1)
    ttk.Checkbutton(permissions_frame, text="Enable Global Hotkeys", variable=enable_hotkeys_var).pack(anchor="w")
    ttk.Checkbutton(permissions_frame, text="Enable Microphone Access", variable=enable_microphone_var).pack(anchor="w")

    # --- Analytics Tab ---
    analytics_container = ttk.Frame(tabs["📊 Analytics"], padding="10")
    analytics_container.pack(fill="both", expand=True)

    stats_frame = ttk.LabelFrame(analytics_container, text="Usage Statistics", padding="10")
    stats_frame.pack(fill="x", expand=True, pady=5)

    analytics_tree = ttk.Treeview(stats_frame, columns=("Category", "Item", "Count"), show="headings")
    analytics_tree.heading("Category", text="Category")
    analytics_tree.heading("Item", text="Item")
    analytics_tree.heading("Count", text="Count")
    analytics_tree.pack(fill="both", expand=True, pady=5)

    def populate_analytics_tree():
        for i in analytics_tree.get_children():
            analytics_tree.delete(i)
        data = load_analytics_data()
        for category, items in data.items():
            for item, count in items.items():
                analytics_tree.insert("", "end", values=(category, item, count))

    def handle_reset_analytics():
        if messagebox.askyesno("Reset Analytics", "Are you sure you want to reset all usage statistics?"):
            reset_analytics_data()
            populate_analytics_tree()

    # Create a frame for the buttons
    analytics_buttons_frame = ttk.Frame(stats_frame)
    analytics_buttons_frame.pack(fill="x", pady=5)

    refresh_button = ttk.Button(analytics_buttons_frame, text="🔄 Refresh", command=populate_analytics_tree)
    refresh_button.pack(side="left", padx=5)

    reset_button = ttk.Button(analytics_buttons_frame, text="Reset Statistics", command=handle_reset_analytics)
    reset_button.pack(side="left", padx=5)

    populate_analytics_tree() # Initial population

    perf_frame = ttk.LabelFrame(analytics_container, text="Performance Dashboard", padding="10")
    perf_frame.pack(fill="x", expand=True, pady=5)

    cpu_label = ttk.Label(perf_frame, text="CPU Usage:")
    cpu_label.grid(row=0, column=0, sticky="w", padx=5, pady=2)
    cpu_value = ttk.Label(perf_frame, text="N/A")
    cpu_value.grid(row=0, column=1, sticky="w", padx=5)

    ram_label = ttk.Label(perf_frame, text="RAM Usage:")
    ram_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ram_value = ttk.Label(perf_frame, text="N/A")
    ram_value.grid(row=1, column=1, sticky="w", padx=5)

    gpu_label = ttk.Label(perf_frame, text="GPU Usage:")
    gpu_label.grid(row=2, column=0, sticky="w", padx=5, pady=2)
    gpu_value = ttk.Label(perf_frame, text="N/A")
    gpu_value.grid(row=2, column=1, sticky="w", padx=5)

    _update_perf_job = None
    def update_performance_labels():
        try:
            metrics = get_performance_metrics()
            cpu_value.config(text=metrics['cpu_usage'])
            ram_value.config(text=metrics['ram_usage'])
            gpu_value.config(text=metrics['gpu_usage'])
            global _update_perf_job
            _update_perf_job = window.after(2000, update_performance_labels) # Update every 2 seconds
        except tk.TclError: # Window was destroyed
            pass

    def on_destroy(event):
        if event.widget == window:
            if _update_perf_job:
                window.after_cancel(_update_perf_job)

    window.bind("<Destroy>", on_destroy)
    update_performance_labels()

    # --- SAPI Tab ---
    sapi_frame = ttk.LabelFrame(tabs["🔊 Windows SAPI"], text="Windows SAPI Settings", padding="10")
    sapi_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    sapi_frame.columnconfigure(1, weight=1)
    ttk.Label(sapi_frame, text="Voice:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(sapi_frame, sapi_voice_desc_var, initial_sapi_voice_desc or "Select a voice", *(sapi_voice_map.keys())).grid(row=0, column=1, sticky="ew", padx=5)
    
    ttk.Label(sapi_frame, text="Rate (-10 to 10):").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(sapi_frame, from_=-10, to=10, orient='horizontal', variable=sapi_rate_var).grid(row=1, column=1, sticky="ew", padx=5)

    ttk.Label(sapi_frame, text="Volume (0 to 100):").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(sapi_frame, from_=0, to=100, orient='horizontal', variable=sapi_volume_var).grid(row=2, column=1, sticky="ew", padx=5)

    sapi_test_frame = ttk.LabelFrame(tabs["🔊 Windows SAPI"], text="Test SAPI Voice", padding="10")
    sapi_test_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    sapi_test_frame.columnconfigure(0, weight=1)
    sapi_test_text_var = tk.StringVar(window, value="This is a test of the Windows SAPI voice.")
    ttk.Entry(sapi_test_frame, textvariable=sapi_test_text_var).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(sapi_test_frame, text="Test Voice", command=lambda: test_sapi_voice(sapi_test_text_var.get(), sapi_voice_map.get(sapi_voice_desc_var.get()), int(sapi_rate_var.get()), int(sapi_volume_var.get()))).grid(row=0, column=1, padx=5, pady=5)

    # --- OpenAI TTS Tab ---
    openai_main_frame = ttk.LabelFrame(tabs["🤖 OpenAI TTS"], text="OpenAI TTS Settings", padding="10")
    openai_main_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    openai_main_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(openai_main_frame, text="Enable OpenAI TTS", variable=openai_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Label(openai_main_frame, text="API Key:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(openai_main_frame, textvariable=openai_api_key_var, show="*").grid(row=1, column=1, sticky="ew", padx=5)
    ttk.Label(openai_main_frame, text="Voice:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(openai_main_frame, openai_voice_var, openai_voice_var.get(), "alloy", "echo", "fable", "onyx", "nova", "shimmer").grid(row=2, column=1, sticky="ew", padx=5)
    ttk.Label(openai_main_frame, text="Speed (0.25x - 4.0x):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(openai_main_frame, from_=0.25, to=4.0, orient='horizontal', variable=openai_speed_var).grid(row=3, column=1, sticky="ew", padx=5)

    openai_test_frame = ttk.LabelFrame(tabs["🤖 OpenAI TTS"], text="Test OpenAI Voice", padding="10")
    openai_test_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    openai_test_frame.columnconfigure(0, weight=1)
    openai_test_text_var = tk.StringVar(window, value="This is a test of the OpenAI text to speech system.")
    ttk.Entry(openai_test_frame, textvariable=openai_test_text_var).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(openai_test_frame, text="Test Voice", command=lambda: test_openai_voice(openai_test_text_var.get(), openai_voice_var.get(), openai_api_key_var.get(), openai_speed_var.get())).grid(row=0, column=1, padx=5, pady=5)

    # --- Kokoro TTS Tab ---
    kokoro_main_frame = ttk.LabelFrame(tabs["❤️ Kokoro TTS"], text="Kokoro TTS Settings", padding="10")
    kokoro_main_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    kokoro_main_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(kokoro_main_frame, text="Enable Kokoro TTS", variable=kokoro_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Label(kokoro_main_frame, text="Model File:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(kokoro_main_frame, kokoro_model_file_var, kokoro_model_file_var.get() or "Select a model", *get_kokoro_models()).grid(row=1, column=1, sticky="ew", padx=5)
    
    ttk.Label(kokoro_main_frame, text="Language:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    kokoro_lang_menu = ttk.OptionMenu(kokoro_main_frame, kokoro_language_var, kokoro_language_var.get() or "Select a language", *get_kokoro_languages())
    kokoro_lang_menu.grid(row=2, column=1, sticky="ew", padx=5)

    ttk.Label(kokoro_main_frame, text="Voice:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    kokoro_voice_menu = ttk.OptionMenu(kokoro_main_frame, kokoro_voice_var, kokoro_voice_var.get() or "Select a voice")
    kokoro_voice_menu.grid(row=3, column=1, sticky="ew", padx=5)

    def update_kokoro_voices_menu(*args):
        selected_language = kokoro_language_var.get()
        voices = get_kokoro_voices(selected_language)
        
        kokoro_voice_var.set("")
        menu = kokoro_voice_menu["menu"]
        menu.delete(0, "end")

        if voices:
            for voice in voices:
                menu.add_command(label=voice, command=lambda v=voice: kokoro_voice_var.set(v))
            kokoro_voice_var.set(voices[0])
            kokoro_voice_menu.configure(state="normal")
        else:
            kokoro_voice_var.set("No voices for this language")
            kokoro_voice_menu.configure(state="disabled")

    kokoro_language_var.trace_add("write", update_kokoro_voices_menu)
    update_kokoro_voices_menu() # Initial population

    # --- Voice Mixer ---
    mixer_frame = ttk.LabelFrame(tabs["❤️ Kokoro TTS"], text="Voice Mixer", padding="10")
    mixer_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
    mixer_frame.columnconfigure(1, weight=1)
    mixer_frame.columnconfigure(2, weight=1)
    mixer_frame.columnconfigure(3, weight=0)

    ttk.Checkbutton(mixer_frame, text="Enable Voice Blending", variable=kokoro_enable_blending_var).grid(row=0, column=0, columnspan=4, sticky="w", padx=5)

    def _add_linked_entry(parent, var, row, column):
        string_var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=string_var, width=5)
        entry.grid(row=row, column=column, sticky="w", padx=5)

        def _update_from_entry(event):
            try:
                val = float(string_var.get())
                val = max(0.0, min(1.0, val))
                var.set(round(val, 2))
            except (ValueError, tk.TclError):
                pass # Ignore invalid entries, will be reset by the trace
            finally:
                string_var.set(f"{var.get():.2f}")
        
        entry.bind("<Return>", _update_from_entry)
        entry.bind("<FocusOut>", _update_from_entry)

        def _update_entry_from_slider(*args):
            string_var.set(f"{var.get():.2f}")
        
        _update_entry_from_slider()
        var.trace_add("write", _update_entry_from_slider)

    # Voice 1 (Primary)
    ttk.Label(mixer_frame, text="Primary Voice:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_1_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
    _add_linked_entry(mixer_frame, kokoro_voice_weight_1_var, 1, 3)

    # Voice 2
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_2_var).grid(row=2, column=0, sticky="w", padx=5)
    kokoro_voice_2_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_2_var, kokoro_voice_2_var.get() or "Select a voice")
    kokoro_voice_2_menu.grid(row=2, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_2_var).grid(row=2, column=2, sticky="ew", padx=5)
    _add_linked_entry(mixer_frame, kokoro_voice_weight_2_var, 2, 3)

    # Voice 3
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_3_var).grid(row=3, column=0, sticky="w", padx=5)
    kokoro_voice_3_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_3_var, kokoro_voice_3_var.get() or "Select a voice")
    kokoro_voice_3_menu.grid(row=3, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_3_var).grid(row=3, column=2, sticky="ew", padx=5)
    _add_linked_entry(mixer_frame, kokoro_voice_weight_3_var, 3, 3)

    # Voice 4
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_4_var).grid(row=4, column=0, sticky="w", padx=5)
    kokoro_voice_4_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_4_var, kokoro_voice_4_var.get() or "Select a voice")
    kokoro_voice_4_menu.grid(row=4, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_4_var).grid(row=4, column=2, sticky="ew", padx=5)
    _add_linked_entry(mixer_frame, kokoro_voice_weight_4_var, 4, 3)

    # Voice 5
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_5_var).grid(row=5, column=0, sticky="w", padx=5)
    kokoro_voice_5_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_5_var, kokoro_voice_5_var.get() or "Select a voice")
    kokoro_voice_5_menu.grid(row=5, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_5_var).grid(row=5, column=2, sticky="ew", padx=5)
    _add_linked_entry(mixer_frame, kokoro_voice_weight_5_var, 5, 3)

    def update_mixer_voices_menu(*args):
        selected_language = kokoro_language_var.get()
        voices = get_kokoro_voices(selected_language)
        for menu_var, menu in [(kokoro_voice_2_var, kokoro_voice_2_menu), (kokoro_voice_3_var, kokoro_voice_3_menu), (kokoro_voice_4_var, kokoro_voice_4_menu), (kokoro_voice_5_var, kokoro_voice_5_menu)]:
            current_voice = menu_var.get()
            menu["menu"].delete(0, "end")
            if voices:
                for voice in voices:
                    menu["menu"].add_command(label=voice, command=lambda v=voice, m=menu_var: m.set(v))
                if current_voice in voices:
                    menu_var.set(current_voice)
                else:
                    menu_var.set(voices[0])
                menu.configure(state="normal")
            else:
                menu_var.set("No voices for this language")
                menu.configure(state="disabled")

    kokoro_language_var.trace_add("write", update_mixer_voices_menu)
    update_mixer_voices_menu()

    def run_kokoro_test():
        test_config = {
            'enable_voice_blending': kokoro_enable_blending_var.get(),
            'voice': kokoro_voice_var.get(),
            'voice_weight_1': kokoro_voice_weight_1_var.get(),
            'enable_voice_2': kokoro_enable_voice_2_var.get(),
            'voice_2': kokoro_voice_2_var.get(),
            'voice_weight_2': kokoro_voice_weight_2_var.get(),
            'enable_voice_3': kokoro_enable_voice_3_var.get(),
            'voice_3': kokoro_voice_3_var.get(),
            'voice_weight_3': kokoro_voice_weight_3_var.get(),
            'enable_voice_4': kokoro_enable_voice_4_var.get(),
            'voice_4': kokoro_voice_4_var.get(),
            'voice_weight_4': kokoro_voice_weight_4_var.get(),
            'enable_voice_5': kokoro_enable_voice_5_var.get(),
            'voice_5': kokoro_voice_5_var.get(),
            'voice_weight_5': kokoro_voice_weight_5_var.get(),
            'language': kokoro_language_var.get()
        }
        test_kokoro_voice(
            kokoro_test_text_var.get(),
            kokoro_config=test_config,
            device_index=get_selected_device_index()
        )

    kokoro_test_frame = ttk.LabelFrame(tabs["❤️ Kokoro TTS"], text="Test Kokoro Voice", padding="10")
    kokoro_test_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
    kokoro_test_frame.columnconfigure(0, weight=1)
    kokoro_test_text_var = tk.StringVar(window, value="中国人民不信邪也不怕邪")
    ttk.Entry(kokoro_test_frame, textvariable=kokoro_test_text_var).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(kokoro_test_frame, text="Test Voice", command=run_kokoro_test).grid(row=0, column=1, padx=5, pady=5)

    kokoro_actions_frame = ttk.LabelFrame(tabs["❤️ Kokoro TTS"], text="Actions", padding="10")
    kokoro_actions_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=5)
    kokoro_actions_frame.columnconfigure(0, weight=1)
    kokoro_actions_frame.columnconfigure(1, weight=1)
    kokoro_actions_frame.columnconfigure(2, weight=1)
    ttk.Button(kokoro_actions_frame, text="📥 Download Models", command=trigger_kokoro_model_download).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(kokoro_actions_frame, text="📊 View Benchmarks", command=open_benchmark_folder).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    ttk.Button(kokoro_actions_frame, text="▶️ Run Benchmark", command=trigger_kokoro_benchmark).grid(row=0, column=2, sticky="ew", padx=5, pady=5)

    # --- Piper TTS Tab ---
    piper_main_frame = ttk.LabelFrame(tabs["🐍 Piper TTS"], text="Piper TTS Settings", padding="10")
    piper_main_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    piper_main_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(piper_main_frame, text="Enable Piper TTS", variable=piper_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    
    # Create a frame for the model dropdown and its refresh button
    piper_model_frame = ttk.Frame(piper_main_frame)
    piper_model_frame.grid(row=1, column=1, sticky="ew", padx=5)
    piper_model_frame.columnconfigure(0, weight=1)

    piper_model_menu = ttk.OptionMenu(piper_model_frame, piper_model_file_var, piper_model_file_var.get() or "Select a model")
    piper_model_menu.grid(row=0, column=0, sticky="ew")

    def refresh_piper_model_dropdown():
        """Refreshes the Piper model dropdown menu."""
        models = get_piper_model_files()
        menu = piper_model_menu["menu"]
        menu.delete(0, "end")
        for model in models:
            menu.add_command(label=model, command=lambda value=model: piper_model_file_var.set(value))
        if not piper_model_file_var.get() in models:
            piper_model_file_var.set(models[0] if models else "")

    refresh_piper_model_dropdown() # Initial population

    piper_model_refresh_button = ttk.Button(piper_model_frame, text="🔄", command=refresh_piper_model_dropdown, width=3)
    piper_model_refresh_button.grid(row=0, column=1, padx=(5, 0))

    ttk.Label(piper_main_frame, text="Model File:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Label(piper_main_frame, text="Voice:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    piper_voice_menu = ttk.OptionMenu(piper_main_frame, piper_voice_var, "Select a voice")
    piper_voice_menu.grid(row=2, column=1, sticky="ew", padx=5)
    piper_voice_menu.configure(state="disabled")

    def update_piper_voices_menu(*args):
        selected_model = piper_model_file_var.get()
        voices = get_voices_for_piper_model(selected_model)
        
        piper_voice_var.set("")
        menu = piper_voice_menu["menu"]
        menu.delete(0, "end")

        if voices:
            for voice in voices:
                menu.add_command(label=voice, command=lambda v=voice: piper_voice_var.set(v))
            piper_voice_var.set(voices[0])
            piper_voice_menu.configure(state="normal")
        else:
            piper_voice_var.set("N/A (single voice model)")
            piper_voice_menu.configure(state="disabled")

    piper_model_file_var.trace_add("write", update_piper_voices_menu)
    if piper_model_file_var.get():
        update_piper_voices_menu()

    ttk.Label(piper_main_frame, text="Speed (slower to faster):").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(piper_main_frame, from_=2.0, to=0.5, orient='horizontal', variable=piper_length_scale_var).grid(row=3, column=1, sticky="ew", padx=5)

    piper_test_frame = ttk.LabelFrame(tabs["🐍 Piper TTS"], text="Test Piper Voice", padding="10")
    piper_test_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    piper_test_frame.columnconfigure(0, weight=1)
    piper_test_text_var = tk.StringVar(window, value="This is a test of the Piper text to speech system.")
    ttk.Entry(piper_test_frame, textvariable=piper_test_text_var).grid(row=0, column=0, sticky="ew", padx=5, pady=5)

    def run_piper_test():
        model = piper_model_file_var.get()
        voice = piper_voice_var.get()
        if voice == "N/A (single voice model)":
            voice = None
        test_piper_voice(
            piper_test_text_var.get(),
            model_file=model,
            voice_name=voice,
            length_scale=piper_length_scale_var.get(),
            device_index=get_selected_device_index()
        )
    ttk.Button(piper_test_frame, text="Test Voice", command=run_piper_test).grid(row=0, column=1, padx=5, pady=5)

    # --- ZipVoice TTS Tab ---
    zipvoice_main_frame = ttk.LabelFrame(tabs["🧬 ZipVoice TTS"], text="ZipVoice Voice Cloning", padding="10")
    zipvoice_main_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    zipvoice_main_frame.columnconfigure(1, weight=1)
    ttk.Checkbutton(zipvoice_main_frame, text="Enable ZipVoice TTS", variable=zipvoice_enabled_var).grid(row=0, column=0, columnspan=3, sticky="w", padx=5)

    ttk.Label(zipvoice_main_frame, text="Model Variant:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(zipvoice_main_frame, zipvoice_model_var, zipvoice_model_var.get() or "zipvoice", "zipvoice", "zipvoice_distill").grid(row=1, column=1, sticky="ew", padx=5)

    ttk.Label(zipvoice_main_frame, text="Backend:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(
        zipvoice_main_frame,
        zipvoice_backend_var,
        zipvoice_backend_var.get() or "torch",
        "torch",
        "onnx",
    ).grid(row=2, column=1, sticky="ew", padx=5)

    ttk.Label(zipvoice_main_frame, text="Prompt Source:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    zipvoice_mode_frame = ttk.Frame(zipvoice_main_frame)
    zipvoice_mode_frame.grid(row=3, column=1, columnspan=2, sticky="w", padx=5, pady=2)
    zipvoice_sample_radio = ttk.Radiobutton(
        zipvoice_mode_frame,
        text="WAV / Sample",
        variable=zipvoice_prompt_mode_var,
        value="sample",
    )
    zipvoice_sample_radio.pack(side="left", padx=(0, 8))
    zipvoice_profile_radio = ttk.Radiobutton(
        zipvoice_mode_frame,
        text="Saved Embedding",
        variable=zipvoice_prompt_mode_var,
        value="profile",
    )
    zipvoice_profile_radio.pack(side="left")

    zipvoice_sample_source_frame = ttk.Frame(zipvoice_main_frame)
    zipvoice_sample_source_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=0, pady=2)
    zipvoice_sample_source_frame.columnconfigure(1, weight=1)
    sample_display_values = [sample.display_name for sample in zipvoice_samples] if zipvoice_samples else ["No samples available"]
    ttk.Label(zipvoice_sample_source_frame, text="Sample Voice Prompt:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    zipvoice_sample_combo = ttk.Combobox(
        zipvoice_sample_source_frame,
        textvariable=zipvoice_sample_display_var,
        values=sample_display_values,
        state="readonly" if zipvoice_samples else "disabled"
    )
    zipvoice_sample_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
    ttk.Button(zipvoice_sample_source_frame, text="📁", width=4, command=open_zipvoice_samples_folder).grid(row=0, column=2, padx=5, pady=2)

    ttk.Label(zipvoice_sample_source_frame, text="Save as Embedding:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    zipvoice_profile_name_entry = ttk.Entry(zipvoice_sample_source_frame, textvariable=zipvoice_profile_name_var)
    zipvoice_profile_name_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
    zipvoice_convert_button = ttk.Button(zipvoice_sample_source_frame, text="Convert & Save")
    zipvoice_convert_button.grid(row=1, column=2, padx=5, pady=2)
    ttk.Label(zipvoice_sample_source_frame, textvariable=zipvoice_profile_status_var, foreground="green").grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=2)

    zipvoice_profile_source_frame = ttk.Frame(zipvoice_main_frame)
    zipvoice_profile_source_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=0, pady=2)
    zipvoice_profile_source_frame.columnconfigure(1, weight=1)
    ttk.Label(zipvoice_profile_source_frame, text="Saved Embedding:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    zipvoice_profile_combo = ttk.Combobox(
        zipvoice_profile_source_frame,
        textvariable=zipvoice_profile_selection_var,
        values=[],
        state="disabled"
    )
    zipvoice_profile_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
    profile_button_group = ttk.Frame(zipvoice_profile_source_frame)
    profile_button_group.grid(row=0, column=2, sticky="e", padx=5, pady=2)
    zipvoice_profile_refresh_button = ttk.Button(profile_button_group, text="🔄", width=3)
    zipvoice_profile_refresh_button.pack(side="left", padx=(0, 4))
    ttk.Button(profile_button_group, text="📁", width=3, command=open_zipvoice_profiles_folder).pack(side="left", padx=(0, 4))
    zipvoice_profile_delete_button = ttk.Button(profile_button_group, text="🗑", width=3)
    zipvoice_profile_delete_button.pack(side="left")

    ttk.Label(zipvoice_main_frame, text="Speed Multiplier:").grid(row=5, column=0, sticky="w", padx=5, pady=2)
    zipvoice_speed_scale = ttk.Scale(zipvoice_main_frame, from_=0.6, to=1.4, orient='horizontal', variable=zipvoice_speed_var)
    zipvoice_speed_scale.grid(row=5, column=1, sticky="ew", padx=5)
    zipvoice_speed_value_label = ttk.Label(zipvoice_main_frame, text=f"{zipvoice_speed_var.get():.2f}")
    zipvoice_speed_value_label.grid(row=5, column=2, padx=5)

    ttk.Label(zipvoice_main_frame, text="Deterministic Seed (optional):").grid(row=6, column=0, sticky="w", padx=5, pady=2)
    zipvoice_seed_entry = ttk.Entry(zipvoice_main_frame, textvariable=zipvoice_seed_var)
    zipvoice_seed_entry.grid(row=6, column=1, sticky="ew", padx=5, pady=2)
    ttk.Label(zipvoice_main_frame, text="Use blank for random each run").grid(row=6, column=2, sticky="w", padx=5, pady=2)

    zipvoice_blend_frame = ttk.LabelFrame(zipvoice_main_frame, text="Blend Saved Embeddings", padding="10")
    zipvoice_blend_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=5)
    zipvoice_blend_frame.columnconfigure(1, weight=1)

    ttk.Label(zipvoice_blend_frame, text="Primary Profile:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    zipvoice_blend_primary_combo = ttk.Combobox(
        zipvoice_blend_frame,
        textvariable=zipvoice_blend_primary_var,
        values=[],
        state="disabled",
    )
    zipvoice_blend_primary_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

    ttk.Label(zipvoice_blend_frame, text="Secondary Profile:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    zipvoice_blend_secondary_combo = ttk.Combobox(
        zipvoice_blend_frame,
        textvariable=zipvoice_blend_secondary_var,
        values=[],
        state="disabled",
    )
    zipvoice_blend_secondary_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

    ttk.Label(zipvoice_blend_frame, text="Primary Weight:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    zipvoice_blend_weight_scale = ttk.Scale(
        zipvoice_blend_frame,
        from_=0.0,
        to=1.0,
        orient="horizontal",
        variable=zipvoice_blend_weight_var,
    )
    zipvoice_blend_weight_scale.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
    zipvoice_blend_weight_label = ttk.Label(zipvoice_blend_frame, text="")
    zipvoice_blend_weight_label.grid(row=2, column=2, sticky="w", padx=5)

    ttk.Label(zipvoice_blend_frame, text="Blended Name:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
    zipvoice_blend_name_entry = ttk.Entry(zipvoice_blend_frame, textvariable=zipvoice_blend_name_var)
    zipvoice_blend_name_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
    zipvoice_blend_button = ttk.Button(
        zipvoice_blend_frame,
        text="Blend & Save",
        state="disabled",
    )
    zipvoice_blend_button.grid(row=3, column=2, sticky="ew", padx=5, pady=2)

    ttk.Label(
        zipvoice_blend_frame,
        textvariable=zipvoice_blend_status_var,
        wraplength=420,
        justify="left",
    ).grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=(4, 0))

    def _update_blend_weight_display(*_args):
        primary_weight = max(0.0, min(1.0, float(zipvoice_blend_weight_var.get() or 0.0)))
        secondary_weight = 1.0 - primary_weight
        zipvoice_blend_weight_label.config(text=f"{primary_weight:.2f} / {secondary_weight:.2f}")

    def _update_blend_button_state(*_args):
        primary = zipvoice_blend_primary_var.get().strip()
        secondary = zipvoice_blend_secondary_var.get().strip()
        name = zipvoice_blend_name_var.get().strip()
        ready = bool(primary and secondary and primary != secondary and name)
        zipvoice_blend_button.configure(state="normal" if ready else "disabled")

    def _handle_blend_selection_change(_event=None):
        zipvoice_blend_status_var.set("")
        _update_blend_button_state()

    def run_zipvoice_blend():
        primary_name = zipvoice_blend_primary_var.get().strip()
        secondary_name = zipvoice_blend_secondary_var.get().strip()
        blend_name = zipvoice_blend_name_var.get().strip()

        if not primary_name or not secondary_name:
            messagebox.showwarning("ZipVoice Blend", "Select two saved embeddings to blend.")
            return
        if primary_name == secondary_name:
            messagebox.showwarning("ZipVoice Blend", "Choose two different embeddings to blend.")
            return
        if not blend_name:
            messagebox.showwarning("ZipVoice Blend", "Enter a name for the blended embedding.")
            return

        primary_meta = zipvoice_profiles_map.get(primary_name)
        secondary_meta = zipvoice_profiles_map.get(secondary_name)
        if not primary_meta or not secondary_meta:
            messagebox.showerror("ZipVoice Blend", "Unable to resolve the selected embeddings. Refresh the list and try again.")
            return

        primary_path = primary_meta.get("path")
        secondary_path = secondary_meta.get("path")
        if not primary_path or not secondary_path:
            messagebox.showerror("ZipVoice Blend", "Selected embeddings are missing file paths.")
            return

        weight_primary = max(0.0, min(1.0, float(zipvoice_blend_weight_var.get() or 0.0)))
        weight_secondary = 1.0 - weight_primary

        destination = profile_path_for_name(blend_name, zipvoice_model_var.get())
        overwrite = False
        if destination.exists():
            if not messagebox.askyesno(
                "Overwrite Blended Embedding?",
                f"An embedding named '{destination.stem}' already exists. Do you want to replace it?",
                parent=window,
            ):
                return
            overwrite = True

        zipvoice_blend_status_var.set("Blending embeddings...")
        zipvoice_blend_button.configure(state="disabled")

        blend_metadata = {
            "created_at": dt.datetime.utcnow().isoformat() + "Z",
            "saved_from": "settings_window_blend",
        }

        def worker() -> None:
            try:
                saved_path = blend_voice_profiles(
                    [primary_path, secondary_path],
                    [weight_primary, weight_secondary],
                    blend_name,
                    metadata={
                        **blend_metadata,
                        "blend_pairs": [
                            {"name": primary_name, "weight": round(weight_primary, 4)},
                            {"name": secondary_name, "weight": round(weight_secondary, 4)},
                        ],
                    },
                    overwrite=overwrite,
                )
            except Exception as exc:  # pylint: disable=broad-except
                error_text = f"{exc}"

                def on_error() -> None:
                    messagebox.showerror("ZipVoice Blend", f"Failed to blend embeddings: {error_text}")
                    zipvoice_blend_status_var.set("")
                    _update_blend_button_state()

                window.after(0, on_error)
                return

            def on_success() -> None:
                zipvoice_blend_status_var.set(f"Saved blended embedding as {saved_path.name}")
                refresh_zipvoice_profiles(selected_name=saved_path.stem, selected_path=str(saved_path))
                zipvoice_prompt_mode_var.set("profile")
                _update_blend_button_state()

            window.after(0, on_success)

        threading.Thread(target=worker, daemon=True).start()

    zipvoice_blend_primary_combo.bind("<<ComboboxSelected>>", _handle_blend_selection_change)
    zipvoice_blend_secondary_combo.bind("<<ComboboxSelected>>", _handle_blend_selection_change)
    zipvoice_blend_weight_var.trace_add("write", lambda *_args: _update_blend_weight_display())
    zipvoice_blend_primary_var.trace_add("write", lambda *_args: _handle_blend_selection_change())
    zipvoice_blend_secondary_var.trace_add("write", lambda *_args: _handle_blend_selection_change())
    zipvoice_blend_name_var.trace_add("write", lambda *_args: _handle_blend_selection_change())
    zipvoice_blend_button.configure(command=run_zipvoice_blend)
    _update_blend_weight_display()
    _update_blend_button_state()

    def update_zipvoice_speed_display(*args):
        zipvoice_speed_value_label.config(text=f"{zipvoice_speed_var.get():.2f}")

    zipvoice_speed_var.trace_add("write", lambda *args: update_zipvoice_speed_display())
    update_zipvoice_speed_display()

    def update_zipvoice_preview():
        mode = zipvoice_prompt_mode_var.get()
        preview_text = "Select a sample to view its reference transcript."

        if mode == "profile":
            selected_profile = zipvoice_profile_selection_var.get()
            profile_meta = zipvoice_profiles_map.get(selected_profile)
            if profile_meta:
                prompt_text = (profile_meta.get("prompt_text") or "").strip()
                metadata = profile_meta.get("metadata") or {}
                source_label = metadata.get("source_sample") or metadata.get("source_wav_path") or ""
                if prompt_text:
                    preview_text = prompt_text
                else:
                    preview_text = "This embedding does not contain stored prompt transcript text."
                header = f"Saved profile '{selected_profile}'"
                if source_label:
                    header += f" (source: {source_label})"
                preview_text = f"{header}\n\n{preview_text}".strip()
            else:
                preview_text = "Select a saved embedding to view its stored prompt."
        else:
            selected_name = zipvoice_sample_var.get()
            sample_meta = zipvoice_samples_map.get(selected_name)
            if sample_meta and sample_meta.text_path:
                try:
                    preview_text = Path(sample_meta.text_path).read_text(encoding='utf-8').strip()
                except Exception:
                    preview_text = "Unable to load transcript for this sample."

        preview_text = (preview_text or "").strip()
        if len(preview_text) > 320:
            preview_text = preview_text[:317] + "..."
        zipvoice_prompt_preview_var.set(preview_text or "Select a sample to view its reference transcript.")

    def handle_zipvoice_sample_change(event=None):
        previous_entry_value = zipvoice_profile_name_var.get()
        selected_display = zipvoice_sample_display_var.get()
        selected_name = zipvoice_display_to_name.get(selected_display)
        if selected_name:
            zipvoice_sample_var.set(selected_name)
            if not previous_entry_value or previous_entry_value == selected_display or previous_entry_value == zipvoice_sample_var.get():
                zipvoice_profile_name_var.set(selected_name)
        zipvoice_profile_status_var.set("")
        update_zipvoice_preview()

    zipvoice_sample_combo.bind("<<ComboboxSelected>>", handle_zipvoice_sample_change)

    def handle_zipvoice_profile_change(event=None):
        selected_name = zipvoice_profile_selection_var.get()
        profile_meta = zipvoice_profiles_map.get(selected_name)
        zipvoice_selected_profile_path_var.set(profile_meta.get("path", "") if profile_meta else "")
        zipvoice_profile_status_var.set("")
        update_zipvoice_preview()

    def refresh_zipvoice_profiles(selected_name: str | None = None, selected_path: str | None = None):
        ensure_profiles_directory()
        try:
            profiles = list_saved_profiles(zipvoice_model_var.get())
        except Exception as exc:
            messagebox.showerror("ZipVoice Embeddings", f"Could not read saved embeddings: {exc}")
            profiles = []

        zipvoice_profiles_map.clear()
        for profile in profiles:
            zipvoice_profiles_map[profile["name"]] = profile

        profile_names = sorted(zipvoice_profiles_map.keys())
        if profile_names:
            zipvoice_profile_combo.configure(values=profile_names, state="readonly")
            chosen_name = selected_name or zipvoice_profile_selection_var.get()
            if selected_path:
                for name, meta in zipvoice_profiles_map.items():
                    if Path(meta["path"]).resolve() == Path(selected_path).resolve():
                        chosen_name = name
                        break
            if not chosen_name or chosen_name not in zipvoice_profiles_map:
                chosen_name = profile_names[0]
            zipvoice_profile_selection_var.set(chosen_name)
            zipvoice_selected_profile_path_var.set(zipvoice_profiles_map[chosen_name]["path"])
            zipvoice_profile_status_var.set("")
        else:
            zipvoice_profile_combo.configure(values=["No embeddings saved"], state="disabled")
            zipvoice_profile_selection_var.set("")
            zipvoice_selected_profile_path_var.set("")
            zipvoice_profile_status_var.set("No embeddings saved for this model yet.")

        if len(profile_names) >= 2:
            zipvoice_blend_primary_combo.configure(values=profile_names, state="readonly")
            zipvoice_blend_secondary_combo.configure(values=profile_names, state="readonly")
            primary_choice = zipvoice_blend_primary_var.get()
            if primary_choice not in profile_names:
                primary_choice = profile_names[0]
                zipvoice_blend_primary_var.set(primary_choice)
            secondary_choice = zipvoice_blend_secondary_var.get()
            if secondary_choice not in profile_names or secondary_choice == primary_choice:
                secondary_choice = next((name for name in profile_names if name != primary_choice), "")
                zipvoice_blend_secondary_var.set(secondary_choice)
        elif profile_names:
            zipvoice_blend_primary_combo.configure(values=profile_names, state="readonly")
            if zipvoice_blend_primary_var.get() not in profile_names:
                zipvoice_blend_primary_var.set(profile_names[0])
            zipvoice_blend_secondary_combo.configure(values=profile_names, state="disabled")
            zipvoice_blend_secondary_var.set("")
        else:
            zipvoice_blend_primary_combo.configure(values=["No embeddings saved"], state="disabled")
            zipvoice_blend_secondary_combo.configure(values=["No embeddings saved"], state="disabled")
            zipvoice_blend_primary_var.set("")
            zipvoice_blend_secondary_var.set("")

        zipvoice_profile_radio.configure(state="normal" if profile_names else "disabled")
        update_zipvoice_preview()
        _update_blend_button_state()

    def handle_zipvoice_model_change(*_):
        refresh_zipvoice_profiles(selected_path=zipvoice_selected_profile_path_var.get() or None)

    zipvoice_model_var.trace_add("write", lambda *_: handle_zipvoice_model_change())

    def update_prompt_mode_controls(*_):
        mode = zipvoice_prompt_mode_var.get()
        if mode == "profile" and not zipvoice_profiles_map:
            zipvoice_prompt_mode_var.set("sample")
            mode = "sample"

        if mode == "profile":
            zipvoice_sample_source_frame.grid_remove()
            zipvoice_profile_source_frame.grid()
            if zipvoice_profiles_map:
                zipvoice_profile_combo.configure(state="readonly")
            else:
                zipvoice_profile_combo.configure(state="disabled")
        else:
            zipvoice_profile_source_frame.grid_remove()
            zipvoice_sample_source_frame.grid()
            zipvoice_convert_button.configure(state="normal" if zipvoice_samples else "disabled")

        update_zipvoice_preview()

    def convert_sample_to_profile():
        sample_name = zipvoice_sample_var.get()
        if not sample_name:
            messagebox.showwarning("ZipVoice", "Select or record a voice sample before converting.")
            return

        profile_name = zipvoice_profile_name_var.get().strip()
        if not profile_name:
            messagebox.showwarning("ZipVoice", "Enter a name for the saved embedding.")
            zipvoice_profile_name_entry.focus_set()
            return

        destination = profile_path_for_name(profile_name, zipvoice_model_var.get())
        if destination.exists():
            overwrite = messagebox.askyesno(
                "Overwrite embedding?",
                f"An embedding named '{destination.stem}' already exists. Do you want to replace it?",
                parent=window,
            )
            if not overwrite:
                return

        zipvoice_profile_status_var.set("Converting sample to embedding...")
        zipvoice_convert_button.configure(state="disabled")

        ensure_profiles_directory()
        snapshot = copy.deepcopy(zipvoice_config)
        snapshot.update({
            'enabled': True,
            'sample_name': sample_name,
            'model_name': zipvoice_model_var.get(),
            'backend': zipvoice_backend_var.get(),
            'speed': float(zipvoice_speed_var.get()),
            'prompt_mode': 'sample',
        })
        snapshot.pop('custom_prompt_profile', None)
        snapshot.pop('profile_name', None)

        metadata: Dict[str, Any] = {
            'source_sample': sample_name,
            'created_at': dt.datetime.utcnow().isoformat() + 'Z',
            'saved_from': 'settings_window',
        }

        def worker():
            try:
                saved_path = export_zipvoice_profile(profile_name, snapshot, metadata=metadata, overwrite=True)
            except Exception as exc:
                def on_error() -> None:
                    zipvoice_profile_status_var.set("")
                    zipvoice_convert_button.configure(state="normal")
                    messagebox.showerror("ZipVoice", f"Failed to save embedding: {exc}")

                window.after(0, on_error)
                return

            def on_success() -> None:
                zipvoice_convert_button.configure(state="normal")
                refresh_zipvoice_profiles(selected_name=saved_path.stem, selected_path=str(saved_path))
                zipvoice_profile_status_var.set(f"Saved embedding to {saved_path.name}")
                zipvoice_prompt_mode_var.set("profile")

            window.after(0, on_success)

        threading.Thread(target=worker, daemon=True).start()

    def delete_selected_profile():
        selected_name = zipvoice_profile_selection_var.get()
        profile_meta = zipvoice_profiles_map.get(selected_name)
        if not profile_meta:
            messagebox.showinfo("ZipVoice", "Select a saved embedding to delete.")
            return

        if not messagebox.askyesno("Delete embedding?", f"Remove '{selected_name}' permanently?", parent=window):
            return

        if not delete_voice_profile(profile_meta["path"]):
            messagebox.showerror("ZipVoice", f"Could not delete '{selected_name}'.")
            return

        zipvoice_profile_status_var.set(f"Deleted embedding '{selected_name}'.")
        refresh_zipvoice_profiles()

    zipvoice_profile_combo.bind("<<ComboboxSelected>>", handle_zipvoice_profile_change)
    zipvoice_convert_button.configure(command=convert_sample_to_profile)
    zipvoice_profile_refresh_button.configure(command=lambda: refresh_zipvoice_profiles(selected_path=zipvoice_selected_profile_path_var.get() or None))
    zipvoice_profile_delete_button.configure(command=delete_selected_profile)
    zipvoice_sample_radio.configure(command=update_prompt_mode_controls)
    zipvoice_profile_radio.configure(command=update_prompt_mode_controls)
    zipvoice_prompt_mode_var.trace_add("write", lambda *_: update_prompt_mode_controls())

    refresh_zipvoice_profiles(selected_name=inferred_profile_name or None, selected_path=selected_profile_path or None)
    update_prompt_mode_controls()

    zipvoice_preview_frame = ttk.LabelFrame(tabs["🧬 ZipVoice TTS"], text="Prompt Transcript Preview", padding="10")
    zipvoice_preview_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    zipvoice_preview_frame.columnconfigure(0, weight=1)
    ttk.Label(zipvoice_preview_frame, textvariable=zipvoice_prompt_preview_var, wraplength=460, justify="left").grid(row=0, column=0, sticky="w", padx=5)

    zipvoice_test_frame = ttk.LabelFrame(tabs["🧬 ZipVoice TTS"], text="Test ZipVoice Voice", padding="10")
    zipvoice_test_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    zipvoice_test_frame.columnconfigure(0, weight=1)
    zipvoice_test_text_var = tk.StringVar(window, value="This is a ZipVoice cloning test.")
    ttk.Entry(zipvoice_test_frame, textvariable=zipvoice_test_text_var).grid(row=0, column=0, sticky="ew", padx=5, pady=5)

    def run_zipvoice_test():
        mode = zipvoice_prompt_mode_var.get()
        selected_profile_path = (zipvoice_selected_profile_path_var.get() or "").strip()

        if mode == "profile":
            if not selected_profile_path:
                messagebox.showwarning("ZipVoice Embeddings", "Select a saved embedding before testing.")
                return
        elif not zipvoice_sample_var.get():
            messagebox.showwarning("ZipVoice Samples", "No ZipVoice sample is selected. Add samples to test voice cloning.")
            return

        test_settings = dict(zipvoice_config)
        test_settings.update({
            'enabled': True,
            'model_name': zipvoice_model_var.get(),
            'backend': zipvoice_backend_var.get(),
            'speed': float(zipvoice_speed_var.get()),
            'prompt_mode': mode,
        })

        if mode == "profile":
            test_settings['custom_prompt_profile'] = selected_profile_path
            test_settings['profile_name'] = zipvoice_profile_selection_var.get()
            test_settings.pop('sample_name', None)
            test_settings.pop('custom_prompt_wav', None)
            test_settings.pop('custom_prompt_text_path', None)
            test_settings.pop('custom_prompt_text', None)
        else:
            test_settings['sample_name'] = zipvoice_sample_var.get()
            test_settings.pop('custom_prompt_profile', None)
            test_settings.pop('profile_name', None)

        test_zipvoice_voice(zipvoice_test_text_var.get(), test_settings, device_index=get_selected_device_index())

    zipvoice_test_button = ttk.Button(
        zipvoice_test_frame,
        text="Test Voice",
        command=run_zipvoice_test,
        state="normal" if zipvoice_samples else "disabled"
    )
    zipvoice_test_button.grid(row=0, column=1, padx=5, pady=5)

    def refresh_zipvoice_sample_sources(selected_sample: str | None = None):
        nonlocal zipvoice_samples, zipvoice_samples_map, zipvoice_display_to_name, zipvoice_name_to_display

        new_samples = get_zipvoice_samples()
        zipvoice_samples = new_samples
        zipvoice_samples_map = {sample.name: sample for sample in new_samples}
        zipvoice_display_to_name = {sample.display_name: sample.name for sample in new_samples}
        zipvoice_name_to_display = {sample.name: sample.display_name for sample in new_samples}

        display_values = [sample.display_name for sample in new_samples] if new_samples else ["No samples available"]
        zipvoice_sample_combo.configure(values=display_values)

        if new_samples:
            chosen = selected_sample if selected_sample in zipvoice_name_to_display else new_samples[0].name
            zipvoice_sample_var.set(chosen)
            zipvoice_sample_display_var.set(zipvoice_name_to_display[chosen])
            zipvoice_sample_combo.configure(state="readonly")
            zipvoice_test_button.configure(state="normal")
            zipvoice_convert_button.configure(state="normal")
            update_zipvoice_preview()
        else:
            zipvoice_sample_var.set("")
            zipvoice_sample_display_var.set("No samples available")
            zipvoice_sample_combo.configure(state="disabled")
            zipvoice_test_button.configure(state="disabled")
            zipvoice_convert_button.configure(state="disabled")
            zipvoice_prompt_preview_var.set("Add a sample to view its transcript.")

    refresh_zipvoice_sample_sources(zipvoice_sample_var.get() or None)

    update_prompt_mode_controls()
    update_zipvoice_preview()

    # --- ZipVoice Samples Tab ---
    zipvoice_samples_tab = tabs["🎙️ ZipVoice Samples"]
    zipvoice_samples_tab.columnconfigure(0, weight=1)
    zipvoice_samples_tab.rowconfigure(1, weight=1)

    zipvoice_sample_name_var = tk.StringVar(window, value="")
    initial_status = "Ready to record a new sample." if input_device_map else "No recording devices detected."
    zipvoice_samples_status_var = tk.StringVar(window, value=initial_status)

    current_sample_safe_name: str | None = None
    current_temp_recording_path: Path | None = None
    current_final_wav_path: Path | None = None
    current_transcript_path: Path | None = None
    recording_in_progress = False

    def _has_valid_input_devices() -> bool:
        return any(info.get('index', -1) >= 0 for info in input_device_map.values())

    sample_form_frame = ttk.LabelFrame(zipvoice_samples_tab, text="Create ZipVoice Sample", padding="10")
    sample_form_frame.grid(row=0, column=0, sticky="ew", pady=5)
    sample_form_frame.columnconfigure(1, weight=1)

    ttk.Label(sample_form_frame, text="Sample Name:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    zipvoice_sample_name_entry = ttk.Entry(sample_form_frame, textvariable=zipvoice_sample_name_var)
    zipvoice_sample_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

    ttk.Label(sample_form_frame, text="Input Source:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    input_device_container = ttk.Frame(sample_form_frame)
    input_device_container.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
    input_device_container.columnconfigure(0, weight=1)

    input_device_values = list(input_device_map.keys()) or ["No input devices found"]
    zipvoice_input_device_combo = ttk.Combobox(
        input_device_container,
        textvariable=zipvoice_input_device_var,
        values=input_device_values,
        state="readonly" if _has_valid_input_devices() else "disabled"
    )
    if not zipvoice_input_device_var.get() and input_device_values:
        zipvoice_input_device_var.set(input_device_values[0])
    zipvoice_input_device_combo.grid(row=0, column=0, sticky="ew")

    def refresh_input_device_options():
        nonlocal input_device_map
        latest_devices = get_input_devices()
        input_device_map = {name: info for name, info in latest_devices.items()}
        values = list(input_device_map.keys()) or ["No input devices found"]
        zipvoice_input_device_combo.configure(values=values)
        valid_choice = zipvoice_input_device_var.get() in input_device_map
        if not valid_choice and values:
            zipvoice_input_device_var.set(values[0])
        has_valid = _has_valid_input_devices()
        new_state = "readonly" if has_valid else "disabled"
        zipvoice_input_device_combo.configure(state=new_state)
        zipvoice_sample_record_button.configure(state="normal" if has_valid else "disabled")

    ttk.Button(input_device_container, text="🔄", width=3, command=refresh_input_device_options).grid(row=0, column=1, padx=(5, 0))

    button_row = ttk.Frame(sample_form_frame)
    button_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
    button_row.columnconfigure(0, weight=1)
    button_row.columnconfigure(1, weight=1)
    button_row.columnconfigure(2, weight=1)

    zipvoice_sample_record_button = ttk.Button(
        button_row,
        text="⏺️ Record",
        state="normal" if _has_valid_input_devices() else "disabled"
    )
    zipvoice_sample_record_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

    zipvoice_sample_stop_button = ttk.Button(button_row, text="⏹️ Stop", state="disabled")
    zipvoice_sample_stop_button.grid(row=0, column=1, sticky="ew", padx=(0, 5))

    ttk.Button(button_row, text="📁 Open Folder", command=open_zipvoice_samples_folder).grid(row=0, column=2, sticky="ew")

    if not _has_valid_input_devices():
        zipvoice_samples_status_var.set("No recording or loopback devices detected. Use 🔄 after enabling one.")

    ttk.Label(sample_form_frame, textvariable=zipvoice_samples_status_var, wraplength=440, justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))

    transcript_frame = ttk.LabelFrame(zipvoice_samples_tab, text="Transcript", padding="10")
    transcript_frame.grid(row=1, column=0, sticky="nsew", pady=5)
    transcript_frame.columnconfigure(0, weight=1)
    transcript_frame.rowconfigure(0, weight=1)

    zipvoice_transcript_text = tk.Text(transcript_frame, height=8, wrap="word")
    zipvoice_transcript_text.grid(row=0, column=0, sticky="nsew")
    transcript_scrollbar = ttk.Scrollbar(transcript_frame, orient="vertical", command=zipvoice_transcript_text.yview)
    transcript_scrollbar.grid(row=0, column=1, sticky="ns")
    zipvoice_transcript_text.configure(yscrollcommand=transcript_scrollbar.set)

    transcript_button_row = ttk.Frame(transcript_frame)
    transcript_button_row.grid(row=1, column=0, columnspan=2, sticky="e", pady=(5, 0))
    zipvoice_save_transcript_button = ttk.Button(transcript_button_row, text="💾 Save Transcript", state="disabled")
    zipvoice_save_transcript_button.grid(row=0, column=0, padx=5)

    def sanitize_sample_name(raw_name: str) -> str:
        name = raw_name.strip().lower().replace(" ", "_")
        name = re.sub(r"[^a-z0-9_-]", "", name)
        name = re.sub(r"_+", "_", name).strip("_")
        return name

    def enable_transcript_controls(enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        zipvoice_save_transcript_button.configure(state=state)
        zipvoice_transcript_text.configure(state=state)

    enable_transcript_controls(False)

    def start_zipvoice_recording():
        nonlocal recording_in_progress, current_sample_safe_name, current_temp_recording_path, current_final_wav_path, current_transcript_path
        if recording_in_progress:
            messagebox.showinfo("Recording", "A recording is already in progress.")
            return

        safe_name = sanitize_sample_name(zipvoice_sample_name_var.get())
        if not safe_name:
            messagebox.showerror("Sample Name", "Please enter a valid sample name (letters, numbers, dashes, underscores).")
            zipvoice_sample_name_entry.focus_set()
            return
        zipvoice_sample_name_var.set(safe_name)

        device_label = zipvoice_input_device_var.get()
        device_info = input_device_map.get(device_label)
        if not device_info or int(device_info.get('index', -1)) < 0:
            messagebox.showerror("Input Source", "Select a valid input device before recording.")
            return

        samples_dir = ensure_samples_directory()
        temp_wav_path = samples_dir / f"{safe_name}__recording.wav"
        final_wav_path = samples_dir / f"{safe_name}.wav"
        final_txt_path = samples_dir / f"{safe_name}.txt"

        if final_wav_path.exists() or final_txt_path.exists():
            overwrite = messagebox.askyesno(
                "Overwrite Sample?",
                f"A sample named '{safe_name}' already exists. Do you want to overwrite it?",
                parent=window,
            )
            if not overwrite:
                return
            for path in (final_wav_path, final_txt_path):
                try:
                    if path.exists():
                        path.unlink()
                except Exception as exc:
                    messagebox.showerror("File Error", f"Could not remove existing file {path.name}: {exc}")
                    return

        if temp_wav_path.exists():
            try:
                temp_wav_path.unlink()
            except Exception:
                pass

        try:
            start_audio_capture(str(temp_wav_path), device_info=device_info)
        except Exception as exc:
            messagebox.showerror("Recording Failed", f"Could not start recording: {exc}")
            return

        recording_in_progress = True
        current_sample_safe_name = safe_name
        current_temp_recording_path = temp_wav_path
        current_final_wav_path = final_wav_path
        current_transcript_path = final_txt_path

        zipvoice_samples_status_var.set("Recording... Press Stop when you are finished speaking.")
        zipvoice_sample_record_button.configure(state="disabled")
        zipvoice_sample_stop_button.configure(state="normal")
        zipvoice_transcript_text.configure(state="normal")
        zipvoice_transcript_text.delete("1.0", tk.END)
        enable_transcript_controls(False)

    def finalize_zipvoice_recording():
        nonlocal current_temp_recording_path, current_final_wav_path, current_transcript_path, current_sample_safe_name
        temp_path = current_temp_recording_path
        final_wav_path = current_final_wav_path
        final_txt_path = current_transcript_path
        safe_name = current_sample_safe_name

        if not temp_path or not temp_path.exists() or not final_wav_path or not final_txt_path or not safe_name:
            def handle_missing():
                zipvoice_samples_status_var.set("Recording did not produce any audio. Please try again.")
                zipvoice_sample_record_button.configure(state="normal")
                zipvoice_sample_stop_button.configure(state="disabled")
            window.after(0, handle_missing)
            return

        try:
            shutil.move(str(temp_path), str(final_wav_path))
        except Exception as exc:
            def handle_move_error():
                messagebox.showerror("File Error", f"Could not finalise recording: {exc}")
                zipvoice_samples_status_var.set("Failed to move recorded audio. Please try again.")
                zipvoice_sample_record_button.configure(state="normal")
                zipvoice_sample_stop_button.configure(state="disabled")
            window.after(0, handle_move_error)
            return

        transcript_text = transcribe_audio(str(final_wav_path)).strip()
        lowered = transcript_text.lower()
        whisper_model_missing = "model file not found" in lowered
        transcription_error = lowered.startswith("error") or lowered.startswith("an unexpected error")
        if whisper_model_missing:
            transcription_error = True

        text_to_persist = "" if whisper_model_missing else transcript_text

        try:
            Path(final_txt_path).write_text(text_to_persist, encoding="utf-8")
        except Exception as exc:
            transcription_error = True
            if not whisper_model_missing:
                transcript_text = transcript_text or ""
            def handle_write_error():
                messagebox.showerror("Transcript Error", f"Failed to write transcript: {exc}")
            window.after(0, handle_write_error)

        current_temp_recording_path = None

        def update_ui():
            if not window.winfo_exists():
                return
            zipvoice_transcript_text.configure(state="normal")
            zipvoice_transcript_text.delete("1.0", tk.END)
            display_text = "" if whisper_model_missing else transcript_text
            zipvoice_transcript_text.insert(tk.END, display_text)
            enable_transcript_controls(True)

            if transcription_error:
                if window.winfo_exists():
                    if whisper_model_missing:
                        messagebox.showwarning(
                            "Whisper Model Missing",
                            "Whisper could not find the configured model file. Download ggml-base.bin (or your selected model) into the models folder and try again.",
                        )
                    else:
                        messagebox.showwarning(
                            "Transcription",
                            "Whisper reported an error while transcribing. You can edit the transcript manually.",
                        )
                if whisper_model_missing:
                    zipvoice_samples_status_var.set(
                        "Whisper model not found. Add ggml-base.bin to the models folder, then re-run transcription."
                    )
                else:
                    zipvoice_samples_status_var.set("Transcription completed with warnings. Please review the text.")
            else:
                zipvoice_samples_status_var.set(f"Saved sample '{safe_name}'.")

            zipvoice_sample_record_button.configure(state="normal")
            zipvoice_sample_stop_button.configure(state="disabled")
            refresh_zipvoice_sample_sources(safe_name)

        window.after(0, update_ui)

    def stop_zipvoice_recording():
        nonlocal recording_in_progress
        if not recording_in_progress:
            return

        try:
            stop_audio_capture()
        except Exception as exc:
            messagebox.showerror("Recording", f"Could not stop recording cleanly: {exc}")
        recording_in_progress = False
        zipvoice_samples_status_var.set("Processing recording...")
        zipvoice_sample_stop_button.configure(state="disabled")
        threading.Thread(target=finalize_zipvoice_recording, daemon=True).start()

    def save_current_transcript():
        if not current_transcript_path or not current_sample_safe_name:
            messagebox.showinfo("Transcript", "Record a sample before saving the transcript.")
            return
        text_to_save = zipvoice_transcript_text.get("1.0", tk.END).strip()
        try:
            Path(current_transcript_path).write_text(text_to_save, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Save Failed", f"Could not save transcript: {exc}")
            return
        zipvoice_samples_status_var.set("Transcript saved.")
        refresh_zipvoice_sample_sources(current_sample_safe_name)

    zipvoice_sample_record_button.configure(command=start_zipvoice_recording)
    zipvoice_sample_stop_button.configure(command=stop_zipvoice_recording)
    zipvoice_save_transcript_button.configure(command=save_current_transcript)

    def ensure_recording_stopped_on_close():
        nonlocal recording_in_progress, current_temp_recording_path
        if recording_in_progress:
            try:
                stop_audio_capture()
            except Exception:
                pass
            recording_in_progress = False
        if current_temp_recording_path and current_temp_recording_path.exists():
            try:
                current_temp_recording_path.unlink()
            except Exception:
                pass
            current_temp_recording_path = None


    # --- Hardware Tab ---
    hardware_frame = ttk.LabelFrame(tabs["🛠️ Hardware"], text="Execution Providers", padding="10")
    hardware_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    hardware_frame.columnconfigure(1, weight=1)
    ttk.Label(hardware_frame, text="Kokoro TTS:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(hardware_frame, kokoro_execution_provider_var, kokoro_execution_provider_var.get(), "CPU", "CUDA").grid(row=0, column=1, sticky="ew", padx=5)
    
    ttk.Label(hardware_frame, text="Piper TTS:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(hardware_frame, piper_execution_provider_var, piper_execution_provider_var.get(), "CPU", "CUDA", "Tensorrt").grid(row=1, column=1, sticky="ew", padx=5)
    
    ttk.Label(hardware_frame, text="Whisper:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(hardware_frame, whisper_execution_provider_var, whisper_execution_provider_var.get(), "CPU", "GPU").grid(row=2, column=1, sticky="ew", padx=5)

    # --- Audio I/O Tab ---
    audio_io_frame = ttk.Frame(tabs["🎤 Audio I/O"], padding="10")
    audio_io_frame.pack(expand=True, fill="both")

    speaker_frame = ttk.LabelFrame(audio_io_frame, text="Global TTS Output Speaker", padding="10")
    speaker_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    speaker_frame.columnconfigure(1, weight=1)
    ttk.Label(speaker_frame, text="Output Device:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(speaker_frame, speaker_desc_var, initial_output_device_desc or "Select a device", *(output_device_map.keys())).grid(row=0, column=1, sticky="ew", padx=5)
    ttk.Button(speaker_frame, text="🔊 Test Speaker", command=lambda: play_test_sound(device_index=get_selected_device_index())).grid(row=1, column=1, sticky="e", padx=5, pady=5)

    tts_provider_frame = ttk.LabelFrame(audio_io_frame, text="TTS Provider", padding="10")
    tts_provider_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    tts_provider_frame.columnconfigure(1, weight=1)
    ttk.Label(tts_provider_frame, text="Active TTS Provider:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(tts_provider_frame, active_tts_provider_var, active_tts_provider_var.get(), "Windows SAPI", "OpenAI", "Kokoro TTS", "Piper TTS", "ZipVoice TTS").grid(row=0, column=1, sticky="ew", padx=5)

    tts_behavior_frame = ttk.LabelFrame(audio_io_frame, text="TTS Behavior", padding="10")
    tts_behavior_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
    ttk.Checkbutton(tts_behavior_frame, text="Automatically speak transcription result", variable=speak_transcription_var).pack(anchor="w")

    # --- Model Management Tab ---
    piper_models_frame = ttk.LabelFrame(tabs["📦 Models"], text="Piper TTS Models", padding="10")
    piper_models_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    piper_models_frame.columnconfigure(0, weight=1)

    piper_model_listbox = tk.Listbox(piper_models_frame, height=6)
    piper_model_listbox.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

    def refresh_piper_model_list():
        piper_model_listbox.delete(0, tk.END)
        for model_file in get_piper_model_files():
            piper_model_listbox.insert(tk.END, model_file)
        # Also refresh the main dropdown
        refresh_piper_model_dropdown()

    refresh_piper_model_list()

    def handle_import_models():
        if import_piper_models():
            refresh_piper_model_list()

    def delete_selected_piper_model():
        selected_indices = piper_model_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select a model to delete.")
            return
        
        selected_model = piper_model_listbox.get(selected_indices[0])
        if delete_piper_model(selected_model):
            refresh_piper_model_list()
            piper_model_file_var.set('')

    # Create a frame for the buttons
    model_buttons_frame = ttk.Frame(piper_models_frame)
    model_buttons_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    model_buttons_frame.columnconfigure(0, weight=1)
    model_buttons_frame.columnconfigure(1, weight=1)
    model_buttons_frame.columnconfigure(2, weight=1)

    import_button = ttk.Button(model_buttons_frame, text="Import Model(s)...", command=handle_import_models)
    import_button.grid(row=0, column=0, sticky="w", padx=5)

    delete_button = ttk.Button(model_buttons_frame, text="Delete Selected", command=delete_selected_piper_model)
    delete_button.grid(row=0, column=1, sticky="w", padx=5)

    def open_piper_models_page():
        webbrowser.open("https://huggingface.co/rhasspy/piper-voices/tree/main")

    download_button = ttk.Button(model_buttons_frame, text="Find More Models...", command=open_piper_models_page)
    download_button.grid(row=0, column=2, sticky="e", padx=5)

    # --- API Tab ---
    api_server_frame = ttk.LabelFrame(tabs["🌐 API"], text="API Server Settings", padding="10")
    api_server_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    api_server_frame.columnconfigure(1, weight=1)

    ttk.Checkbutton(api_server_frame, text="Enable API Server", variable=api_enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)
    ttk.Checkbutton(api_server_frame, text="Start Server Automatically on Startup", variable=api_auto_start_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)

    ttk.Label(api_server_frame, text="Server Port:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
    ttk.Entry(api_server_frame, textvariable=api_port_var, width=10).grid(row=2, column=1, sticky="w", padx=5)

    # --- API Server Status Indicator ---
    api_status_var = tk.StringVar()
    api_status_label = ttk.Label(api_server_frame, textvariable=api_status_var, font=("Segoe UI", 10, "bold"))
    api_status_label.grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    def update_api_status():
        status = is_api_running()
        if status == "running":
            api_status_var.set("API Server: Running")
            api_status_label.configure(foreground="green")
        elif status == "error":
            api_status_var.set("API Server: Error")
            api_status_label.configure(foreground="orange")
        else:
            api_status_var.set("API Server: Stopped")
            api_status_label.configure(foreground="red")
        # Poll every 10 seconds (was 3 seconds)
        api_status_label.after(10000, update_api_status)

    update_api_status()

    api_controls_frame = ttk.LabelFrame(tabs["🌐 API"], text="Server Controls", padding="10")
    api_controls_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
    api_controls_frame.columnconfigure(0, weight=1)
    api_controls_frame.columnconfigure(1, weight=1)
    api_controls_frame.columnconfigure(2, weight=1)

    def start_and_update():
        start_api_server()
        update_api_status()
    def stop_and_update():
        stop_api_server()
        update_api_status()
    def restart_and_update():
        restart_api_server()
        update_api_status()

    ttk.Button(api_controls_frame, text="▶️ Start Server", command=start_and_update).grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(api_controls_frame, text="⏹️ Stop Server", command=stop_and_update).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
    ttk.Button(api_controls_frame, text="🔄 Restart Server", command=restart_and_update).grid(row=0, column=2, sticky="ew", padx=5, pady=5)

    # --- MCP Tab ---
    mcp_frame = ttk.LabelFrame(tabs["🛠️ MCP"], text="MCP Server", padding="10")
    mcp_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    mcp_frame.columnconfigure(1, weight=1)

    mcp_auto_start_var = tk.BooleanVar(window, value=config.get('mcp', {}).get('auto_start', False))
    ttk.Checkbutton(mcp_frame, text="Auto-start MCP server on launch", variable=mcp_auto_start_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)

    mcp_status_label = ttk.Label(mcp_frame, text="MCP Status: Unknown")
    mcp_status_label.grid(row=1, column=0, sticky="w", padx=5, pady=2)

    mcp_log_panel = tk.Text(mcp_frame, height=10, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
    mcp_log_panel.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
    mcp_log_panel.configure(state="disabled") # Start disabled

    def populate_mcp_log():
        mcp_log_panel.configure(state="normal")
        mcp_log_panel.delete(1.0, tk.END)
        for line in get_mcp_log_history():
            mcp_log_panel.insert(tk.END, line + "\n")
        mcp_log_panel.yview(tk.END)
        mcp_log_panel.configure(state="disabled")

    def append_mcp_log(line):
        mcp_log_panel.configure(state="normal")
        mcp_log_panel.insert(tk.END, line + "\n")
        mcp_log_panel.yview(tk.END)
        mcp_log_panel.configure(state="disabled")

    register_mcp_log_callback(append_mcp_log)
    populate_mcp_log() # Populate with history on open

    def update_mcp_status():
        running = is_mcp_running()
        mcp_status_label.config(text=f"MCP Status: {'Running' if running else 'Stopped'}")
    update_mcp_status()

    ttk.Button(mcp_frame, text="Start MCP", command=lambda: [start_mcp(), update_mcp_status()]).grid(row=3, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(mcp_frame, text="Stop MCP", command=lambda: [stop_mcp(), update_mcp_status()]).grid(row=3, column=1, sticky="ew", padx=5, pady=5)
    ttk.Button(mcp_frame, text="Restart MCP", command=lambda: [restart_mcp(), update_mcp_status()]).grid(row=4, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(mcp_frame, text="Clear Logs", command=lambda: [clear_mcp_log_history(), populate_mcp_log()]).grid(row=4, column=1, sticky="ew", padx=5, pady=5)

    def ping_mcp():
        host = config.get('mcp', {}).get('host', '127.0.0.1')
        port = config.get('mcp', {}).get('port', 9032)
        url = f"http://{host}:{port}/health"
        try:
            r = requests.get(url, timeout=2.0)
            ok = (r.status_code == 200 and r.text.strip().lower() == 'ok')
            if ok:
                append_mcp_log(f"[GUI] MCP /health OK at {url}")
                mcp_status_label.config(text="MCP Status: Healthy", foreground="green")
                messagebox.showinfo("MCP Health", f"OK: {url}")
            else:
                append_mcp_log(f"[GUI] MCP /health BAD ({r.status_code}) at {url}")
                mcp_status_label.config(text="MCP Status: Running (Health check failed)", foreground="orange")
                messagebox.showwarning("MCP Health", f"Unexpected response ({r.status_code}): {r.text}")
        except Exception as e:
            append_mcp_log(f"[GUI] MCP /health ERROR: {e}")
            mcp_status_label.config(text="MCP Status: Stopped or Unreachable", foreground="red")
            messagebox.showerror("MCP Health", str(e))

    def mcp_test_speak():
        host = config.get('mcp', {}).get('host', '127.0.0.1')
        port = config.get('mcp', {}).get('port', 9032)
        url = f"http://{host}:{port}/speak"
        payload = {"text": "Hello from VibeType MCP test."}
        try:
            r = requests.post(url, json=payload, timeout=3.0)
            if r.status_code in (200, 202):
                append_mcp_log("[GUI] MCP /speak accepted (test message queued)")
                messagebox.showinfo("MCP Test Speak", "Test message queued for playback.")
            else:
                append_mcp_log(f"[GUI] MCP /speak failed ({r.status_code}): {r.text}")
                messagebox.showwarning("MCP Test Speak", f"Failed: {r.status_code}\n{r.text}")
        except Exception as e:
            append_mcp_log(f"[GUI] MCP /speak ERROR: {e}")
            messagebox.showerror("MCP Test Speak", str(e))

    ttk.Button(mcp_frame, text="Ping MCP /health", command=ping_mcp).grid(row=5, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(mcp_frame, text="Test Speak (Hello)", command=mcp_test_speak).grid(row=5, column=1, sticky="ew", padx=5, pady=5)

    def mcp_test_speak_batch():
        host = config.get('mcp', {}).get('host', '127.0.0.1')
        port = config.get('mcp', {}).get('port', 9032)
        url = f"http://{host}:{port}/speak_batch"
        payload = {
            "items": [
                {"text": "This is the first message."},
                {"text": "This is the second message, spoken after the first."},
                {"text": "And this is the final message."}
            ]
        }
        try:
            r = requests.post(url, json=payload, timeout=5.0)
            if r.status_code in (200, 202):
                append_mcp_log(f"[GUI] MCP /speak_batch accepted ({len(payload['items'])} items)")
                messagebox.showinfo("MCP Test Speak Batch", f"Batch of {len(payload['items'])} messages queued for sequential playback.")
            else:
                append_mcp_log(f"[GUI] MCP /speak_batch failed ({r.status_code}): {r.text}")
                messagebox.showwarning("MCP Test Speak Batch", f"Failed: {r.status_code}\n{r.text}")
        except Exception as e:
            append_mcp_log(f"[GUI] MCP /speak_batch ERROR: {e}")
            messagebox.showerror("MCP Test Speak Batch", str(e))

    def mcp_test_phonemes():
        host = config.get('mcp', {}).get('host', '127.0.0.1')
        port = config.get('mcp', {}).get('port', 9032)
        url = f"http://{host}:{port}/phonemes"
        # Test with a simple English and a multilingual string
        text_to_test = "Hello world. これは日本語です。"
        payload = {"text": text_to_test, "language": "Auto-Detect"}
        try:
            r = requests.post(url, json=payload, timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                append_mcp_log(f"[GUI] MCP /phonemes OK. Segments: {len(data.get('segments', []))}")
                # Pretty print the JSON to a message box
                pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
                # Show in a new window with a text widget to allow scrolling
                result_window = tk.Toplevel(window)
                result_window.title("Phoneme Result")
                result_text = tk.Text(result_window, wrap=tk.WORD, height=20, width=80)
                result_text.pack(padx=10, pady=10, fill="both", expand=True)
                result_text.insert(tk.END, pretty_json)
                result_text.configure(state="disabled")
            else:
                append_mcp_log(f"[GUI] MCP /phonemes failed ({r.status_code}): {r.text}")
                messagebox.showwarning("MCP Test Phonemes", f"Failed: {r.status_code}\n{r.text}")
        except Exception as e:
            append_mcp_log(f"[GUI] MCP /phonemes ERROR: {e}")
            messagebox.showerror("MCP Test Phonemes", str(e))

    ttk.Button(mcp_frame, text="Test /speak_batch", command=mcp_test_speak_batch).grid(row=6, column=0, sticky="ew", padx=5, pady=5)
    ttk.Button(mcp_frame, text="Test /phonemes", command=mcp_test_phonemes).grid(row=6, column=1, sticky="ew", padx=5, pady=5)

    # --- Save and Cancel Buttons ---
    def on_save():
        config['theme'] = theme_var.get()
        config['enable_text_injection'] = enable_text_injection_var.get()
        
        api_config_save = config.setdefault('api', {})
        api_config_save['enabled'] = api_enabled_var.get()
        api_config_save['auto_start'] = api_auto_start_var.get()
        api_config_save['port'] = api_port_var.get()

        # Persist MCP auto-start
        set_mcp_auto_start(mcp_auto_start_var.get())

        ollama_config_save = config.setdefault('ai_providers', {}).setdefault('Ollama', {})
        ollama_config_save['enabled'] = ollama_enabled_var.get()
        ollama_config_save['api_url'] = ollama_url_var.get()
        ollama_config_save['model'] = ollama_model_var.get()
        ollama_config_save['speak_response'] = ai_speak_response_var.get()
        ollama_config_save['use_thinking_fillers'] = use_thinking_fillers_var.get()
        ollama_config_save['webhook_enabled'] = webhook_enabled_var.get()
        ollama_config_save['webhook_url'] = webhook_url_var.get()
        
        prompts = {}
        for mode, text_widget in ai_prompt_entries.items():
            prompts[mode] = text_widget.get("1.0", tk.END).strip()
        ollama_config_save['prompts'] = prompts

        config['active_tts_provider'] = active_tts_provider_var.get()
        config.setdefault('tts_providers', {}).setdefault('Windows SAPI', {})['voice_index'] = sapi_voice_map.get(sapi_voice_desc_var.get(), 0)
        config.setdefault('tts_providers', {}).setdefault('Windows SAPI', {})['rate'] = sapi_rate_var.get()
        config.setdefault('tts_providers', {}).setdefault('Windows SAPI', {})['volume'] = sapi_volume_var.get()
        config.setdefault('tts_providers', {}).setdefault('OpenAI', {})['enabled'] = openai_enabled_var.get()
        config.setdefault('tts_providers', {}).setdefault('OpenAI', {})['api_key'] = openai_api_key_var.get()
        config.setdefault('tts_providers', {}).setdefault('OpenAI', {})['voice'] = openai_voice_var.get()
        config.setdefault('tts_providers', {}).setdefault('OpenAI', {})['speed'] = openai_speed_var.get()
        
        kokoro_config_save = config.setdefault('tts_providers', {}).setdefault('Kokoro TTS', {})
        kokoro_config_save['enabled'] = kokoro_enabled_var.get()
        kokoro_config_save['model_file'] = kokoro_model_file_var.get()
        kokoro_config_save['language'] = kokoro_language_var.get()
        kokoro_config_save['voice'] = kokoro_voice_var.get()
        kokoro_config_save['enable_voice_blending'] = kokoro_enable_blending_var.get()
        kokoro_config_save['voice_2'] = kokoro_voice_2_var.get()
        kokoro_config_save['voice_3'] = kokoro_voice_3_var.get()
        kokoro_config_save['voice_4'] = kokoro_voice_4_var.get()
        kokoro_config_save['voice_5'] = kokoro_voice_5_var.get()
        kokoro_config_save['enable_voice_2'] = kokoro_enable_voice_2_var.get()
        kokoro_config_save['enable_voice_3'] = kokoro_enable_voice_3_var.get()
        kokoro_config_save['enable_voice_4'] = kokoro_enable_voice_4_var.get()
        kokoro_config_save['enable_voice_5'] = kokoro_enable_voice_5_var.get()
        kokoro_config_save['voice_weight_1'] = kokoro_voice_weight_1_var.get()
        kokoro_config_save['voice_weight_2'] = kokoro_voice_weight_2_var.get()
        kokoro_config_save['voice_weight_3'] = kokoro_voice_weight_3_var.get()
        kokoro_config_save['voice_weight_4'] = kokoro_voice_weight_4_var.get()
        kokoro_config_save['voice_weight_5'] = kokoro_voice_weight_5_var.get()

        config.setdefault('tts_providers', {}).setdefault('Piper TTS', {})['enabled'] = piper_enabled_var.get()
        config.setdefault('tts_providers', {}).setdefault('Piper TTS', {})['model'] = piper_model_file_var.get()
        config.setdefault('tts_providers', {}).setdefault('Piper TTS', {})['voice'] = piper_voice_var.get()
        config.setdefault('tts_providers', {}).setdefault('Piper TTS', {})['length_scale'] = piper_length_scale_var.get()

        zipvoice_config_save = config.setdefault('tts_providers', {}).setdefault('ZipVoice TTS', {})
        zipvoice_config_save['enabled'] = zipvoice_enabled_var.get()
        zipvoice_config_save['sample_name'] = zipvoice_sample_var.get()
        zipvoice_config_save['model_name'] = zipvoice_model_var.get()
        zipvoice_config_save['backend'] = (zipvoice_backend_var.get() or 'torch').lower()
        zipvoice_config_save['speed'] = float(zipvoice_speed_var.get())
        zipvoice_config_save['prompt_mode'] = zipvoice_prompt_mode_var.get()
        seed_text = (zipvoice_seed_var.get() or "").strip()
        if seed_text:
            try:
                zipvoice_config_save['seed'] = int(seed_text)
            except ValueError:
                messagebox.showerror("ZipVoice", "ZipVoice seed must be an integer or left blank for random output.")
                return
        else:
            zipvoice_config_save.pop('seed', None)
        if zipvoice_prompt_mode_var.get() == 'profile':
            selected_profile_path = zipvoice_selected_profile_path_var.get().strip()
            if selected_profile_path:
                zipvoice_config_save['custom_prompt_profile'] = selected_profile_path
            else:
                zipvoice_config_save.pop('custom_prompt_profile', None)
            zipvoice_config_save['profile_name'] = zipvoice_profile_selection_var.get()
        else:
            zipvoice_config_save.pop('custom_prompt_profile', None)
            zipvoice_config_save.pop('profile_name', None)

        hardware_config_save = config.setdefault('hardware', {})
        hardware_config_save['kokoro_execution_provider'] = kokoro_execution_provider_var.get()
        hardware_config_save['piper_execution_provider'] = piper_execution_provider_var.get()
        hardware_config_save['whisper_execution_provider'] = whisper_execution_provider_var.get()
        
        config.setdefault('audio', {})['output_device_index'] = get_selected_device_index()
        selected_input_label = zipvoice_input_device_var.get()
        selected_input_info = input_device_map.get(selected_input_label)
        if selected_input_info:
            normalised_input = {
                'index': int(selected_input_info.get('index', 0) or 0),
                'loopback': bool(selected_input_info.get('loopback', False)),
                'channels': int(selected_input_info.get('channels', 1) or 1),
                'default_rate': int(float(selected_input_info.get('default_rate', 16000) or 16000)),
            }
        else:
            normalised_input = {'index': 0, 'loopback': False, 'channels': 1, 'default_rate': 16000}
        config['input_device'] = normalised_input
        config['input_device_index'] = normalised_input['index']
        config.setdefault('audio', {})['speak_transcription_result'] = speak_transcription_var.get()
        config.setdefault('history', {})['transcript_limit'] = transcript_limit_var.get()
        config.setdefault('user_experience', {})['show_status_overlay'] = show_status_overlay_var.get()
        
        privacy_config_save = config.setdefault('privacy', {})
        privacy_config_save['clipboard_privacy'] = clipboard_privacy_var.get()
        privacy_config_save['local_only_mode'] = local_only_mode_var.get()
        privacy_config_save['enable_hotkeys'] = enable_hotkeys_var.get()
        privacy_config_save['enable_microphone'] = enable_microphone_var.get()

        new_hotkeys = {}
        for action, hotkey_vars in hotkeys_vars.items():
            new_hotkeys[action] = [var.get() for var in hotkey_vars if var.get()]
        config['hotkeys'] = new_hotkeys

        # Persist MCP settings
        mcp_cfg = config.setdefault('mcp', {})
        mcp_cfg['auto_start'] = mcp_auto_start_var.get()
        # Apply immediately for future launches
        set_mcp_auto_start(mcp_auto_start_var.get())

        save_config(config)
        messagebox.showinfo("Settings Saved", "Your settings have been saved. Please restart VibeType for all changes to take effect.")
        if on_save_callback: on_save_callback()
        ensure_recording_stopped_on_close()
        window.destroy()

    def close_window():
        ensure_recording_stopped_on_close()
        window.destroy()

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(side="bottom", fill="x", padx=10, pady=10, anchor="se")
    ttk.Button(button_frame, text="✔️ Save", command=on_save).pack(side=tk.RIGHT, padx=5)
    ttk.Button(button_frame, text="❌ Cancel", command=close_window).pack(side=tk.RIGHT)

    window.protocol("WM_DELETE_WINDOW", close_window)
    return window
