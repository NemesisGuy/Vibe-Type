# VibeType Web API

> Recent Improvements (2025-09-24):
> - Versioned API base path `/api/v1`.
> - Kokoro TTS speak endpoint returns quickly with `{ status: "in_progress" }`.
> - Queue/backpressure and health endpoint added to improve stability.
> - Recommended to run under Waitress on Windows; Flask dev server is used as a fallback.

This document provides details on the VibeType web API, which allows for programmatic interaction with the system's core functionalities.

## Base Path

All endpoints below are served under the versioned base path:

- Base: `/api/v1`

## Kokoro TTS API

These endpoints provide access to the powerful, local Kokoro TTS engine.

### Get Supported Languages

- Endpoint: `/api/v1/tts/kokoro/languages`
- Method: `GET`
- Description: Returns a JSON array of all supported languages, including `"Auto-Detect"`.
- Example Response:
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

- Endpoint: `/api/v1/tts/kokoro/voices`
- Method: `GET`
- Description: Returns a JSON array of available voices. Can be filtered by language.
- Query Parameters:
  - `language` (optional): The name of the language to filter by (e.g., `English (US)`, `Japanese`).
- Example Request:
  ```
  GET /api/v1/tts/kokoro/voices?language=Japanese
  ```
- Example Response:
  ```json
  ["am_adam", "af_nova", "am_eric", "zf_xiaoxiao", "..."]
  ```

### Get Available Models

- Endpoint: `/api/v1/tts/kokoro/models`
- Method: `GET`
- Description: Returns the available Kokoro ONNX model variants.

### Speak (fire-and-forget playback on server)

- Endpoint: `/api/v1/tts/kokoro/speak`
- Method: `POST`
- Description: Triggers speech playback on the server audio device in the background; the request returns quickly.
- Request Body (JSON):
  - `text` (required): Text to speak.
  - `voice` (required): Voice identifier.
  - `language` (optional): Defaults to `"Auto-Detect"`.
  - `speed` (optional): Defaults to `1.0`.
- Success Response:
  - Code: `200 OK`
  - Body:
    ```json
    { "status": "in_progress", "message": "Speech synthesis started" }
    ```
- Busy Response (backpressure):
  - Code: `429 Too Many Requests`
  - Body:
    ```json
    { "status": "error", "message": "TTS queue is busy. Try again shortly." }
    ```
- Notes:
  - The server limits concurrent TTS to improve stability and may queue requests.
  - Clients should not wait for playback to complete; treat `200/in_progress` as accepted.

### Synthesize (return audio)

- Endpoint: `/api/v1/tts/kokoro/synthesize`
- Method: `POST`
- Description: Synthesizes speech and returns a WAV file in the response.
- Request Body (JSON):
  - `text` (required)
  - `voice` (required)
  - `language` (optional, default `"Auto-Detect"`)
  - `speed` (optional, default `1.0`)
- Success Response:
  - Code: `200 OK`
  - Content-Type: `audio/wav`
- Error Response:
  - Code: `400` or `500`
  - Content-Type: `application/json`

### Phoneme Breakdown

- Endpoint: `/api/v1/tts/kokoro/phonemes`
- Method: `POST`
- Description: Returns the phoneme sequence and tokenization for the provided text (for debugging/education).
- Request Body (JSON): `{ "text": "...", "language": "Auto-Detect" }`

### Health / Status

- Endpoint: `/status`
- Method: `GET`
- Description: Returns API health plus TTS queue metrics.
- Example Response:
  ```json
  {
    "status": "ok",
    "message": "API server is running.",
    "version": "1.0",
    "queue_len": 0,
    "max_queue": 10,
    "max_workers": 1
  }
  ```

## MCP Integration Notes

- The MCP speak tool treats slow HTTP responses as accepted, to avoid client-side timeouts.
- To reduce permission prompts, use the `speak_batch` MCP tool to send multiple short lines in one request.
- Recommended voices for reliability: `am_adam`, `am_eric`.

## Debugging and Logging

- Server logs include queue size and background playback completion notices.
- On Windows, the API prefers **Waitress** for better concurrency; if not available, Flask dev server runs with `threaded=True`.
- If you see `429` busy, wait a few seconds and retry with shorter lines.
