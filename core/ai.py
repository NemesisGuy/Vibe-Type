# core/ai.py

import requests
from tkinter import messagebox
import json
from core.config_manager import load_config

def get_ollama_models(api_url: str) -> list:
    """Fetches the list of available models from the Ollama API."""
    if not api_url:
        messagebox.showerror("Error", "Ollama API URL is not set.")
        return []
    try:
        response = requests.get(f"{api_url}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [model["name"] for model in models]
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Connection Error", f"Could not fetch models from Ollama: {e}")
        return []
    except json.JSONDecodeError:
        messagebox.showerror("API Error", "Received an invalid response from the Ollama API.")
        return []

def get_ai_response(prompt: str, mode: str) -> str:
    """
    Sends a prompt to the configured Ollama server using the specified mode's system prompt and returns the AI's response.
    """
    config = load_config()
    ollama_config = config.get('ai_providers', {}).get('Ollama', {})

    if not ollama_config.get('enabled'):
        return "Ollama is not enabled in the settings."

    api_url = ollama_config.get('api_url')
    model = ollama_config.get('model')
    
    # Get the specific system prompt for the given mode, with a fallback to default prompts
    default_prompts = {
        "Summarize": "Summarize the following text, focusing on the key points and main ideas. Be concise and clear. Be concise , your response will be spoken via TTS exactly as you reply",
        "Explain": "Be concise, you are a helpful ai voice assistant , your response will be spoken via TTS exactly as you reply Explain the following text in simple and easy-to-understand terms. Use analogies or examples if helpful. Be concise , your response will be spoken via TTS exactly as you reply",
        "Correct": "Correct any grammatical errors, spelling mistakes, or typos in the following text. Preserve the original meaning. Be concise , your response will be spoken via TTS exactly as you reply",
        "Chat": "You are a helpful AI assistant. Respond to the user's query in a conversational and informative manner. Be concise , your response will be spoken via TTS exactly as you reply"
    }
    system_prompt = ollama_config.get('prompts', {}).get(mode, default_prompts.get(mode, ''))

    if not api_url or not model:
        return "Ollama API URL or model is not configured."

    full_prompt = f"{system_prompt}\n\nUser: {prompt}\nAI:"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(f"{api_url}/api/generate", json=payload, timeout=60)
        response.raise_for_status()
        
        response_data = response.json()
        final_text = response_data.get("response", "").strip()
        
        post_to_webhook(final_text, source=f"AI Response ({mode})")
        return final_text

    except requests.exceptions.RequestException as e:
        error_message = f"Failed to get response from Ollama: {e}"
        print(error_message)
        return error_message
    except json.JSONDecodeError as e:
        error_message = f"Failed to decode Ollama response: {e}\nResponse text: {response.text}"
        print(error_message)
        return error_message

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
