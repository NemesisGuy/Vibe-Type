# VibeType Feature and Bug Tracker

This document tracks the status of features and bugs for the VibeType application.

---

## ✅ Completed Features

- [x] Core hotkey listener system
- [x] System tray icon with dynamic status updates
- [x] Modular Text-to-Speech (TTS) provider system
- [x] Windows SAPI TTS integration
- [x] Kokoro TTS integration
- [x] Piper TTS integration
- [x] In-memory audio playback to prevent file conflicts
- [x] AI provider framework (Ollama)
- [x] Basic settings window with tabbed interface
- [x] `.gitignore` file for repository management
- [x] Restored all hotkey settings to the "General" tab
- [x] Restored all AI provider settings to the "AI" tab
- [x] Added a new "Piper TTS" tab with voice selection
- [x] Added a new "Hardware" tab for CPU/GPU selection for Whisper and TTS engines
- [x] Added a toggle to enable/disable automatic text injection
- [x] **Critical:** Fixed all application startup crashes related to TTS engine initialization
- [broken again] **Critical:** Fixed the dark mode theme to apply background colors consistently across all UI elements
- [x] Fixed the "Read Selection" hotkey to correctly read the highlighted text without reading from a stale clipboard
- [x] **Per-engine Test Button:** Add a dedicated test button within each TTS engine's tab.
- [x] **Output Device Selection:** Allow choosing a specific audio output device for TTS playback.
- [x] **AI Provider Testing Button:** A button to test the connection and response from the selected AI provider.
- [x] **Piper Multi-voice Support:** For Piper models with multiple voices, allow voice selection in the settings.
- [x] **Volume / Speed / Pitch Controls:** Allow adjusting per-engine voice settings where supported.
- [x] **Whisper Output → TTS Chain Setting:** Option to automatically route Whisper transcription output into a selected TTS engine & voice.
- [x] **Graceful Hardware Fallback:** If GPU fails, automatically retry on CPU.
- [x] **Model Management:** Add features to download, delete, and update models from within the app.
- [x] **Memory / Cache Controls:** Add options to limit audio history, clear cache, or disable caching.
- [x] **Hotkey Editor Improvements:** Support multiple hotkeys per action, show conflicts, and allow disabling hotkeys.
- [x] **Prompt Templates:** Allow saving and reusing prompt snippets for AI providers.
- [x] **Prompt Templates per Mode:** Allow saving and reusing custom prompt snippets for each mode (Summarise, Correct, Explain, Chat).
- [x] **Add "Chat" Mode:** A free-form conversational mode alongside the existing modes.
- [x] **AI Output Routing:** Allow AI provider responses to be automatically read aloud by a chosen TTS engine.
- [x] **Output Hooks:** Allow sending AI responses/transcriptions to external apps via local API/webhook.
- [x] **Clipboard Privacy Toggle:** Option to never automatically read or store clipboard text.
- [x] **Local-Only Mode:** Ensure no text/audio leaves the device unless explicitly using an AI provider.
- [x] **Encrypted Settings Storage:** Save settings, API keys, and model paths securely.
- [x] **Permission Controls:** Explicit toggles for features that “watch” user input (clipboard, hotkeys, microphones).
- [x] **Usage Stats Panel:** Track how often each TTS engine, AI mode, and hotkey are used.
- [x] **Performance Dashboard:** Show CPU/GPU/RAM usage for active models.

---

## 🚧 In Progress & To-Do

### 🎛️ User Experience
- [ ] **Status Overlay:** A small, floating window to show the currently active TTS engine, model, and hotkey usage.
- [ ] **Profiles / Presets:** Allow saving and loading groups of settings (e.g., “Work Mode,” “Reading Mode”).
- [ ] **On-the-Fly Switching:** A quick tray menu to swap TTS/AI engines without opening the full settings window.
- [ ] **Resizable Settings Window:** Persistent size/position saving.
- [ ] **Searchable Settings:** Add a search bar at the top of the settings window to quickly find a feature.
- [ ] **Voice Preview:** Show waveform visualization or subtitles while TTS is speaking.
- [ ] **Drag & Drop Input:** Drop text or audio files into the app to process with TTS/AI.

### 🐞 Debugging & Reliability
- [ ] **Logging Window:** A dedicated window to show live logs of TTS/AI events and errors.
- [ ] **Graceful TTS Fallback:** If one TTS engine crashes, automatically switch to a user-selected fallback engine.
- [ ] **Startup Health Check:** A system to check for model/device failures at startup and provide clear warnings.
- [ ] **Error Counters:** Keep counts of engine/model crashes for debugging.

