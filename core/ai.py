# core/ai.py

import requests
from tkinter import messagebox
import json
from core.config_manager import load_config

def test_ollama_connection(api_url: str):
    """Tests the connection to the Ollama API server."""
    config = load_config()
    if config.get('privacy', {}).get('local_only_mode', False):
        messagebox.showinfo("Local-Only Mode", "Network requests are disabled in Local-Only Mode.")
        return

    if not api_url:
        messagebox.showerror("Error", "Ollama API URL is not set.")
        return

    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            messagebox.showinfo("Success", f"Successfully connected to Ollama at {api_url}.")
        else:
            messagebox.showwarning("Warning", f"Connected to {api_url}, but received status code: {response.status_code}. Ollama may not be running.")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Connection Error", f"Failed to connect to Ollama at {api_url}.\n\nError: {e}")

def send_webhook_test(webhook_url: str):
    """Sends a test payload to the configured webhook URL."""
    config = load_config()
    if config.get('privacy', {}).get('local_only_mode', False):
        messagebox.showinfo("Local-Only Mode", "Network requests are disabled in Local-Only Mode.")
        return

    if not webhook_url:
        messagebox.showerror("Error", "Webhook URL is not set.")
        return

    headers = {'Content-Type': 'application/json'}
    payload = {
        "text": "This is a test payload from VibeType.",
        "source": "VibeType Webhook Test"
    }

    try:
        response = requests.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=10)
        if 200 <= response.status_code < 300:
            messagebox.showinfo("Success", f"Successfully sent test payload to {webhook_url}.\n\nStatus Code: {response.status_code}")
        else:
            messagebox.showwarning("Webhook Test Failed", f"Failed to send test payload to {webhook_url}.\n\nStatus Code: {response.status_code}\nResponse: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Webhook Connection Error", f"Failed to connect to webhook at {webhook_url}.\n\nError: {e}")

def post_to_webhook(text: str, source: str = "AI Response"):
    """Posts the given text to the user-configured webhook if enabled."""
    config = load_config()
    if config.get('privacy', {}).get('local_only_mode', False):
        print("Local-Only Mode is enabled. Skipping webhook.")
        return

    ollama_config = config.get('ai_providers', {}).get('Ollama', {})
    
    if not ollama_config.get('webhook_enabled', False):
        return

    webhook_url = ollama_config.get('webhook_url')
    if not webhook_url:
        print("Webhook is enabled, but no URL is configured.")
        return

    headers = {'Content-Type': 'application/json'}
    payload = {
        "text": text,
        "source": source
    }

    try:
        with requests.Session() as session:
            response = session.post(webhook_url, headers=headers, data=json.dumps(payload), timeout=10)
            if not (200 <= response.status_code < 300):
                print(f"Webhook call to {webhook_url} failed with status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending to webhook at {webhook_url}: {e}")
