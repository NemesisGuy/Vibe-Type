# Known Fixed Bugs To Avoid

This document serves as a reference for subtle, hard-to-debug issues that have been fixed in the past. Review this before making major changes to the application's core architecture.

---

### 1. Silent Crash at Startup on Windows

- **Symptom:** The application crashes instantly upon startup with no Python traceback or error message. The process simply disappears.

- **Root Cause:** A low-level C-based conflict between the Windows COM library and the `tkinter` GUI event loop. The `pythoncom.CoInitialize()` function, when called with its default parameters, sets a threading model that is incompatible with `tkinter`. This was being called in `core/tts.py` to support the Windows SAPI TTS engine.

- **Solution:** The COM library must be initialized with a GUI-compatible, apartment-threaded model *before* the `tkinter` main loop is started. This is the only safe way to use these two libraries together.

  ```python
  # In core/tts.py
  import pythoncom
  
  # Correct Initialization (in pre_initialize_tts_services)
  pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
  ```

- **Lesson:** Any library that interacts with low-level Windows APIs (especially COM) must be treated with extreme caution in a GUI application. Always check for thread-safe initialization options.

---

### 2. Silent Crash When Using Hotkeys

- **Symptom:** The application runs but crashes silently as soon as a global hotkey is registered or triggered.

- **Root Cause:** The `keyboard` library, while powerful, is known to have low-level conflicts with other event-driven libraries like `tkinter` and `pystray`. It attempts to hook into the Windows event system in a way that can interfere with the main application's message loop, causing a silent crash.

- **Solution:** The `keyboard` library was replaced with `pynput`. The `pynput` library is more stable and is designed to work correctly in multi-threaded and multi-process applications. It provides a `GlobalHotkey` listener that runs in its own thread and communicates safely.

- **Lesson:** When implementing global system hooks (like hotkeys or mouse listeners), always choose a library that is explicitly designed for use in complex GUI applications and that manages its own thread of execution safely.

---

### 3. Hotkey Process Crashing After Library Change

- **Symptom:** The application would crash silently, and debugging revealed the `multiprocessing` hotkey listener process was terminating unexpectedly.

- **Root Cause:** When the hotkey library was switched from `keyboard` to `pynput`, a data conversion function (`_convert_hotkey_format`) was accidentally left in the main application code. The old library required hotkey strings like `ctrl+c`, while the new library requires `<ctrl>+c`. The conversion function was corrupting the hotkey data, causing the `pynput` library to crash in the background process.

- **Solution:** Remove the unnecessary data conversion function and ensure that the hotkey strings are passed to the `pynput` listener in the exact format it expects.

- **Lesson:** When replacing a core library, always audit the entire data pipeline that feeds it. Mismatched data formats between components are a common source of subtle and difficult-to-trace bugs.

---

### 4. Incorrect Phonemization for Non-English Kokoro TTS

- **Symptom:** Kokoro TTS would produce garbled or incorrect audio for languages other than English, even when using a voice for that language.

- **Root Cause:** The initial implementation used the built-in tokenizer from the `kokoro-onnx` library. This tokenizer is designed **only for English** and produces incorrect phonemes for all other languages. The `kokoro-onnx` library is only responsible for the final audio synthesis from phonemes, not the phoneme generation itself.

- **Solution:** The `misaki` library was integrated. `misaki` is the official, dedicated phonemizer for the Kokoro model and provides different grapheme-to-phoneme (G2P) pipelines for each supported language (English, Japanese, Spanish, etc.). The application was updated to use the correct `misaki` pipeline based on the language selected in the settings.

- **Lesson:** When working with multi-stage AI models, ensure you are using the correct, officially supported tool for each stage of the pipeline. Do not assume a single library handles all steps. For Kokoro, the process is: **Text -> `misaki` (Phonemizer) -> Phonemes -> `kokoro-onnx` (Synthesizer) -> Audio**.

---

### 5. Japanese TTS Failing with `RuntimeError: Failed initializing MeCab`

