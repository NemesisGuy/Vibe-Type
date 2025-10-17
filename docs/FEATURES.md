# VibeType Features

This document provides a detailed overview of every feature available in VibeType, including the default hotkeys and how to use them.

## Core Hotkeys

VibeType is controlled by a set of global hotkeys that work in any application.

*   **Toggle Dictation (`<alt>+<caps_lock>`):** Starts or stops standard speech-to-text.
*   **AI Dictation (`<scroll_lock>`):** Transcribes your speech, then processes it with your selected AI Provider using the active AI prompt.
*   **Process Clipboard (`<ctrl>+<alt>+p`):** Takes text from your clipboard and processes it with your selected AI Provider.
*   **Speak from Clipboard (`<ctrl>+<alt>+c`):** Reads the text on your clipboard aloud using your selected TTS Provider.
*   **Explain Text (`<alt>+<ctrl>+e`):** A dedicated hotkey to process the selected text with an "Explain" AI prompt.
*   **Summarize Text (`<ctrl>+<alt>+z`):** A dedicated hotkey to process the selected text with a "Summarize" AI prompt.
*   **Correct Text (`<ctrl>+<alt>+x`):** A dedicated hotkey to process the selected text with a "Correct" AI prompt.
*   **Read Text (`<alt>+<ctrl>+s`):** Reads the selected text aloud using your selected TTS Provider. If no text is selected, it will read the content of the clipboard.
*   **Voice Conversation (`<alt>+<ctrl>+t`):** Starts a continuous voice conversation with the AI.
*   **Interrupt Speech (`<ctrl>+<alt>+i`):** Immediately stops any ongoing or queued speech.

## Responsive Speech System

To provide a more fluid and responsive experience, VibeType's Text-to-Speech (TTS) system includes the following features:

*   **Speech Queuing:** All speech requests are handled in a queue, so you can fire off multiple commands without waiting for the first one to finish.
*   **Smart Chunking:** For longer passages of text, VibeType will speak the first sentence immediately to give you a fast response, then continue with the rest of the text.
*   **Interruption:** You can stop speech at any time using the dedicated hotkey, giving you full control over the audio output.

## Pluggable Providers

VibeType's power comes from its flexibility. You can choose which backend services you want to use for both AI processing and voice output. You can configure these in the **Settings** window.

### AI (LLM) Providers

Choose the language model that best fits your needs for tasks like code generation, correction, and summarization.

*   **Ollama (Local First):**
    *   **Type:** Local
    *   **Default:** Enabled
    *   **Description:** Runs entirely on your own machine for maximum privacy. Requires a running Ollama instance.
    *   **Configuration:** Set the API URL (e.g., `http://localhost:11434`). You can then click the "Refresh" button to populate a dropdown menu with all of your downloaded Ollama models, allowing you to easily select the one you want to use.

*   **Cohere:**
    *   **Type:** External API
    *   **Default:** Disabled
    *   **Description:** A powerful, cloud-based provider. Offers excellent performance for a wide range of tasks.
    *   **Configuration:** Requires a Cohere API Key.

### Text-to-Speech (TTS) Providers

Choose the voice you want to hear for audio feedback. All local models should be placed in the `/models` directory at the root of the project.

*   **Windows SAPI (Local First):**
    *   **Type:** Local
    *   **Default:** Enabled
    *   **Description:** Uses the voices built into the Windows operating system. Fast, reliable, and requires no internet connection.
    *   **Configuration:** Select from a list of available voices on your system and adjust the speech rate.

*   **OpenAI:**
    *   **Type:** External API
    *   **Default:** Disabled
    *   **Description:** Provides high-quality, natural-sounding voices via the OpenAI API.
    *   **Configuration:** Requires an OpenAI API Key.

