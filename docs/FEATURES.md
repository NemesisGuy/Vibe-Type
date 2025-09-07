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
    *   **Type:** Custom Local
    *   **Default:** Disabled
    *   **Description:** A high-quality, local TTS engine with multi-language support. Requires model files to be placed in the `/models/kokoro` directory.
    *   **Configuration:** Select the desired model file, language, and primary voice from the settings window.
    *   **Seamless Streaming:** This engine supports seamless, chunked streaming for a more responsive experience.

*   **Piper TTS (Local):**
    *   **Type:** Custom Local
    *   **Default:** Disabled
    *   **Description:** A fast, efficient, and high-quality local TTS engine. Requires model files to be placed in the `/models/piper` directory.
    *   **Configuration:** Select the desired model file and voice from the settings window.

*   **Kitten TTS (Coming Soon):**
    *   **Type:** Custom Local
    *   **Description:** An upcoming, high-performance TTS engine.

## The AI Toolkit: Prompt Templates

Select an active prompt to change the AI's "personality" and tell it what kind of task to perform. The active prompt is used by the **AI Dictation** and **Process Clipboard** hotkeys.

*   **Assistant:** A general-purpose conversational AI for answering questions or generating text.
*   **Corrector:** Fixes grammar and spelling mistakes without changing the meaning. Ideal for cleaning up dictation.
*   **Summarizer:** Condenses long text into key points. Perfect for summarizing articles from your clipboard.
*   **Chat:** A more free-form conversational AI for natural, back-and-forth interaction.

## Customization and Prompts

All hotkeys, provider settings (API keys, URLs, models), and AI prompts can be fully customized in the **Settings** window. VibeType now features a dedicated **Prompts** settings page, allowing you to create, edit, and save unique prompts for each operational mode.

When a hotkey is used, the associated prompt is passed to the Ollama LLM, ensuring that your custom instructions are applied correctly. This allows you to tailor the AI's behavior to your specific needs, whether you're correcting dictation, summarizing text, or engaging in a voice conversation.