- **Symptom:** When attempting to use a Japanese voice, the application would crash with a `RuntimeError` indicating that `MeCab` could not be initialized. The error message would point to a missing `mecabrc` file.

- **Root Cause:** The `misaki` library's Japanese phonemizer (`ja.JAG2P`) has a dependency on the `fugashi` library, which in turn requires a MeCab dictionary to be installed and available. The required packages, `mecab-python3` and `unidic-lite`, were not included in the project's dependencies.

- **Solution:** The `mecab-python3` and `unidic-lite` packages were added to the `requirements.txt` file. This ensures that the necessary backend for Japanese text processing is installed with the other project dependencies.

- **Lesson:** When integrating a new library, especially one that supports multiple languages, it is crucial to check for any language-specific dependencies. The `misaki` library's documentation (and the error message itself) pointed to the need for MeCab, which was the key to resolving the issue. Always thoroughly investigate the requirements for each component of a library.

---

### 6. Chinese TTS Failing with `AttributeError`

- **Symptom:** When attempting to use a Chinese voice, the application would crash with an `AttributeError: module 'misaki.zh' has no attribute 'ZHHANSG2P'`.

- **Root Cause:** The wrong class name was used for the Chinese phonemizer. The correct class is `misaki.zh.ChineseG2P`.

- **Solution:** The `_get_g2p_pipeline` function in `kokoro_tts/kokoro_tts.py` was updated to use the correct class name. Additionally, the `jieba` dependency was added to `requirements.txt`.

- **Lesson:** Always double-check the class and function names provided by a library, especially when working with multiple languages that may have different naming conventions.

---

### 7. TTS Failing on Long Texts with `TypeError`

- **Symptom:** The application would successfully synthesize short phrases, but would crash with a `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` when given a long paragraph of text.

- **Root Cause:** The `misaki` phonemizer library was failing on long strings of text, returning `None` instead of a list of phonemes. This was happening because the library was not designed to handle long blocks of text without sentence-ending punctuation.

- **Solution:** The `synthesize_to_memory` function in `kokoro_tts/kokoro_tts.py` was updated to split the incoming text into sentences before passing them to the phonemizer. This ensures that the phonemizer is never overloaded with too much text at once.

- **Lesson:** When working with external libraries, always be mindful of their limitations. Even if a library works perfectly with short inputs, it may fail with longer ones. It is good practice to sanitize and chunk large inputs before passing them to an external library.

---

### 8.  TTS Speaking "No text selected" when reading from clipboard

- **Symptom:** When using the "Speak from Clipboard" hotkey, the TTS would say "No text selected" instead of reading the clipboard content.

- **Root Cause:** The hotkey was incorrectly mapped to the `read_selected_text` function, which is designed to be destructive (it clears the clipboard to capture selected text). This caused the clipboard to be cleared before it could be read.

- **Solution:** The hotkey was re-mapped to the `speak_from_clipboard` function, which is non-destructive and only reads the clipboard content.

- **Lesson:** Be careful when re-using functions that have side effects. A function designed for one specific purpose may not be suitable for another, even if it seems similar. Always ensure that the function you are calling has the expected behavior for the given context.

---

### 9. Piper TTS Failing with `AttributeError: 'PiperTTS' object has no attribute 'stream_seamlessly'`

- **Symptom:** When using the Piper TTS engine, the application would crash with an `AttributeError` indicating that the `stream_seamlessly` method does not exist.

- **Root Cause:** The `piper_tts.py` library was updated, and the `stream_seamlessly` method was either renamed or removed. The correct method to use is `stream`, which handles a single sentence at a time.

- **Solution:** The `test_piper_voice` and `_speak_piper` functions in `core/tts.py` were updated to loop through the sentences and call the `stream` method for each one.

- **Lesson:** When a library is updated, it is important to check for any API changes that may affect the application. In this case, the `stream_seamlessly` method was removed, and the code needed to be updated to use the new `stream` method.