*   **Kokoro TTS (Local):**
    *   **Type:** Advanced Local
    *   **Default:** Disabled
    *   **Description:** A high-quality, local TTS engine with robust multi-language capabilities. Requires model files to be placed in the `/models/kokoro` directory.
    *   **Configuration:** 
        *   Select the desired ONNX model file.
        *   Choose your language. Select **"Auto-Detect"** to have the engine automatically determine the language of the input text (e.g., English, Japanese, Chinese).
        *   Select a primary voice. The voice dropdown is automatically filtered based on the selected language.
    *   **Features:**
        *   **Seamless Streaming:** Supports chunked streaming for a highly responsive experience.
        *   **Voice Blending:** Create unique, custom voices by mixing the characteristics of existing ones.
        *   **Wide Language Support:** Includes high-quality voices for English, Japanese, Spanish, French, Mandarin Chinese, and more.
        *   **Examples:**
            *   English: "Hello, how are you?" (Voice: Alex)
            *   Japanese: "こんにちは、お元気ですか？" (Voice: Sakura)
            *   Spanish: "Hola, ¿cómo estás?" (Voice: Carlos)
            *   French: "Bonjour, comment ça va?" (Voice: Claire)
            *   Mandarin Chinese: "你好，你怎么样？" (Voice: Ming)

*   **Piper TTS (Local):**
    *   **Type:** Custom Local
    *   **Default:** Disabled
    *   **Description:** A fast, efficient, and high-quality local TTS engine. Models are managed via the **Models** tab in the settings.
    *   **Configuration:** 
        *   Select the desired model file and voice from the settings window.
        *   **Hardware Acceleration:** You can select the execution provider (e.g., `CPU`, `CUDA`, `Tensorrt`) for Piper in the **Hardware** tab to leverage GPU acceleration for faster voice synthesis.

*   **ZipVoice TTS (Local Voice Cloning):**
  *   **Type:** Local (PyTorch GPU with optional ONNX Runtime)
  *   **Default:** Disabled
  *   **Description:** Streams high-quality cloned voices from short voice prompts. Runs on the native PyTorch checkpoint by default and uses CUDA when available, with optional ONNX Runtime support for environments that prefer exported models.
  *   **Configuration:**
    *   Open the **🧬 ZipVoice TTS** tab in settings, select a bundled prompt sample, or add your own audio/text pair under `zipvoice_tts/samples`.
    *   Pick the backend (`onnx` for ONNX Runtime or `torch` for native PyTorch checkpoints) and model variant (`zipvoice` or `zipvoice_distill`).
    *   Adjust the playback speed slider to fine-tune pacing and use the built-in test button to preview the cloned voice.

*   **Kitten TTS (Coming Soon):**
    *   **Type:** Custom Local
    *   **Description:** An upcoming, high-performance TTS engine.

## Model Management (Piper TTS)

The **Models** tab in the settings window provides a simple interface for managing your local Piper TTS models.

*   **Find More Models:** Opens a web browser to the official Piper models page on Hugging Face, where you can download new voices.
*   **Import Model(s):** Opens a file dialog to import downloaded models. Simply select the `.onnx` file for the model you wish to import, and VibeType will automatically copy both the model and its corresponding `.json` configuration file into your library.
*   **Delete Selected:** Removes the selected model from your library.
*   **Refresh List:** The model list automatically refreshes after any import or deletion.

## The AI Toolkit: Prompt Templates

Select an active prompt to change the AI's "personality" and tell it what kind of task to perform. The active prompt is used by the **AI Dictation** and **Process Clipboard** hotkeys.

*   **Assistant:** A general-purpose conversational AI for answering questions or generating text.
*   **Corrector:** Fixes grammar and spelling mistakes without changing the meaning. Ideal for cleaning up dictation.
*   **Summarizer:** Condenses long text into key points. Perfect for summarizing articles from your clipboard.
*   **Chat:** A more free-form conversational AI for natural, back-and-forth interaction.

## Customization and Prompts

All hotkeys, provider settings (API keys, URLs, models), and AI prompts can be fully customized in the **Settings** window. VibeType now features a dedicated **Prompts** settings page, allowing you to create, edit, and save unique prompts for each operational mode.

When a hotkey is used, the associated prompt is passed to the Ollama LLM, ensuring that your custom instructions are applied correctly. This allows you to tailor the AI's behavior to your specific needs, whether you're correcting dictation, summarizing text, or engaging in a voice conversation.

## Recent Improvements (2025-09-17)

