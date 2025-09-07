# VibeType Feature Tracking

This document tracks the status of features and ongoing development. For information on past bugs and their solutions, please see `know_fixed_bugs_to_avoid.md`.

---

## ✅ Completed Features

- **Responsive Speech System:**
  - Implemented a TTS queuing system to handle speech requests asynchronously, preventing UI freezes.
  - Added a smart chunking mechanism to prioritize the first sentence for immediate playback, improving time-to-first-speech.
  - Introduced a dedicated hotkey (`Ctrl+Alt+I`) to interrupt any ongoing or queued speech.
  - Refactored TTS providers (Kokoro TTS, Piper TTS) to properly handle the interrupt signal.

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

- **Kokoro TTS Multi-Language Support & Streaming:**
  - Integrated the `misaki` library for advanced, multi-language phonemization, with a fallback to the built-in `kokoro-onnx` tokenizer for stability.
  - Implemented seamless, chunked streaming for Kokoro TTS to provide a more responsive experience.
  - Added a language selection dropdown in the settings UI for Kokoro TTS.
  - The voice selection dropdown is now intelligently filtered based on the chosen language.
  - Supported languages include English (US/UK), Japanese, Spanish, French, Hindi, Italian, Portuguese, and Mandarin Chinese.
  - **Dependency Note:** Japanese and Chinese language support now correctly includes the `mecab-python3`, `unidic-lite`, and `jieba` packages in `requirements.txt`.

- **Fixed AI and Transcription Modules:**
  - Restored the `get_ai_response` function in the AI module.
  - Corrected the logic for locating the `ggml-base.bin` transcription model.
  - Added a test file for the AI module to ensure its functionality.

- **Fixed GPU Execution for Local TTS:**
  - **Piper TTS:** Corrected a bug in `core/tts.py` that was preventing the `piper_execution_provider` setting from being read, ensuring the engine now uses the selected hardware.
  - **Kokoro TTS:** Fixed a crash on startup by correcting a faulty logging statement. The engine now correctly initializes with the selected hardware provider (CPU or CUDA). The underlying `kokoro-onnx` library\'s session is now properly overridden to respect the user\'s hardware choice.

- **Improved Hotkey Functionality:**
  - The "Read Selected Text" and "Speak from Clipboard" hotkeys now have distinct, reliable functions.

---

## 📝 To-Do

- **Kitten TTS Integration:** Integrate the Kitten TTS engine as a new pluggable TTS provider.
- **Resizable Settings Window:** Implement persistent state for the settings window size and position.
- **Comprehensive Tests:** Create a comprehensive test suite that covers all major features and providers.
- **Graceful TTS Fallback:** If a selected TTS engine fails to initialize or speak, the application should gracefully fall back to a default provider (e.g., Windows SAPI).
