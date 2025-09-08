# gui/settings_window.py

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
import os
import json

# Import from core
from core.config_manager import load_config, save_config
from core.tts import (
    get_available_sapi_voices, get_kokoro_voices, get_output_devices,
    play_test_sound, speak_text, trigger_kokoro_model_download,
    open_benchmark_folder, get_kokoro_models, trigger_kokoro_benchmark,
    test_kokoro_voice, get_piper_model_files, get_voices_for_piper_model,
    test_sapi_voice, test_piper_voice, test_openai_voice, get_kokoro_languages
)
from core.ai import test_ollama_connection, send_webhook_test, get_ai_response, get_ollama_models
from core.model_manager import delete_piper_model
from core.transcript_saver import clear_transcript_history
from core.analytics import load_analytics_data, reset_analytics_data
from core.performance_monitor import get_performance_metrics

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
    sapi_voices = get_available_sapi_voices()
    sapi_voice_map = {desc: index for desc, index in sapi_voices}
    sapi_index_map = {index: desc for desc, index in sapi_voices}
    output_device_map = {name: index for name, index in output_devices.items()}
    output_index_map = {index: name for name, index in output_devices.items()}

    # --- Helper Functions (defined early to avoid NameError) ---
    def get_selected_device_index():
        return output_device_map.get(speaker_desc_var.get())

    # --- Variables ---
    theme_var = tk.StringVar(window, value=config.get('theme', 'System'))
    enable_text_injection_var = tk.BooleanVar(window, value=config.get('enable_text_injection'))
    
    ollama_config = config.get('ai_providers', {}).get('Ollama', {})
    ollama_enabled_var = tk.BooleanVar(window, value=ollama_config.get('enabled', False))
    ollama_url_var = tk.StringVar(window, value=ollama_config.get('api_url', ''))
    ollama_model_var = tk.StringVar(window, value=ollama_config.get('model', ''))
    ai_speak_response_var = tk.BooleanVar(window, value=ollama_config.get('speak_response', True))
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

    hardware_config = config.get('hardware', {})
    kokoro_execution_provider_var = tk.StringVar(window, value=hardware_config.get('kokoro_execution_provider', 'CPU'))
    whisper_execution_provider_var = tk.StringVar(window, value=hardware_config.get('whisper_execution_provider', 'CPU'))

    audio_config = config.get('audio', {})
    initial_output_device_desc = output_index_map.get(audio_config.get('output_device_index'))
    speaker_desc_var = tk.StringVar(window, value=initial_output_device_desc)
    speak_transcription_var = tk.BooleanVar(window, value=audio_config.get('speak_transcription_result', True))

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
    tabs = {name: ttk.Frame(notebook, padding="10") for name in ["⚙️ General", "⌨️ Hotkeys", "🤖 AI", "🎤 Audio I/O", "🔊 Windows SAPI", "🤖 OpenAI TTS", "❤️ Kokoro TTS", "🐍 Piper TTS", "🛠️ Hardware", "📦 Models", "🔐 Security & Privacy", "📊 Analytics"]}
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
    ttk.Button(history_frame, text="Clear Transcript History", command=clear_transcript_history).grid(row=1, column=0, columnspan=2, pady=5)

    # --- Hotkeys Tab ---
    hotkey_canvas = tk.Canvas(tabs["⌨️ Hotkeys"], bg=theme_bg, highlightthickness=0)
    hotkey_scrollbar = ttk.Scrollbar(tabs["⌨️ Hotkeys"], orient="vertical", command=hotkey_canvas.yview)
    hotkey_scrollable_frame = ttk.Frame(hotkey_canvas)
    hotkey_scrollable_frame.bind("<Configure>", lambda e: hotkey_canvas.configure(scrollregion=hotkey_canvas.bbox("all")))
    hotkey_canvas.create_window((0, 0), window=hotkey_scrollable_frame, anchor="nw")
    hotkey_canvas.configure(yscrollcommand=hotkey_scrollbar.set)
    hotkey_canvas.pack(side="left", fill="both", expand=True)
    hotkey_scrollbar.pack(side="right", fill="y")
    
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

    for i, (action, hotkeys) in enumerate(hotkeys_vars.items()):
        action_frame = ttk.LabelFrame(hotkey_scrollable_frame, text=action.replace('_', ' ').title(), padding="10")
        action_frame.grid(row=i, column=0, sticky="ew", padx=10, pady=5)
        action_frame.columnconfigure(0, weight=1)
        action_frames[action] = action_frame
        _redraw_action_frame(action)
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

    reset_button = ttk.Button(stats_frame, text="Reset Statistics", command=handle_reset_analytics)
    reset_button.pack(pady=5)

    populate_analytics_tree()

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

    ttk.Checkbutton(mixer_frame, text="Enable Voice Blending", variable=kokoro_enable_blending_var).grid(row=0, column=0, columnspan=3, sticky="w", padx=5)

    # Voice 1 (Primary)
    ttk.Label(mixer_frame, text="Primary Voice:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_1_var).grid(row=1, column=1, sticky="ew", padx=5)

    # Voice 2
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_2_var).grid(row=2, column=0, sticky="w", padx=5)
    kokoro_voice_2_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_2_var, kokoro_voice_2_var.get() or "Select a voice")
    kokoro_voice_2_menu.grid(row=2, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_2_var).grid(row=2, column=2, sticky="ew", padx=5)

    # Voice 3
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_3_var).grid(row=3, column=0, sticky="w", padx=5)
    kokoro_voice_3_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_3_var, kokoro_voice_3_var.get() or "Select a voice")
    kokoro_voice_3_menu.grid(row=3, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_3_var).grid(row=3, column=2, sticky="ew", padx=5)

    # Voice 4
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_4_var).grid(row=4, column=0, sticky="w", padx=5)
    kokoro_voice_4_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_4_var, kokoro_voice_4_var.get() or "Select a voice")
    kokoro_voice_4_menu.grid(row=4, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_4_var).grid(row=4, column=2, sticky="ew", padx=5)

    # Voice 5
    ttk.Checkbutton(mixer_frame, text="", variable=kokoro_enable_voice_5_var).grid(row=5, column=0, sticky="w", padx=5)
    kokoro_voice_5_menu = ttk.OptionMenu(mixer_frame, kokoro_voice_5_var, kokoro_voice_5_var.get() or "Select a voice")
    kokoro_voice_5_menu.grid(row=5, column=1, sticky="ew", padx=5)
    ttk.Scale(mixer_frame, from_=0, to=1, orient='horizontal', variable=kokoro_voice_weight_5_var).grid(row=5, column=2, sticky="ew", padx=5)

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
    kokoro_test_text_var = tk.StringVar(window, value="The quick brown fox jumps over the lazy dog.")
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
    ttk.Label(piper_main_frame, text="Model File:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    piper_model_menu = ttk.OptionMenu(piper_main_frame, piper_model_file_var, piper_model_file_var.get() or "Select a model", *get_piper_model_files())
    piper_model_menu.grid(row=1, column=1, sticky="ew", padx=5)
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

    # --- Hardware Tab ---
    hardware_frame = ttk.LabelFrame(tabs["🛠️ Hardware"], text="Execution Providers", padding="10")
    hardware_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
    hardware_frame.columnconfigure(1, weight=1)
    ttk.Label(hardware_frame, text="Kokoro TTS:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(hardware_frame, kokoro_execution_provider_var, kokoro_execution_provider_var.get(), "CPU", "CUDA").grid(row=0, column=1, sticky="ew", padx=5)
    ttk.Label(hardware_frame, text="Whisper:").grid(row=1, column=0, sticky="w", padx=5, pady=2)
    ttk.OptionMenu(hardware_frame, whisper_execution_provider_var, whisper_execution_provider_var.get(), "CPU", "GPU").grid(row=1, column=1, sticky="ew", padx=5)

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
    ttk.OptionMenu(tts_provider_frame, active_tts_provider_var, active_tts_provider_var.get(), "Windows SAPI", "OpenAI", "Kokoro TTS", "Piper TTS").grid(row=0, column=1, sticky="ew", padx=5)

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

    delete_button = ttk.Button(piper_models_frame, text="Delete Selected Model", command=delete_selected_piper_model)
    delete_button.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    def open_piper_models_page():
        webbrowser.open("https://huggingface.co/rhasspy/piper-voices/tree/main")

    download_button = ttk.Button(piper_models_frame, text="Download More Models...", command=open_piper_models_page)
    download_button.grid(row=1, column=1, sticky="e", padx=5, pady=5)

    # --- Save and Cancel Buttons ---
    def on_save():
        config['theme'] = theme_var.get()
        config['enable_text_injection'] = enable_text_injection_var.get()
        
        ollama_config_save = config.setdefault('ai_providers', {}).setdefault('Ollama', {})
        ollama_config_save['enabled'] = ollama_enabled_var.get()
        ollama_config_save['api_url'] = ollama_url_var.get()
        ollama_config_save['model'] = ollama_model_var.get()
        ollama_config_save['speak_response'] = ai_speak_response_var.get()
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
        config.setdefault('hardware', {})['kokoro_execution_provider'] = kokoro_execution_provider_var.get()
        config.setdefault('hardware', {})['whisper_execution_provider'] = whisper_execution_provider_var.get()
        config.setdefault('audio', {})['output_device_index'] = get_selected_device_index()
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

        save_config(config)
        messagebox.showinfo("Settings Saved", "Your settings have been saved. Please restart VibeType for all changes to take effect.")
        if on_save_callback: on_save_callback()
        window.destroy()

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(side="bottom", fill="x", padx=10, pady=10, anchor="se")
    ttk.Button(button_frame, text="✔️ Save", command=on_save).pack(side=tk.RIGHT, padx=5)
    ttk.Button(button_frame, text="❌ Cancel", command=window.destroy).pack(side=tk.RIGHT)

    window.protocol("WM_DELETE_WINDOW", window.destroy)
    return window
