# Known Fixed Bugs To Avoid

This document serves as a reference for subtle, hard-to-debug issues that have been fixed in the past. Review this before making major changes to the application's core architecture.

---

### 1. Catastrophic G2P Failures in Kokoro TTS for English

- **Symptom:** A series of cascading, difficult-to-diagnose errors when synthesizing English text with Kokoro TTS, including:
    1.  `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` originating deep inside the `misaki` library.
    2.  `AttributeError: 'str' object has no attribute 'phonemes'` when trying to process the G2P result.
    3.  `WARNING: G2P produced empty output for text: ...`

- **Root Cause:** This was a complex issue with multiple layers of failure:
    1.  **Internal Library Bug:** The version of the `misaki` library used has an internal bug in its English G2P (`en.G2P`) that causes it to fail on certain valid inputs, leading to the `NoneType` error.
    2.  **Incorrect API Assumptions:** Multiple incorrect assumptions were made about the `misaki` API during attempts to fix the initial bug. The `en.G2P` engine, when it works, returns a single `str`, not a list of token objects. Attempts to treat it like a list of objects caused the `AttributeError`.
    3.  **Faulty Workarounds:** Attempts to bypass the internal bug by using other `misaki` methods (like `.tokenize()` and the non-existent `.phonemize()`) were based on incorrect understandings of the library's API and led to further errors or empty output.

- **Solution:** The final, robust solution was to radically simplify the approach. The `_synthesize_chunk` method now does the following:
    1.  It calls the `g2p_engine(text)` directly, as it is the intended use.
    2.  This entire call is wrapped in a broad `try...except Exception` block.
    3.  If the `g2p_engine` fails for **any reason** (including the internal `NoneType` bug), the exception is caught, logged, and the synthesis for that chunk is safely aborted by returning `None`.

- **Lesson:** When a third-party library exhibits buggy or unpredictable behavior internally, do not try to replicate or work around its internal logic. The most stable and robust solution is to **isolate the faulty call** and **wrap it in a protective exception handler**. Accept that it will sometimes fail and ensure that failure does not crash the entire application.

---

### 2. Incorrect Phonemization for Non-English Kokoro TTS

- **Symptom:** Kokoro TTS would produce garbled or incorrect audio for languages other than English.

- **Root Cause:** The initial implementation used a tokenizer designed **only for English**. The `kokoro-onnx` library is only responsible for the final audio synthesis from phonemes, not the phoneme generation itself.

- **Solution:** The `misaki` library was integrated, which provides different grapheme-to-phoneme (G2P) pipelines for each supported language. The application now uses the correct `misaki` pipeline based on the detected or selected language.

- **Lesson:** When working with multi-stage AI models, ensure you are using the correct, officially supported tool for each stage of the pipeline. For Kokoro, the process is: **Text -> `misaki` (Phonemizer) -> Phonemes -> `kokoro-onnx` (Synthesizer) -> Audio**.

---

### 3. Japanese TTS Failing with `RuntimeError: Failed initializing MeCab`

- **Symptom:** When attempting to use a Japanese voice, the application would crash with a `RuntimeError` indicating that `MeCab` could not be initialized.

- **Root Cause:** The `misaki` library's Japanese phonemizer (`ja.JAG2P`) requires a MeCab dictionary. The required `unidic` package was not being installed and downloaded correctly.

- **Solution:** The `unidic` package was added to `requirements.txt`. The documentation now instructs the user to run `python -m unidic download` to ensure the dictionary is present.

- **Lesson:** When integrating a new library, especially one that supports multiple languages, it is crucial to check for any language-specific dependencies.

---

### 4. Silent Crash at Startup on Windows

- **Symptom:** The application crashes instantly upon startup with no Python traceback or error message.

- **Root Cause:** A low-level C-based conflict between the Windows COM library (used for SAPI TTS) and the `tkinter` GUI event loop.

- **Solution:** The COM library must be initialized with a GUI-compatible, apartment-threaded model (`pythoncom.COINIT_APARTMENTTHREADED`) *before* the `tkinter` main loop is started.

- **Lesson:** Any library that interacts with low-level Windows APIs (especially COM) must be treated with extreme caution in a GUI application. Always check for thread-safe initialization options.

---

### 5. Intermittent 'No text selected' Bug in Clipboard/Selection

- **Symptom:** Sometimes, when using the 'Read Selected Text' hotkey (Ctrl+R), the system would say "No text selected" even though text was highlighted.
- **Root Cause:** The clipboard update after Ctrl+C was not always immediate, especially in some editors or with large selections. The system would read the clipboard too soon and get an empty or stale value.
- **Solution:** The selection logic now polls the clipboard for up to 0.5 seconds, logging both the raw and sanitized selection. If the selection is empty or whitespace, it falls back to the previous clipboard content. This greatly reduces false negatives.
- **Lesson:** Always allow for asynchronous clipboard updates and log both the raw and processed values for debugging.

---

### 6. Overlapping Audio in Batch Speech

- **Symptom:** When using the `speak_batch` tool or the `/speak_batch` endpoint, multiple audio segments would play simultaneously instead of sequentially.
- **Root Cause:** The `/speak_batch` endpoint was being called with parallel requests, and the underlying TTS worker thread (`_tts_worker` in `core/tts.py`) processed items from the `tts_queue` without a mechanism to ensure one speech task finished before the next one started.
- **Solution:** A `threading.Lock` (`tts_playback_lock`) was introduced in `core/tts.py`. The `_tts_worker` now acquires this lock before processing a text from the queue and releases it only after the audio playback is complete. This enforces sequential, one-at-a-time processing of all TTS tasks, including those from the `/speak_batch` endpoint.
- **Lesson:** When a worker thread consumes from a queue to perform I/O-bound tasks that must not overlap (like audio playback), use a lock to serialize the execution of the task itself.

---

### 7. Faulty Phoneme Generation Endpoint

- **Symptom:** The `mcp_vibetts_mcp_phonemes` tool or direct calls to the `/phonemes` endpoint would fail, return incorrect data, or cause server errors.
- **Root Cause:** The endpoint handler in `MCP/vibetts_mcp_server.py` contained unstable, experimental code (including module reloading) and was not correctly wired to the robust, multi-language phonemizer (`KokoroTTS.phonemize_text`) available in `core/tts.py`.
- **Solution:** The `/phonemes` endpoint handler was rewritten to directly call `core.tts.kokoro_tts_instance.phonemize_text()`. This ensures that all phoneme generation requests are processed by the correct, stable, and fully-featured implementation that leverages the `misaki` library for accurate G2P conversion across all supported languages. The unstable reloading code was removed.
- **Lesson:** Ensure that high-level tool wrappers and API endpoints correctly delegate to the core application logic where the stable, tested implementation resides. Avoid duplicating or creating partial, experimental implementations at the API layer.

---

### Debugging Tools

- **Phoneme Logging:**
  - You can now enable detailed phoneme logging for each TTS chunk (see kokoro_tts.py: SHOW_PHONEMES_IN_LOGS). This is invaluable for diagnosing G2P issues and understanding how text is being processed.

---

## Feature Suggestions

- **Automated Bug Reporting:** Add a feature to export logs and recent errors directly from the GUI for easier troubleshooting.
- **Log Export for TTS/Selection:** Allow users to save the raw/sanitized selection and phoneme logs for any session.
