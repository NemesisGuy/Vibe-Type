VibeType MVP Specification
Overview
VibeType is a privacy-first, offline-capable voice assistant focused on:

Speech-to-Text using local Whisper.cpp models

Text-to-Speech via Piper (CPU-friendly neural TTS)

Optional AI processing with Ollama local LLM

A system tray GUI for control, settings, and testing

Hotkey and optional wake word activation

Text injection into focused apps

Packaged as a single executable (initially Windows)

Core Features
Speech-to-Text (STT)

Offline Whisper.cpp transcription (tiny/base/medium models)

CPU optimized, no internet required

Text-to-Speech (TTS)

Piper TTS for natural speech playback

Toggle playback option

AI Layer (Optional)

Ollama LLM for text processing (summarization, rewriting, commands)

Configurable API endpoint and system prompt

Activation

Hotkey (default Ctrl+Alt+Space) to start/stop recording

Optional wake word detection for hands-free control

Output

Injects transcribed or AI-processed text into active window

Optionally copies text to clipboard

GUI Features
System tray icon with status display (Idle, Listening, Transcribing, Speaking)

Start/Stop dictation controls

Settings window to configure:

Hotkey and wake word

Whisper model selection

Enable/disable Piper TTS playback

Ollama API URL and key

Silence timeout and log level

Test buttons for microphone input and TTS playback

Transcription and AI output history viewer

Dark mode (planned)

Multi-language support (planned)

Architecture
vbnet
Copy
Edit
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
Project Structure
arduino
Copy
Edit
VibeType/
├── vibe_type.py               # Main entrypoint
├── core/
│   ├── __init__.py
│   ├── audio_capture.py
│   ├── hotkey_handler.py
│   ├── whisper_transcriber.py
│   ├── piper_tts.py
│   ├── ollama_ai.py
│   └── text_injector.py
├── gui/
│   ├── __init__.py
│   ├── tray_app.py
│   └── settings_window.py
├── config/
│   └── config.json            # User config data
├── requirements.txt
└── README.md
Tech Stack
Python 3.11+

Whisper.cpp (bundled binaries and models)

Piper TTS (local CPU neural TTS)

Ollama API for local AI integration

PySimpleGUI (or PyQt) for tray GUI and settings

sounddevice for audio capture

keyboard and pyautogui for hotkeys and text injection

requests for API communication

PyInstaller for packaging as single executable

Estimated Lines of Code
Module	LOC
Tray Icon + GUI	~180
Hotkey & Wake Word	~70
Audio Capture	~80
Whisper Integration	~110
Ollama AI Integration	~70
Piper TTS Integration	~90
Text Injection	~50
Config & Logging	~50
Total	~700 LOC

Additional Features to Consider
Auto-start on system login

Silence detection to auto-stop recording

Transcription and AI output history log in GUI

Clipboard copy option

Global mute / Do Not Disturb mode

Customizable Ollama system prompts

Config export/import

Dark mode UI

Multi-language UI support

Quick hotkey for repeating last output

Development Roadmap & Next Steps
Setup project folder structure and requirements.txt

Create minimal vibe_type.py as entrypoint stub

Build core module stubs (audio_capture.py, hotkey_handler.py, etc.) with TODOs

Develop tray app skeleton (tray_app.py) with basic menu and status display

Implement hotkey listener and connect to audio capture stubs

Integrate Whisper.cpp for transcription (start with dummy data)

Add Piper TTS playback and test GUI controls

Integrate Ollama API calls with toggle control

Implement text injection to active window

Expand settings window and user config management

Package app with PyInstaller for Windows .exe

Plan Mac/Linux support and advanced features

Ready to build out VibeType? 🚀