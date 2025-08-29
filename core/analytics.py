# core/analytics.py

import json
import os
from .utils import get_config_path
from collections import defaultdict

ANALYTICS_PATH = os.path.join(os.path.dirname(get_config_path()), "analytics.json")

def load_analytics_data():
    """Loads analytics data from a JSON file."""
    if not os.path.exists(ANALYTICS_PATH):
        return {
            "tts_engine_usage": {},
            "ai_mode_usage": {},
            "hotkey_usage": {}
        }
    try:
        with open(ANALYTICS_PATH, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "tts_engine_usage": {},
            "ai_mode_usage": {},
            "hotkey_usage": {}
        }

def save_analytics_data(data):
    """Saves analytics data to a JSON file."""
    with open(ANALYTICS_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def increment_usage(category: str, item: str):
    """Increments the usage count for a specific category and item."""
    data = load_analytics_data()
    
    # Ensure the category exists
    if category not in data:
        data[category] = {}
        
    # Increment the item count
    data[category][item] = data[category].get(item, 0) + 1
    
    save_analytics_data(data)

def reset_analytics_data():
    """Resets all analytics data."""
    if os.path.exists(ANALYTICS_PATH):
        os.remove(ANALYTICS_PATH)
    print("Analytics data has been reset.")
