# VibeType Feature Tracking

This document tracks the status of features and ongoing development. For information on past bugs and their solutions, please see `know_fixed_bugs_to_avoid.md`.

---

## ✅ Completed Features

- **Web API for System Integration:**
  - Implemented a Flask-based web server in `api/api.py` to expose core functionalities.
  - Added initial endpoints for Kokoro TTS, allowing programmatic access to:
    - `/api/tts/kokoro/languages` (List supported languages)
    - `/api/tts/kokoro/voices` (List available voices, filter by language)
    - `/api/tts/kokoro/synthesize` (Generate speech and receive WAV audio)
  - Created `docs/API.md` to provide detailed documentation for all new endpoints.

- **Advanced Multi-Language TTS & Auto-Detection:**
  - The **Kokoro TTS** engine now features robust, automatic language detection, allowing for seamless synthesis of mixed-language text (e.g., English and Japanese).
  - The underlying G2P (grapheme-to-phoneme) process has been completely rewritten to be stable and resilient, eliminating a wide range of crashes related to the `misaki` library.
  - The voice selection dropdown in the settings is now intelligently filtered based on the selected language.
  - Supported languages include English (US/UK), Japanese, Spanish, French, Hindi, Italian, Portuguese, and Mandarin Chinese.
  - **Dependency Note:** Japanese language support now correctly requires the full `unidic` dictionary. It can be installed via `pip install unidic` and then downloaded by running `python -m unidic download`.

- **Responsive Speech System:**
  - Implemented a TTS queuing system to handle speech requests asynchronously, preventing UI freezes.
  - Added a smart chunking mechanism to prioritize the first sentence for immediate playback, improving time-to-first-speech.
  - Introduced a dedicated hotkey (`Ctrl+Alt+I`) to interrupt any ongoing or queued speech.
  - Refactored TTS providers to properly handle the interrupt signal.

- **Ollama Model Management & New Hotkeys:**
  - Added a "Refresh Models" button to the AI settings to fetch and display a list of available Ollama models.
  - Replaced the free-text model input with a dropdown for easier model selection.
  - Introduced new default hotkeys:
    - `Ctrl+Alt+Z` for summarizing selected text.
    - `Ctrl+Alt+X` for correcting selected text.
  - Updated documentation to reflect the new hotkeys and model management features.

- **Dedicated Prompts Settings Page:**
  - Implemented a dedicated settings page for creating, editing, and saving custom prompts for different operational modes.
  - Ensured that user updates to prompts are saved and correctly applied when the associated hotkey is used.
  - Fixed issues with system prompts for Ollama, ensuring they are correctly passed to the LLM during execution.

- **Fixed GPU Execution for Local TTS:**
  - **Piper TTS:** Corrected a bug that prevented the `piper_execution_provider` setting from being used, ensuring the engine now runs on the selected hardware.
  - **Kokoro TTS:** Resolved a startup crash and ensured the engine correctly initializes with the user-selected hardware provider (CPU or CUDA).

- **Improved Hotkey Functionality:**
  - The "Read Selected Text" and "Speak from Clipboard" hotkeys now have distinct, reliable functions.

---

## 📝 To-Do

- **Kitten TTS Integration:** Integrate the Kitten TTS engine as a new pluggable TTS provider.
- **Resizable Settings Window:** Implement persistent state for the settings window size and position.
- **Comprehensive Tests:** Create a comprehensive test suite that covers all major features and providers.
- **Graceful TTS Fallback:** If a selected TTS engine fails to initialize or speak, the application should gracefully fall back to a default provider (e.g., Windows SAPI).
