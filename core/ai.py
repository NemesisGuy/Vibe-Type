# core/ai.py

import requests
from tkinter import messagebox
import json
import re # Import the regular expression module
from core.config_manager import load_config
from core.thinking_fillers import thinking_fillers

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

def get_ai_response(prompt: str, mode: str, use_fillers: bool = True, tts_callback=None) -> str:
    """
    Sends a prompt to the configured Ollama server and returns ONLY the final, clean response.

    Args:
        prompt: The user's input text
        mode: AI mode (Summarize, Explain, Correct, Chat)
        use_fillers: Whether to speak filler phrases while waiting
        tts_callback: Function to call for TTS (voice, text, language, speed)
    """
    config = load_config()
    ollama_config = config.get('ai_providers', {}).get('Ollama', {})

    if not ollama_config.get('enabled'):
        return "Ollama is not enabled in the settings."

    api_url = ollama_config.get('api_url')
    model = ollama_config.get('model')
    show_thought_process = ollama_config.get('show_thought_process', False)

    default_prompts = {
        "Summarize": "Summarize the following text, focusing on the key points and main ideas.",
        "Explain": "Explain the following text in simple and easy-to-understand terms. Use analogies or examples if helpful.",
        "Correct": "Correct any grammatical errors, spelling mistakes, or typos in the following text. Preserve the original meaning.",
        "Chat": "You are a helpful AI assistant. Respond to the user's query in a conversational and informative manner."
    }
    base_system_prompt = ollama_config.get('prompts', {}).get(mode, default_prompts.get(mode, ''))

    if show_thought_process:
        system_prompt = (
            f"First, think step-by-step inside <think> tags. Then, provide your final, concise answer outside the tags."
        )
    else:
        system_prompt = (
            f"IMPORTANT: Provide only the final, concise answer. Do not include any preliminary thoughts or XML tags. Your response must be clean, direct, and ready for a Text-to-Speech engine."
        )

    if not api_url or not model:
        return "Ollama API URL or model is not configured."

    full_prompt = f"{base_system_prompt}\n\n{system_prompt}\n\nUser: {prompt}\nAI:"

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }

    # Set up thinking fillers if TTS callback is provided
    if use_fillers and tts_callback:
        # Get configurable timing parameters from config
        filler_config = ollama_config.get('filler_initial_delay', 0.5)
        interval_min = ollama_config.get('filler_interval_min', 2.5)
        interval_max = ollama_config.get('filler_interval_max', 5.0)

        thinking_fillers.set_speak_callback(lambda text: tts_callback("am_adam", text, "English (US)", 1.0))
        thinking_fillers.start_thinking_mode(
            initial_delay=filler_config,
            interval_min=interval_min,
            interval_max=interval_max
        )

    try:
        response = requests.post(f"{api_url}/api/generate", json=payload, timeout=60)
        response.raise_for_status()

        # Stop fillers before processing response - with error handling
        if use_fillers:
            try:
                thinking_fillers.stop_thinking_mode()
                # Give a brief moment for cleanup to complete
                import time
                time.sleep(0.2)
            except Exception as e:
                print(f"Warning: Error stopping thinking fillers: {e}")

        response_data = response.json()
        raw_text = response_data.get("response", "").strip()

        # --- DEFINITIVE FIX: Process and clean the text HERE, at the source ---
        # This robustly finds the closing think tag and takes only the text after it.
        # This is the only way to guarantee that the rest of the application
        # NEVER sees the AI's internal monologue.
        parts = re.split(r'</think.*?>', raw_text, maxsplit=1, flags=re.IGNORECASE | re.DOTALL)
        if len(parts) > 1:
            final_text = parts[-1].strip()
        else:
            final_text = raw_text # No think tag found, use the whole response

        # Speak a completion phrase if using fillers - with thread safety
        if use_fillers and tts_callback:
            try:
                completion_phrase = thinking_fillers.get_completion_phrase()
                # Use a small delay to avoid thread conflicts
                import threading
                def delayed_completion():
                    import time
                    time.sleep(0.3)  # Brief delay to avoid TTS conflicts
                    try:
                        tts_callback("am_adam", completion_phrase, "English (US)", 1.0)
                    except Exception as e:
                        print(f"Warning: Error speaking completion phrase: {e}")

                completion_thread = threading.Thread(target=delayed_completion, daemon=True)
                completion_thread.start()
            except Exception as e:
                print(f"Warning: Error with completion phrase: {e}")

        post_to_webhook(final_text, source=f"AI Response ({mode})")
        return final_text

    except requests.exceptions.RequestException as e:
        # Stop fillers on error
        if use_fillers:
            thinking_fillers.stop_thinking_mode()
        error_message = f"Failed to get response from Ollama: {e}"
        print(error_message)
        return error_message
    except json.JSONDecodeError as e:
        # Stop fillers on error
        if use_fillers:
            thinking_fillers.stop_thinking_mode()
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