# VibeType MVP Specification

## Overview
VibeType is a privacy-first, offline-capable voice assistant designed for seamless voice-to-text transcription and optional AI-powered text processing. It prioritizes local processing, minimal resource usage, and user control via a system tray GUI. The application is packaged as a single executable, initially targeting Windows, with planned support for Mac and Linux.

### Core Objectives
- **Privacy-First**: Fully offline speech-to-text (STT) and text-to-speech (TTS) with optional local AI processing.
- **User-Friendly**: Simple system tray interface with hotkey and optional wake word activation.
- **Lightweight**: Optimized for CPU usage, no internet required for core functionality.
- **Customizable**: Configurable settings for models, hotkeys, and AI behavior.

## Core Features

### Speech-to-Text (STT)
- Utilizes **Whisper.cpp** for offline transcription.
- Supports **tiny**, **base**, and **medium** models for varying accuracy and performance.
- Fully CPU-optimized, no internet required.

### Text-to-Speech (TTS)
- Implements **Piper TTS** for natural, offline speech playback.
- Toggleable playback for user flexibility.

### AI Layer (Optional)
- Integrates **Ollama** local LLM for advanced text processing (e.g., summarization, rewriting, command execution).
- Configurable API endpoint and system prompt for customization.

### Activation
- **Hotkey**: Default `Ctrl+Alt+Space` to start/stop recording.
- **Wake Word**: Optional hands-free activation with customizable wake word detection.

### Output
- Injects transcribed or AI-processed text into the active application window.
- Optional clipboard copy for transcribed text.

## GUI Features
- **System Tray Icon**:
    - Displays status: Idle, Listening, Transcribing, Speaking.
    - Provides Start/Stop dictation controls.
- **Settings Window**:
    - Configure hotkey and wake word.
    - Select Whisper model (tiny/base/medium).
    - Enable/disable Piper TTS playback.
    - Set Ollama API URL and key.
    - Adjust silence timeout and log level.
    - Test buttons for microphone input and TTS playback.
- **History Viewer**: Displays transcription and AI output history.
- **Planned Features**:
    - Dark mode UI.
    - Multi-language support.

## Architecture
```plaintext
User Hotkey / Wake Word
        ↓
    Audio Capture
        ↓
    Whisper.cpp STT
        ↓
 AI Processing (optional Ollama LLM)
        ↓
    Text Injection
        ↓
  Piper TTS (optional playback)
        ↓
 User hears speech
```

## Project Structure
```plaintext
VibeType/
├── vibe_type.py              # Main entrypoint
├── core/
│   ├── __init__.py
│   ├── audio_capture.py      # Audio recording logic
│   ├── hotkey_handler.py     # Hotkey and wake word detection
│   ├── whisper_transcriber.py # Whisper.cpp integration
│   ├── piper_tts.py          # Piper TTS integration
│   ├── ollama_ai.py          # Ollama LLM integration
│   └── text_injector.py      # Text injection into active window
├── gui/
│   ├── __init__.py
│   ├── tray_app.py           # System tray icon and menu
│   └── settings_window.py    # Settings GUI
├── config/
│   └── config.json           # User configuration data
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

## Tech Stack
- **Python 3.11+**: Core programming language.
- **Whisper.cpp**: Bundled binaries and models for STT.
- **Piper TTS**: Local CPU-based neural TTS.
- **Ollama API**: Local AI model integration.
- **PySimpleGUI (or PyQt)**: System tray and settings GUI.
- **sounddevice**: Audio capture.
- **keyboard/pyautogui**: Hotkey detection and text injection.
- **requests**: API communication for Ollama.
- **PyInstaller**: Packaging as a single executable.

## Estimated Lines of Code (LOC)
| Module                     | Estimated LOC |
|----------------------------|--------------|
| Tray Icon + GUI            | 180          |
| Hotkey & Wake Word         | 70           |
| Audio Capture              | 80           |
| Whisper Integration        | 110          |
| Ollama AI Integration      | 70           |
| Piper TTS Integration      | 90           |
| Text Injection             | 50           |
| Config & Logging           | 50           |
| **Total**                  | **~700**     |

## Additional Features to Consider
- Auto-start on system login.
- Silence detection for auto-stopping recording.
- Transcription and AI output history log in GUI.
- Clipboard copy option for output.
- Global mute / Do Not Disturb mode.
- Customizable Ollama system prompts.
- Config export/import functionality.
- Dark mode UI.
- Multi-language UI support.
- Quick hotkey for repeating last output.

## Development Roadmap
1. **Setup**:
    - Create project folder structure and `requirements.txt`.
    - Initialize `vibe_type.py` as the entrypoint stub.
2. **Core Development**:
    - Build core module stubs (`audio_capture.py`, `hotkey_handler.py`, etc.) with TODOs.
    - Develop tray app skeleton (`tray_app.py`) with basic menu and status display.
    - Implement hotkey listener and connect to audio capture.
3. **Integration**:
    - Integrate Whisper.cpp for transcription (start with dummy data).
    - Add Piper TTS playback with GUI test controls.
    - Implement Ollama API calls with toggle control.
    - Enable text injection to active window.
4. **Refinement**:
    - Expand settings window and user config management.
    - Package app with PyInstaller for Windows `.exe`.
5. **Future Plans**:
    - Plan Mac/Linux support.
    - Implement advanced features (dark mode, multi-language support, etc.).

## Next Steps
- Set up the project repository and install dependencies.
- Develop the tray app skeleton and hotkey listener.
- Integrate Whisper.cpp and test with a minimal audio input.
- Iterate on GUI and core functionality based on testing feedback.