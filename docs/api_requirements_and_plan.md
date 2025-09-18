# VibeType API Requirements & Design Plan

**Date:** 2025-09-17

## Purpose
To define the requirements, design decisions, and implementation plan for a robust, extensible API for VibeType, covering all main features (not just Kokoro TTS). This document ensures we do not break the working Kokoro TTS integration and provides a foundation for future API growth.

---

## 1. API Philosophy & Goals
- **Unified:** Expose all major VibeType features (TTS, STT, AI, clipboard, analytics, etc.) via a single, consistent API.
- **Extensible:** Easy to add new providers (TTS, AI, etc.) and new endpoints.
- **Non-breaking:** Do not disrupt existing Kokoro TTS functionality.
- **Secure:** Allow for future authentication/authorization.
- **Observable:** Log all API calls and errors for debugging and analytics.
- **User-centric:** Designed for both programmatic and GUI/automation use.

---

## 2. Core Features to Expose
- **Text-to-Speech (TTS):**
  - Providers: Kokoro, Piper, SAPI, OpenAI, (future: Kitten)
  - Endpoints: list languages, list voices, synthesize (with streaming option), get models
- **Speech-to-Text (STT):**
  - Providers: Whisper, (future: others)
  - Endpoints: transcribe audio, list models
- **AI/LLM:**
  - Providers: Ollama, Cohere, OpenAI, etc.
  - Endpoints: process text, list models/prompts
- **Clipboard/Selection:**
  - Endpoints: get/set clipboard, read selection, inject text
- **Analytics/Status:**
  - Endpoints: get usage stats, get/set config, get status
- **System/Utility:**
  - Endpoints: list audio devices, test sound, version info

---

## 3. Design Decisions
- **RESTful API:** Use clear, resource-oriented endpoints (e.g., `/api/tts/kokoro/synthesize`).
- **JSON for requests/responses** (except for binary audio data).
- **POST for actions, GET for queries.**
- **Streaming:** Use HTTP chunked responses or WebSockets for streaming audio (future).
- **Error Handling:** Standardized error format (code, message, details).
- **Versioning:** Prefix endpoints with `/api/v1/` for future-proofing.
- **Provider-agnostic:** All endpoints should allow specifying the provider (where relevant).

---

## 4. Kokoro TTS Section (First Implementation)
- **Endpoints:**
  - `GET /api/v1/tts/kokoro/languages` — List supported languages
  - `GET /api/v1/tts/kokoro/voices` — List voices (optionally filter by language)
  - `GET /api/v1/tts/kokoro/models` — List available models
  - `POST /api/v1/tts/kokoro/synthesize` — Synthesize speech (return WAV, support streaming in future)
  - `POST /api/v1/tts/kokoro/phonemes` — Return phoneme breakdown for text (for debugging/education)
- **Requirements:**
  - Must not break current Kokoro TTS usage in VibeType.
  - Should log all requests and errors.
  - Should validate input and return clear errors.
  - Should be easy to extend to other TTS providers.

---

## 5. Extensibility for Other Features
- Use `/api/v1/tts/{provider}/...` for all TTS providers.
- Use `/api/v1/stt/{provider}/...` for STT.
- Use `/api/v1/ai/{provider}/...` for AI/LLM.
- Use `/api/v1/clipboard/...`, `/api/v1/analytics/...`, etc.
- Allow for provider-specific and generic endpoints.

---

## 6. Error Handling & Logging
- All errors should return JSON: `{ "error": { "code": ..., "message": ..., "details": ... } }`
- Log all API calls (method, endpoint, params, status, error if any).
- Optionally log to analytics for usage tracking.

---

## 7. Security/Access Considerations
- For now, local access only (no authentication).
- Plan for future API key/token or OS user-based access control.
- CORS: allow localhost by default, restrict in production.

---

## 8. Testing & Versioning
- All endpoints should have unit/integration tests.
- Use `/api/v1/` prefix for all endpoints.
- Document all endpoints in OpenAPI/Swagger (future).

---

## 9. Open Questions / TODOs
- How to handle long-running/streaming jobs (WebSocket, chunked HTTP)?
- How to expose real-time status/interrupt for TTS jobs?
- How to handle user/session context (for clipboard, config, etc.)?
- How to expose advanced features (voice blending, phoneme logging toggle, etc.)?
- How to allow for plugin/extension endpoints?

---

## 10. MCP/Agent Integration Use Case

- The VibeType API is designed to be fully client-agnostic. It does not distinguish between requests from a normal client, a GUI, a script, or an MCP/agent server.
- This means that LLM agents, MCP servers, or any automation system can access TTS, STT, AI, clipboard, and analytics features via the same endpoints as any other client.
- No special code or handling is required for MCP/agent integration. The API is ready for use in multi-agent, distributed, or automated environments.
- Example use case: An MCP server can POST to `/api/v1/tts/kokoro/synthesize` to generate speech for an LLM agent, or use `/api/v1/tts/kokoro/phonemes` for phoneme breakdowns.
- Security and access control (API keys, tokens, etc.) can be added in the future if needed for multi-tenant or remote deployments.

---

## Voice Code Format and Examples

