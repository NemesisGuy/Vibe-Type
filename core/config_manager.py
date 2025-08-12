# core/config_manager.py

import json
from pathlib import Path

class ConfigManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ConfigManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, config_path="config/config.json"):
        if hasattr(self, 'initialized'):
            return
        self.initialized = True

        self.config_path = Path(config_path)
        self.config = {}
        self.load_config()

    def load_config(self):
        """Loads the configuration from the JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            print("Configuration loaded successfully.")
        except FileNotFoundError:
            print(f"Warning: Configuration file not found at {self.config_path}. Using default values.")
            self.config = self.get_default_config()
            self.save_config()
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.config_path}. Using default values.")
            self.config = self.get_default_config()

    def get(self, key, default=None):
        """Gets a configuration value by key."""
        return self.config.get(key, default)

    def set(self, key, value):
        """Sets a configuration value by key."""
        self.config[key] = value

    def save_config(self):
        """Saves the current configuration to the JSON file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("Configuration saved successfully.")
        except IOError as e:
            print(f"Error saving configuration: {e}")

    def get_default_config(self):
        """Returns the default configuration."""
        return {
            "hotkey": "Ctrl+Alt+Space",
            "whisper_model": "base",
            "output_mode": "inject", # 'inject' or 'clipboard'
            "auto_save_transcripts": True
        }

# Global instance
config_manager = ConfigManager()
