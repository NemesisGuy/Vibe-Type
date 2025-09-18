# VibeType Web API

> **Recent Improvements (2025-09-17):**
> - Kokoro TTS now supports robust polyglot (multi-language) synthesis, improved error handling, and optional phoneme logging. See FEATURES.md for details.

This document provides details on the VibeType web API, which allows for programmatic interaction with the system's core functionalities.

## Kokoro TTS API

These endpoints provide access to the powerful, local Kokoro TTS engine.

### Get Supported Languages

*   **Endpoint:** `/api/tts/kokoro/languages`
*   **Method:** `GET`
*   **Description:** Returns a JSON array of all supported languages, including "Auto-Detect".
*   **Example Response:**
    ```json
    [
        "Auto-Detect",
        "English (US)",
        "English (UK)",
        "Japanese",
        "Spanish",
        "French",
        "Hindi",
        "Italian",
        "Portuguese (BR)",
        "Mandarin Chinese"
    ]
    ```

### Get Available Voices

*   **Endpoint:** `/api/tts/kokoro/voices`
*   **Method:** `GET`
*   **Description:** Returns a JSON array of available voices. Can be filtered by language.
*   **Query Parameters:**
    *   `language` (optional): The name of the language to filter by (e.g., "English (US)", "Japanese"). If not provided, all voices will be returned.
*   **Example Request:**
    ```
    GET /api/tts/kokoro/voices?language=Japanese
    ```
*   **Example Response:**
    ```json
    [
        "ja_01",
        "ja_02",
        "ja_03"
    ]
    ```

### Synthesize Speech

*   **Endpoint:** `/api/tts/kokoro/synthesize`
*   **Method:** `POST`
*   **Description:** Synthesizes speech from the provided text and returns the audio as a WAV file.
*   **Request Body (JSON):**
    *   `text` (required): The text to be synthesized.
    *   `voice` (required): The name of the voice to use.
    *   `language` (optional): The language of the text. Defaults to `"Auto-Detect"`.
    *   `speed` (optional): The speech rate. Defaults to `1.0`.
*   **Example Request:**
    ```json
    {
        "text": "Hello world. こんにちは、世界",
        "voice": "en_us_01",
        "language": "Auto-Detect",
        "speed": 1.2
    }
    ```
*   **Success Response:**
    *   **Code:** `200 OK`
    *   **Content-Type:** `audio/wav`
    *   The response body will contain the raw WAV audio data.
*   **Error Response:**
    *   **Code:** `400 Bad Request` or `500 Internal Server Error`
    *   **Content-Type:** `application/json`
    *   **Example Body:**
        ```json
        {
            "error": "Missing required parameters: text, voice"
        }
        ```

## Implemented Endpoints

The following endpoints are currently available:

### Get Supported Languages
- **Endpoint:** `/api/tts/kokoro/languages`
- **Method:** `GET`
- **Description:** Returns a JSON array of all supported languages, including "Auto-Detect".

### Get Available Voices
- **Endpoint:** `/api/tts/kokoro/voices`
- **Method:** `GET`
- **Description:** Returns a JSON array of available voices. Can be filtered by language.
- **Query Parameters:**
    - `language` (optional): The name of the language to filter by (e.g., "English (US)", "Japanese").

### Synthesize Speech
- **Endpoint:** `/api/tts/kokoro/synthesize`
- **Method:** `POST`
- **Description:** Synthesizes speech from the provided text and returns the audio as a WAV file.
- **Request Body (JSON):**
    - `text` (required): The text to be synthesized.
    - `voice` (required): The name of the voice to use.
    - `language` (optional): The language of the text. Defaults to "Auto-Detect".
    - `speed` (optional): The speech rate. Defaults to 1.0.

## Planned/Experimental Endpoints

The following endpoints are planned or experimental and may not be available in your current build:

- **Batch Synthesis Endpoint:** Submit multiple texts for synthesis in a single API call.
- **Phoneme Breakdown Endpoint:** Return the phoneme sequence and tokenization for a given text (for debugging or educational use).
- **Language Detection Endpoint:** Expose the language detection/segmentation logic as an API for external tools.
- **Streaming Synthesis API:** Support real-time streaming of audio chunks over HTTP/WebSocket.
- **Voice Blending API:** Allow users to create and manage custom blended voices via the API.
- **API for Pronunciation Dictionary:** Let users upload/download custom pronunciation overrides.

## Debugging and Logging

- **Phoneme Logging:** You can enable detailed phoneme logging for each chunk by setting `SHOW_PHONEMES_IN_LOGS` in `kokoro_tts.py`. This is useful for debugging and understanding how text is processed internally.
