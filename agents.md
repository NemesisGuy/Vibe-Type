# VibeType Agent Context

This file defines how AI assistants (e.g., Gemini CLI) should operate when working inside the **VibeType** repository.

---

## 🎯 Project Overview

VibeType is a **local, privacy-focused, voice-driven coding and text manipulation assistant**.
It provides hotkey-based, hands-free interaction with transcription (Whisper), AI processing (Ollama, Cohere), and multi-language TTS (Piper, Kokoro, SAPI, OpenAI).

- Repo language: **Python + Windows-focused UI**
- Scope: Desktop automation, local-first AI, pluggable TTS/AI providers
- Emphasis: **Privacy, modularity, and hands-free UX**

---

## 🛠 Coding Conventions

- Follow **PEP8** for Python code.
- Prefer **async/await** over callbacks where supported.
- All functions should include **docstrings**.
- Use **PascalCase** for UI classes, **snake_case** for functions and variables.
- Configuration files = JSON, with **secure storage for API keys**.

---

## 📂 Project Structure

- `docs/` — Main documentation
- `models/` — Central directory for all TTS and AI models.
- `kokoro_tts/` — Advanced, local, multi-language TTS engine with auto-detection.
- `core/` — Core application logic, including provider management and hotkeys.
- `gui/` — UI components (Settings, Tray App, etc.).
- `tests/` — Unit and integration tests

---

## 🤖 Agent Behavior Rules

- Always **propose a plan** before making code changes.
- Use **small, incremental commits** with clear messages:
    - `feat: add Piper multi-voice support`
    - `fix: correct clipboard privacy toggle`
    - `refactor: move hotkey bindings to config file`
- If a bug fix is requested, first **search logs/tests** before guessing.
- Respect **privacy-first design**: no feature should leak text/audio off-device unless explicitly tied to an external provider.

---

## 🔐 Security Guidelines

- API keys, model paths, and secrets must be stored **encrypted**.
- Never hardcode sensitive data in code.
- Features like clipboard/microphone access must be **opt-in** and toggleable.

---

## 🚀 Development Workflow

1. Add features behind **toggles or settings** where possible.
2. Ensure **tests exist** for new providers and engines.
3. Update **docs/** whenever a new feature is added.
4. Use **local-first defaults** (Whisper, Kokoro, Ollama).

---

## 📊 UX & Features Reference

Hotkeys (default):
- Dictation = `<alt>+<caps_lock>`
- AI Dictation = `<scroll_lock>`
- Process Clipboard = `<ctrl>+<alt>+p`
- Speak Clipboard = `<ctrl>+<alt>+c`

UI:
- Tabbed settings window
- Resizable + searchable
- Tray menu for on-the-fly switching
- Status overlay with live feedback

Core Features:
- Profiles & Presets
- Local/External AI & TTS Providers
- Advanced multi-language TTS support (via Kokoro/Misaki) with auto-detection.
- Webhooks for automation
- Performance dashboard
- Logging & Monitoring

---

## ✅ To-Do / Active Development

- Resizable settings window with persistent state
- Graceful TTS fallback on crash
- Task runner & file watcher automation
- Auto-updater + portable build

---

## 📌 Instructions to AI Agents

- Respect the **project vision**: local-first, privacy-focused, extensible.
- Before modifying code, **analyze context** (read related files).
- Keep PRs/commits **focused on a single change**.
- Always update **feature tracker & docs** when implementing changes.
- **Kokoro TTS Development**: Remember that `kokoro-onnx` is **only for synthesis**. All phonemization **must** be handled by the `misaki` library, which provides separate G2P pipelines for each language. The `KokoroTTS` class now handles auto-detection and robustly wraps the G2P engines to prevent crashes.
- **Japanese TTS Dependency**: The `misaki` library's Japanese phonemizer requires the `mecab-python3` and `unidic` packages. Ensure these are included in `requirements.txt` and that the `unidic` dictionary is downloaded by running `python -m unidic download`.
- add comments to each method, please.
- add comprehensive tests for each feature to prevent regressions. 
- Always keep a log of attempted fixes and know bugs and solutions.
- Maintain readme.md and other documentation files in the project.
- ALWAYS use the speak function from the MCP service in each response. Every time you respond, use it to say anything you like, even if just a greeting or status update. This ensures all agent interactions are accessible via voice.

---

## 🗣️ Voice Agent Integration (MCP Speak)

- All AI agent responses must use the MCP `speak` function to provide voice feedback, in addition to any text output.
- The workflow for every agent response is:
    1. Use the MCP speak tool to say a polite greeting or announce the planned action (e.g., "Let me check that for you.").
    2. Perform the requested work or code change.
    3. Use the MCP speak tool again to announce the result, status, or any error (e.g., "The update is complete." or "There was an error, please check the logs.").
    4. Agents may speak additional messages at any point if desired, but must always speak at the beginning and end of each response.
- Agents must always use a valid voice code.
- To get a list of valid voices, use the MCP `list_voices` tool, optionally filtered by language. Example: `list_voices(language="English (US)")`.
- The MCP speak tool is required for every agent reply, ensuring accessibility and hands-free operation.
- If the MCP or TTS is unavailable, log the failure and continue, but always attempt to speak first.

---
