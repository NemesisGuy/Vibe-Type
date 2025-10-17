import json
import pyaudio
from core.utils import get_config_path
import collections.abc
from core.encryption import encrypt, decrypt
import copy

from core.zipvoice_manager import DEFAULT_SAMPLE_NAME

# Define which fields in the config should be encrypted.
# The path is represented as a tuple of keys.
SENSITIVE_FIELDS = {
    ('ai_providers', 'Ollama', 'webhook_url'),
    ('tts_providers', 'OpenAI', 'api_key'),
    ('ai_providers', 'Cohere', 'api_key'),
}

def _traverse_and_apply(config, func):
    """Traverses the config and applies the function to sensitive fields."""
    for path in SENSITIVE_FIELDS:
        current_level = config
        try:
            for i, key in enumerate(path):
                if i == len(path) - 1:
                    if key in current_level and current_level[key]:
                        current_level[key] = func(current_level[key])
                else:
                    current_level = current_level[key]
        except (KeyError, TypeError):
            # Path doesn't exist in this config, skip.
            continue

def get_default_input_device_index():
    """Gets the index of the default input device using PyAudio."""
    pa = pyaudio.PyAudio()
    try:
        return pa.get_default_input_device_info()['index']
    except (IOError, KeyError):
        print("Could not determine default input device.")
        return 0 # Fallback if no default device is found
    finally:
        pa.terminate()

def deep_update(d, u):
    """Recursively update a dictionary with values from another, creating keys if they don't exist."""
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def load_config():
    """Loads configuration, applying defaults and decrypting sensitive fields."""
    config_path = get_config_path()
    defaults = {
        "hotkeys": {
            "toggle_dictation": ["<alt>+<caps_lock>"],
            "ai_dictation": ["<scroll_lock>"],
            "process_clipboard": ["<ctrl>+<alt>+p"],
            "explain_text": ["<alt>+<ctrl>+e"],
            "read_text": ["<alt>+<ctrl>+s"],
            "voice_conversation": ["<alt>+<ctrl>+t"],
            "summarize_text": ["<ctrl>+<alt>+z"],
            "correct_text": ["<ctrl>+<alt>+x"],
            "speak_from_clipboard": ["<ctrl>+<alt>+c"],
            "interrupt_speech": ["<ctrl>+<alt>+i"]
        },
        
        "active_ai_provider": "Ollama",
        "ai_providers": {
            "Ollama": {"enabled": True, "api_url": "http://localhost:11434", "model": "llama2", "webhook_url": ""},
            "Cohere": {"enabled": False, "api_key": "", "model": "command-r"}
        },
        
        "active_tts_provider": "Windows SAPI",
        "tts_providers": {
            "Windows SAPI": {"enabled": True, "voice_index": 0, "rate": 175},
            "OpenAI": {"enabled": False, "api_key": "", "model": "tts-1", "voice": "alloy"},
            "Kokoro TTS": {"enabled": False, "model_file": "kokoro-v1.0.int8.onnx", "voice": "am_adam"},
            "Piper TTS": {"enabled": False, "model": "en_US-lessac-medium.onnx"},
            "ZipVoice TTS": {
                "enabled": False,
                "backend": "torch",
                "model_name": "zipvoice",
                "sample_name": DEFAULT_SAMPLE_NAME,
                "speed": 1.0,
                "guidance_scale": None,
                "num_step": None,
                "target_rms": 0.1,
                "t_shift": 1.0,
                "remove_long_sil": False,
                "custom_prompt_wav": "",
                "custom_prompt_text_path": "",
                "custom_prompt_text": "",
                "model_dir": "",
                "torch_checkpoint": "",
                "torch_device": "",
                "vocoder_device": "cpu",
                "max_total_seconds": 25.0,
                "num_thread": 6,
                "onnx_int8": False
            }
        },

        "active_prompt": "Assistant",
        "prompt_templates": [
            {"name": "Assistant", "prompt": "You are a helpful assistant. Please be concise."},
            {"name": "Corrector", "prompt": "Correct the grammar and spelling of the following text, maintaining the original meaning and tone. Only output the corrected text."},
            {"name": "Summarizer", "prompt": "Summarize the following text into a few key points."},
            {"name": "Chat", "prompt": "You are a conversational AI. Respond to the following as if in a natural, free-flowing conversation."}
        ],
        
        "hardware": {
            "kokoro_execution_provider": "CPU",
            "piper_execution_provider": "CPU",
            "whisper_execution_provider": "CPU"
        },
        "history": {
            "transcript_limit": 100
        },
        "user_experience": {
            "show_status_overlay": True
        },
        "privacy": {
            "clipboard_privacy": False,
            "local_only_mode": False
        },

        "enable_text_injection": True,
        "language": "en", 
        "input_device_index": get_default_input_device_index(),
        "theme": "System",
        "whisper_model": "base",
        # New default API section so auto-start has predictable settings
        "api": {
            "auto_start": False,
            "port": 9031,
            "host": "0.0.0.0"
        }
    }
    
    config = defaults.copy()
    try:
        with open(config_path, 'r') as f:
            user_config = json.load(f)
            # Decrypt before merging
            _traverse_and_apply(user_config, decrypt)
            deep_update(config, user_config)

    except (FileNotFoundError, json.JSONDecodeError):
        pass
        
    # Ensure all hotkeys are lists for backward compatibility
    for action, hotkey in config.get("hotkeys", {}).items():
        if isinstance(hotkey, str):
            config["hotkeys"][action] = [hotkey]
            
    return config

def save_config(config):
    """Saves the configuration, encrypting sensitive fields before writing."""
    config_path = get_config_path()
    
    # Create a deep copy to avoid encrypting the live config object
    config_to_save = copy.deepcopy(config)
    
    # Encrypt sensitive fields before saving
    _traverse_and_apply(config_to_save, encrypt)
    
    with open(config_path, 'w') as f:
        json.dump(config_to_save, f, indent=4)

def get_mcp_auto_start(config):
    return config.get('mcp', {}).get('auto_start', False)

def set_mcp_auto_start(config, value):
    if 'mcp' not in config:
        config['mcp'] = {}
    config['mcp']['auto_start'] = value
    return config