- **Polyglot TTS Robustness:**
  - Seamless reading of mixed-language passages (English, Chinese, Japanese, Spanish, etc.) with automatic language detection and correct voice switching.
  - Improved segmentation: Latin (including accented) runs are kept together, punctuation is attached to the previous segment, and short runs default to English.
  - G2P failures are now handled gracefully; problematic chunks are skipped, not crashed.
  - Clipboard/selection capture is now robust: polls for up to 0.5s, logs raw and sanitized selection, and falls back to clipboard if needed.
  - Log lines and token dumps are stripped before TTS, so logs are never spoken.
  - New: Optional phoneme logging for each chunk (see kokoro_tts.py: SHOW_PHONEMES_IN_LOGS).

## Robust Error Handling and Fallback

Kokoro TTS automatically detects available hardware and will use GPU acceleration if possible. If the GPU is unavailable or an error occurs, it will gracefully fall back to CPU execution, ensuring that speech synthesis always works. All errors are logged for debugging, and problematic text chunks are skipped rather than causing a crash.

---

## Voice Agent Integration (MCP Speak)

- All agent and assistant features must use the MCP speak function for every response, ensuring accessibility and hands-free operation.
- Example: After any code change, status update, or error, the agent should call the MCP speak tool to announce the result.
- If the MCP or TTS is unavailable, log the failure and continue, but always attempt to speak first.

## MCP Server Integration

- VibeType now manages the MCP server as a subprocess.
- Features:
  - Auto-start MCP server on launch (configurable in settings; persisted)
  - Manual Start/Stop/Restart controls in the GUI
  - Status indicator for MCP server (running/stopped)
  - MCP logs are viewable in the VibeType UI
  - Clear Logs button for MCP panel
  - Ping MCP /health button (shows Healthy/Unreachable and appends a log line)
  - One-click Test Speak (Hello) button (queues a short line via MCP)
  - Batch speech via local HTTP /speak_batch enqueues sequentially (no overlap)
  - Graceful shutdown of MCP server on VibeType exit
- This removes the need to manually launch MCP in a separate terminal.

## AI Integration with Thinking Fillers 🧠💬

**NEW**: VibeType now includes an intelligent thinking fillers system that makes AI interactions feel more natural and engaging.

### What are Thinking Fillers?
When you ask Ollama a question, there's usually a delay while the AI processes your request. Instead of awkward silence, VibeType can now speak natural filler phrases to indicate that it's working on your request.

### How It Works
- **Automatic Detection**: When an AI request is made, the system automatically starts speaking filler phrases
- **Smart Timing**: Fillers are spoken at natural intervals with randomized timing
- **Variety**: Over 40 different phrases to keep interactions fresh
- **Contextual**: Different types of phrases for different situations

### Types of Filler Phrases

**Thinking Indicators:**
- "Let me think about that for a moment..."
- "Processing your request..."
- "Analyzing your input..."
- "Working on that now..."

**Short Pauses:**
- "Just a moment..."
- "Give me a sec..."
- "Almost there..."
- "Nearly done..."

**Professional Responses:**
- "Formulating a response..."
- "Gathering my thoughts..."
- "Reviewing the details..."

**Technical Context:**
- "Querying the language model..."
- "Running inference..."
- "Processing tokens..."

### Configuration Options

You can customize the thinking fillers behavior in your `config.json`:

```json
{
  "ai_providers": {
    "Ollama": {
      "use_thinking_fillers": true,
      "filler_initial_delay": 0.5,
      "filler_interval_min": 2.5,
      "filler_interval_max": 5.0,
      "speak_response": true
    }
  }
}
```

- `use_thinking_fillers`: Enable/disable the feature
- `filler_initial_delay`: Seconds to wait before first filler phrase
- `filler_interval_min`: Minimum seconds between filler phrases  
- `filler_interval_max`: Maximum seconds between filler phrases

### Benefits
- **Natural Interaction**: No more awkward silences during AI processing
- **User Feedback**: Clear indication that the system is working
- **Engagement**: Keeps the conversation flowing naturally
- **Customizable**: Adjust timing to match your preferences

### Demo and Testing
Run the demo script to see how it works:
```bash
python dev/thinking_fillers_demo.py
```

This feature works seamlessly with all VibeType AI modes: Chat, Explain, Summarize, and Correct.
