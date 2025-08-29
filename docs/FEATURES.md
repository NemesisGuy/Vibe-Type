# VibeType Features

This document provides a detailed overview of every feature available in VibeType, including the default hotkeys and how to use them.

## Core Hotkeys

VibeType is controlled by a set of global hotkeys that work in any application.

*   **Standard Dictation (`<alt>+<caps_lock>`):** Starts/stops audio recording. Transcribes the audio using Whisper and injects the text.
*   **AI Dictation (`<scroll_lock>`):** Transcribes your speech, then processes it with your **selected AI Provider** using the active **AI Mode**.
*   **Process Clipboard (AI) (`<ctrl>+<alt>+t`):** Takes text from your clipboard and processes it with your **selected AI Provider**.
*   **Speak from Clipboard (`<ctrl>+<alt>+r`):** Reads the text on your clipboard aloud using your **selected TTS Provider**.

## Pluggable Providers

VibeType's power comes from its flexibility. You can choose which backend services you want to use for both AI processing and voice output. You can configure these in the **Settings** window.

### AI (LLM) Providers

Choose the language model that best fits your needs for tasks like code generation, correction, and summarization.

*   **Ollama (Local First):**
    *   **Type:** Local
    *   **Default:** Enabled
    *   **Description:** Runs entirely on your own machine for maximum privacy. Requires a running Ollama instance.
    *   **Configuration:** Set the API URL (e.g., `http://localhost:11434`) and the name of the model you have downloaded (e.g., `llama3`, `codellama`).

*   **Cohere:**
    *   **Type:** External API
    *   **Default:** Disabled
    *   **Description:** A powerful, cloud-based provider. Offers excellent performance for a wide range of tasks.
    *   **Configuration:** Requires a Cohere API Key.

### Text-to-Speech (TTS) Providers

Choose the voice you want to hear for audio feedback.

*   **Windows SAPI (Local First):**
    *   **Type:** Local
    *   **Default:** Enabled
    *   **Description:** Uses the voices built into the Windows operating system. Fast, reliable, and requires no internet connection.
    *   **Configuration:** Select from a list of available voices on your system and adjust the speech rate.

*   **Kokoro TTS (Local):**
    *   **Type:** Custom Local
    *   **Default:** Disabled
    *   **Description:** Allows you to use a custom, high-quality local TTS engine like Kokoro TTS. Requires a separate executable file.
    *   **Configuration:** You must provide the full path to the Kokoro TTS executable file (e.g., `C:\path\to\kokoro.exe`). The command-line arguments are currently assumed and may need to be adjusted in the code.

## The AI Toolkit: Modes

Select an AI Mode to change the AI's "personality" and tell it what kind of task to perform. The active mode is used by the **AI Dictation** and **Process Clipboard** hotkeys.

*   **Assistant Mode:** A general-purpose conversational AI for answering questions or generating text.
*   **Corrector Mode:** Fixes grammar and spelling mistakes without changing the meaning. Ideal for cleaning up dictation.
*   **Summarizer Mode:** Condenses long text into key points. Perfect for summarizing articles from your clipboard.

## Customization

All hotkeys, provider settings (API keys, URLs, models), and AI prompts can be fully customized in the **Settings** window. You can tailor the AI's instructions for each mode to fit your specific needs.