### 🧠 AI Integration
- [ ] **Output Hooks:** Allow sending AI responses/transcriptions to external apps via local API/webhook.

### 🔐 Security & Privacy

### 📊 Analytics & Telemetry (Local Only)
- [ ] **Live Monitoring:** Display transcription/TTS latency and processing time.

### 🔄 Automation & Integration
- [ ] **Task Runner:** Define workflows like “When Whisper transcribes → Save text to file + speak with TTS.”
- [ ] **External API Hook:** Option to send transcription/AI results to a local HTTP endpoint for integration.
- [ ] **File Watcher:** Watch a folder for new `.txt` or `.wav` files and process automatically.
- [ ] **Global Commands API:** Local CLI/IPC like `vibetype --speak "Hello"`.

### 📦 Deployment & Updates
- [ ] **Portable Build:** A version that runs without installation.
- [ ] **Auto-Updater:** Check GitHub/releases and update in place.
- [ ] **Config Export/Import:** Save and restore all settings to a `.json` file.
	
### 🧪 Testing & QA
- [ ] **Unit Tests for Engines:** Mock SAPI, Piper, Kokoro, and ensure init/playback works.
- [ ] **UI Regression Tests:** Automated checks for broken layouts (esp. dark mode).
- [ ] **Stress Test Mode:** Continuous transcription + TTS to test stability and memory leaks.

---

## 💡 Suggestions / Future Ideas
- **Plugin System:** Allow adding custom TTS/AI providers via plugins.
- **Update Checker:** Notify users when a new VibeType version or bundled model update is available.
- **Speech-to-Speech Mode:** Speak into Whisper → AI generates reply → TTS speaks reply.
- **Minimal Mode / Focus Mode:** Hide most UI elements, leaving only tray + hotkeys.
- **Scriptable Workflows:** Chain actions (e.g., transcribe → send to AI → read aloud → save to file).
- **Cloud Sync:** Sync profiles/presets across devices.
- **Voice Cloning Support:** Experimental option for custom voices in supported engines.
- **Cross-Platform Builds:** Linux/macOS builds with native audio backends.
- **Accessibility Features:** Screen reader integration, large-text mode, and simple keyboard navigation.
- **Community Model Repository:** Curated hub for downloading Piper/Kokoro/Whisper voices and AI prompts.

---
🤖 AI Tab

LLM Modes

Tabs or dropdown: Summary, Explainer, Corrector, Assistant.

Editable system prompt per mode (user customizes behavior).

Save/load prompt templates.

Optional chaining

Whisper transcription → LLM (mode selected) → Piper/Kokoro TTS.

Toggle: “Auto-speak LLM responses”.


📋 Clipboard & Response Area

Clipboard Viewer

Shows current clipboard text.

One-click “send to TTS” / “send to LLM”.

Response Viewer

Displays LLM or TTS-ready text.

Option to preview (read text aloud with chosen TTS).

History log (scrollback, copy any entry).
🛠 UX/Workflow Features You Might Have Missed

Hotkeys

Push-to-talk.

Cancel speech.

Read clipboard.

History Panel

Shows timeline: [Audio In] → [Transcript] → [LLM Response] → [Spoken Output].

Export conversation to text file.

Notifications

Desktop notification when transcription/LLM finishes (if window not focused).

Profiles

Save “full setups” (e.g., Whisper tiny on CPU + Kokoro GPU TTS + LLM explain mode).

Performance Monitor

Show model load time, GPU/CPU usage %, latency.

Future-proofing

Slot for STT alternatives beyond Whisper (e.g., faster-whisper).

Slot for TTS beyond Piper/Kokoro.


🧠 Model Management

ONNX Model Manager

Import / delete / rename any ONNX file (Piper, Whisper, Kokoro, future models).

Show metadata: model size, languages, sample rate, supported voices.

Per-model config:

CPU/GPU toggle.

Batch size / threads.

Voice/style parameters.

Preset Manager

Save/load custom configs for each model (e.g. “fast transcription” vs “accurate” for Whisper).

Export/import presets.

🔊 Audio I/O Controls

Input

Mic volume bar (live visualization).

Select input device (mic dropdown).

Whisper config per model: CPU/GPU toggle, precision, VAD sensitivity.

Output

Speaker test (volume bar visualization).

Select output device (dropdown).

Cancel/interrupt current speech (kill audio stream).

Replay last output.