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

---

## 2025-09-17 — Polyglot TTS stability + logging overhaul

Purpose: make mixed‑language (polyglot) reading robust end‑to‑end and add clear logs to track failures and successes.

What changed (high‑impact)
- Selection capture (Ctrl+R):
  - core/app_state.py::_read_smart_task now polls the clipboard for up to 0.5s after Ctrl+C, reducing “No text selected”.
  - Logs both the raw selection and the sanitized text:
    - [TTS] Raw selected_text: '…'
    - [TTS] Sanitized text: '…'
  - Strips log noise (INFO/DEBUG lines, G2P dumps, MToken tokens) so we don’t speak logs if the terminal is focused.
  - Falls back to the previous clipboard content if the new selection is empty/whitespace.

- TTS input (no more quote‑only extraction):
  - core/tts.py::speak_text now passes the full selection to TTS (removed the “only quoted text” behavior).

- Polyglot segmentation (kokoro_tts.py):
  - Segments by script runs (Latin incl. accents, Han/Chinese, Kana/Japanese, Devanagari/Hindi, Cyrillic), keeping sentences/phrases intact.
  - Punctuation is attached to the preceding run for natural prosody.
  - Latin language detection only on longer runs; short runs default to English (prevents misclassifying “to”, “in”, etc.).
  - Adjacent runs of the same language are merged.

- G2P robustness:
  - Try/except around G2P; chunks that fail are skipped with a warning, stream continues.
  - Filters out tokens with None phonemes; if all tokens are bad, the chunk is skipped.
  - Broader “is content” check (Latin + extended, Han, Kana, Devanagari, Cyrillic) so real text isn’t dropped as punctuation.

- Logging & observability:
  - New flag: SHOW_PHONEMES_IN_LOGS (kokoro_tts.py). When True, logs the phoneme string and token details for each chunk at INFO level.
  - Segmentation details moved to DEBUG to reduce noise at INFO. Chunk starts still logged at INFO:
    - Synthesizing chunk (Mandarin Chinese): '…'

How to track failures & successes
- Verify selection path:
  - Expect to see:
    - Reading from selected text: '…' (or Reading from clipboard: '…' fallback)
    - [TTS] Raw selected_text: '…'
    - [TTS] Sanitized text: '…'
  - If you get “No text selected”, check whether Raw is empty/whitespace or entirely sanitized away as logs.

- Verify polyglot flow:
  - Look for “Synthesizing chunk (LANG): '…'” for each segment.
  - Optional: set logging to DEBUG to see “Polyglot segmentation: …” boundaries.

- Verify G2P health:
  - Success: “Phoneme string: …” (if SHOW_PHONEMES_IN_LOGS=True).
  - Recoverable issues:
    - G2P failed for text: '…' (lang: …)
    - All tokens have None phonemes for text: '…' (lang: …)
    - Skipping punctuation/symbol-only chunk: '…'
  - These should not stop the stream; only that chunk is skipped.

- Quick manual test
  1) Highlight docs/test_text.md (lines 12–20).
  2) Press Ctrl+R.
  3) Expect English → Chinese → English → Japanese → Chinese → Japanese → Spanish … with correct switching.
  4) Observe “Synthesizing chunk (LANG)” logs and optional phonemes.

Known behaviors / workarounds
- If you press Ctrl+R while the terminal/status overlay is focused, the selection may be log text. Sanitization drops it; if nothing remains you’ll hear “No text selected.” Workaround: ensure the editor has focus and re‑select.
- A single isolated accented character (e.g., 'í' alone) may still fail in English G2P; in normal text this is avoided by Latin run grouping.

Operational switches
- Toggle phoneme logging: edit kokoro_tts.py and set SHOW_PHONEMES_IN_LOGS = True/False.
- Increase selection wait (if needed): in core/app_state.py::_read_smart_task, extend the 10 × 50ms polling loop.

Files touched
- core/app_state.py — selection polling, sanitization, logging.
- core/tts.py — full‑selection speak_text (no quote extraction).
- kokoro_tts/kokoro_tts.py — segmentation, G2P robustness, phoneme logging flag.

Success criteria
- Mixed‑language passages are spoken end‑to‑end without crashes.
- Logs clearly indicate selection source, chunk boundaries, and phoneme/G2P results (when enabled).
- Log text is not spoken.
