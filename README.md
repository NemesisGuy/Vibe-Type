# VibeType

VibeType is a voice-driven coding and text manipulation assistant designed for seamless integration into your workflow. It uses local, privacy-focused tools for transcription (Whisper) and AI processing (Ollama) to turn your voice into code, commands, and corrected text.

## Core Philosophy

The goal of VibeType is to provide a powerful, hands-free interface for interacting with your computer, with a strong emphasis on:

*   **Local First:** Whenever possible, processing happens locally on your machine. Your voice and data never leave your computer unless you explicitly configure an external API.
*   **Flexibility:** A powerful "AI Toolkit" allows you to switch between different AI-powered tasks on the fly.
*   **Pluggable Providers:** VibeType is designed to be extensible. You can choose between different AI and Text-to-Speech (TTS) providers to suit your needs, whether you prefer local models for privacy or powerful external APIs for quality.
*   **Customization:** Hotkeys, AI models, and system prompts are all fully customizable to fit your workflow.

## Key Features

VibeType is more than just a dictation tool. It's a suite of voice-powered utilities. For a full list of features and their hotkeys, please see the [**Features Document**](./docs/FEATURES.md).

*   **Standard Dictation:** Quickly transcribe your speech into any text field.
*   **Multi-Provider AI Processing:** Use a local LLM (via Ollama) or a powerful external API (like Cohere) to process your speech for tasks like code generation, rephrasing, or command execution.
*   **Clipboard Processing:** Apply AI transformations (like summarization or correction) to any text on your clipboard using your selected AI provider.
*   **Advanced Multi-Language TTS:** Get audible feedback using the built-in Windows voice, an external API (like OpenAI), or the powerful, local **Kokoro TTS** engine. Kokoro TTS features:
    *   **Automatic Language Detection:** Speak in multiple languages and have the TTS engine automatically switch voices.
    *   **Wide Language Support:** High-quality voices for English, Japanese, Spanish, French, Chinese, and more.
    *   **Voice Blending:** Create unique, custom voices by blending existing ones.
*   **Customizable AI Modes:** Switch between different AI "personalities" (like Assistant, Corrector, or Summarizer) instantly.

## Getting Started

1.  Ensure you have a local [Ollama](https://ollama.com/) server running if you wish to use it.
2.  Install the required Python dependencies from `requirements.txt`.
3.  Run `python VibeType.py`.
4.  Configure your hotkeys, AI provider, and TTS provider from the Settings window.

## Troubleshooting

### Multi-Language TTS Issues

Kokoro TTS relies on a few external dependencies for its powerful multi-language capabilities. If you encounter issues with certain languages, please check the following:

*   **Japanese or Chinese:** If you encounter an error in the logs related to `MeCab`, `fugashi`, or a `RuntimeError` mentioning `unidic` or `mecabrc not found`, the required dictionary was not installed correctly. To fix this, run the following command in your terminal:

    ```sh
    python -m unidic download
    ```

*   **Other Languages (French, Spanish, etc.):** Many other languages are supported via `espeak-ng`. If you have issues with these languages, ensure you have `espeak-ng` installed and accessible in your system's PATH.