Voice codes follow this format:
- **First letters:** Language code (e.g., `am` = American English, `bf` = British English female, `jf` = Japanese female, `zm` = Mandarin male, etc.)
- **Next letter:** Gender (`f` = female, `m` = male)
- **Rest:** Name or model (e.g., `adam`, `alice`, `alpha`, `yunxi`)

**Examples:**
| Voice Code   | Language           | Gender | Name/Model |
|--------------|--------------------|--------|------------|
| am_adam      | American English   | Male   | Adam       |
| am_echo      | American English   | Male   | Echo       |
| bf_alice     | British English    | Female | Alice      |
| jf_alpha     | Japanese           | Female | Alpha      |
| zm_yunxi     | Mandarin Chinese   | Male   | Yunxi      |
| af_sky       | Afrikaans          | Female | Sky        |
| bm_fable     | British English    | Male   | Fable      |
| zf_xiaoxiao  | Mandarin Chinese   | Female | Xiaoxiao   |

**Tip:** Use the `/api/v1/tts/kokoro/voices?language=LANG` endpoint to get all available voices for a language.

---

## 11. Working Demo Requests & Example JSON (Postman-ready)

Below are working example requests for each Kokoro TTS API endpoint. You can use these JSON blocks directly in Postman or any HTTP client. Replace the host/port if you have configured a different one.

### 1. List Supported Languages

**GET** `/api/v1/tts/kokoro/languages`

**Response:**
```json
[
  "Auto-Detect",
  "English (US)",
  "Japanese",
  "Spanish",
  "French",
  "Hindi",
  "Italian",
  "Portuguese (BR)",
  "Mandarin Chinese"
]
```

### 2. List Voices (optionally filter by language)

**GET** `/api/v1/tts/kokoro/voices?language=Japanese`

**Response:**
```json
["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"]
```

### 3. List Available Models

**GET** `/api/v1/tts/kokoro/models`

**Response:**
```json
["kokoro-v1.0.fp16.onnx", "kokoro-v1.0.int8.onnx"]
```

### 4. Synthesize Speech (English Example)

**POST** `/api/v1/tts/kokoro/synthesize`

**Request Body:**
```json
{
  "text": "Hello world. This is a test of the American English voice.",
  "voice": "am_adam",
  "language": "English (US)",
  "speed": 1.0
}
```
**Response:**
- Returns a WAV audio file (binary data). If there is an error, you will get:
```json
{
  "error": {"code": 400, "message": "Missing required parameters: text, voice", "details": null}
}
```

### 4b. Synthesize Speech (Japanese Example)

**POST** `/api/v1/tts/kokoro/synthesize`

**Request Body:**
```json
{
  "text": "こんにちは、世界。これは日本語のテストです。",
  "voice": "jf_alpha",
  "language": "Japanese",
  "speed": 1.0
}
```

### 4c. Speak (Play Audio on Server, Mandarin Example)

**POST** `/api/v1/tts/kokoro/speak`

**Request Body:**
```json
{
  "text": "你好，世界。这是中文男声的测试。",
  "voice": "zm_yunxi",
  "language": "Mandarin Chinese",
  "speed": 1.0
}
```
**Response (success):**
```json
{
  "status": "ok",
  "message": "Speech played on server."
}
```
**Response (error):**
```json
{
  "error": {"code": 500, "message": "Synthesis or playback failed", "details": "..."}
}
```

### 5. Get Phoneme Breakdown (Spanish Example)

**POST** `/api/v1/tts/kokoro/phonemes`

**Request Body:**
```json
{
  "text": "políticos tradicionales compiten con los populismos",
  "language": "Spanish"
}
```
**Response:**
```json
[
  {
    "language": "Spanish",
    "text": "políticos tradicionales compiten con los populismos",
    "phonemes": "politikos tradhionales kompitɛn kon los populismos ",
    "tokens": [
      {"text": "políticos", "phonemes": "politikos", "whitespace": " "},
      {"text": "tradicionales", "phonemes": "tradhionales", "whitespace": " "},
      {"text": "compiten", "phonemes": "kompitɛn", "whitespace": " "},
      {"text": "con", "phonemes": "kon", "whitespace": " "},
      {"text": "los", "phonemes": "los", "whitespace": " "},
      {"text": "populismos", "phonemes": "populismos", "whitespace": " "}
    ]
  }
]
```

---

**Tip:** For all POST requests, set `Content-Type: application/json` in Postman. For `/synthesize`, set the response type to binary to save the WAV file.

---

## API Usage and Conventions

- All endpoints return JSON responses with a `status` field (`ok`, `in_progress`, or `error`).
- The `/tts/kokoro/speak` endpoint now always returns HTTP 200 with `{ "status": "in_progress", "message": "Speech synthesis started" }` for compatibility with MCP and agent clients.
- For long-running TTS operations, always return quickly with a status message and run synthesis in a background thread.
- Log the API server's IP and port on startup for easier debugging.
- If the TTS engine is not initialized, return a clear error message and HTTP 500.
- All error responses should use the `api_error` utility for consistency.

---

## Next Steps
1. Review and finalize this plan.
2. Implement/refactor the Kokoro TTS API endpoints to match this spec.
3. Gradually extend to other features/providers.
4. Add tests and documentation.
