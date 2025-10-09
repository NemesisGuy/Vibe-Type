# Changelog

All notable changes to this project are documented here.

## 2025-10-09 — MCP Server Fixes and GUI Testing

Summary:
- **Fixed Sequential Batch Speech**: The `/speak_batch` endpoint in `vibetts_mcp_server.py` now correctly iterates through all items and calls `core.tts.speak_text` for each one. The underlying TTS queue and playback lock in `core/tts.py` ensure these items are spoken sequentially, not in parallel, resolving the overlapping audio issue.
- **Fixed Phoneme Generation**: The `/phonemes` endpoint in `vibetts_mcp_server.py` now correctly uses the `kokoro_tts_instance.phonemize_text` method, which leverages the powerful polyglot chunker from `kokoro_tts.py`. This guarantees accurate and reliable phoneme generation for multiple languages.
- **Added GUI Test Utilities**: To facilitate easy testing, the MCP tab in the settings window now includes "Test /speak_batch" and "Test /phonemes" buttons. These allow for direct verification of the fixed endpoints from the GUI.
- **Consolidated Server Logic**: The MCP server logic has been successfully consolidated into `vibetts_mcp_server.py`, and the redundant `fastmcp.py` has been removed.

Key changes:
- `MCP/vibetts_mcp_server.py`: Updated `/speak_batch` and `/phonemes` handlers to call the correct, robust core logic in `core/tts.py`.
- `gui/settings_window.py`: Added new buttons and handler functions to test the MCP endpoints directly.
- `core/tts.py`: Verified that the existing `tts_playback_lock` correctly serializes all speech requests, solving the batch overlap problem.
- **Documentation**: Updated `CHANGELOG.md` and `know_fixed_bugs_to_avoid.md` to reflect these final fixes.

## 2025-10-08 — MCP server endpoints + GUI health/test controls

Summary:
- Added a lightweight MCP HTTP server with simple speech endpoints and live log streaming to the MCP tab.
- Implemented sequential queuing for local HTTP batch speech (no overlap).
- Enhanced GUI MCP tab with Ping /health, Test Speak, and Clear Logs.
- Persisted MCP auto-start in settings.

Key changes:
- MCP Server (local HTTP)
  - Endpoints:
    - GET /health -> "ok"
    - POST /speak { text } -> enqueues one utterance
    - POST /speak_batch { texts: [...] } -> enqueues all items sequentially
  - Line-buffered stdout for immediate UI logs.
  - Address reuse to reduce restart bind errors on Windows.
- GUI (Settings → 🛠️ MCP)
  - New buttons: Ping MCP /health, Test Speak (Hello), Clear Logs.
  - Start/Stop/Restart MCP controls remain; auto-start persisted.
- Manager
  - MCP subprocess started unbuffered (PYTHONUNBUFFERED=1) so logs stream to UI in real time.

Known issues:
- Phoneme tool: Returns `phonemes: null` with error `"NoneType" object is not iterable` for some texts. This is a server-side G2P handler behavior; recommend coercing None to [] before iterating.
- The external “MCP speak_batch tool” may start multiple items simultaneously. Use the local HTTP /speak_batch (now sequential) or update the tool wrapper to enqueue per line.

Recommendations / Next steps:
- Wire the MCP tool’s `speak_batch` to call the local HTTP `/speak_batch` for guaranteed sequential playback.
- Fix phoneme handler: always return a list (empty on failure) and include an error field.
- Optional: auto-refresh health indicator in MCP tab (periodic /health ping).
- Optional: add `/status` with queue size; add `/stop` and `/clear_queue` endpoints.

Docs:
- Added docs/MCP.md (endpoints, GUI controls, quick tests, troubleshooting, roadmap).
- README updated with "MCP Server & GUI" section.

## 2025-09-24 — API auto-start + MCP integration stabilization

Summary:
- Fixed API auto-start import issues and stabilized MCP-driven TTS.
- Converted Kokoro “speak” to return-fast with background playback, added queue/backpressure and a watchdog.
- Hardened MCP client with timeouts, connection handling, and batching.
- Added health/status endpoints and a friendly root index.

Breaking symptoms observed:
- API auto-start failed due to missing PYTHONPATH and wrong CWD.
- HTTP requests to /speak hung while TTS was playing.
- Occasional ReadTimeouts and lingering connections.
- Name collision with local `MCP/mcp.py` shadowing the `mcp` package.
- IDE MCP logs showed permission errors when writing to protected paths.

Key changes:
- API
  - Return-fast speak (200, `{ status: "in_progress" }`).
  - Background TTS playback with a single worker (ThreadPoolExecutor) and small queue (MAX_QUEUE=3).
  - Per-job watchdog (MAX_SPEAK_SECONDS=20) to interrupt stuck streams.
  - Add `Connection: close` on responses to avoid lingering sockets.
  - Add `/status` (root) and `/api/v1/status` for health + queue metrics.
  - Add root `/` JSON index with endpoint discovery.
  - Prefer Waitress WSGI; Flask dev server used with `threaded=True` fallback.
  - Read host/port from env `VIBETYPE_API_HOST`/`VIBETYPE_API_PORT`.
- MCP
  - Read API host/port from env; map `0.0.0.0` to `127.0.0.1` for clients.
  - Lower read timeout; treat read timeouts as accepted success.
  - Send `Connection: close`; handle `429` busy explicitly.
  - Added `speak_batch` to reduce repeated approvals.
  - Aligned MCP Manager to pass env and PYTHONPATH; stream logs back to UI.
- App launcher
  - API readiness check switched from `/status` to `languages` endpoint.
  - Stream child stdout/stderr; print “API server is up” when ready.

Docs updated:
- `docs/API.md` updated with versioned endpoints, speak behavior, and health.
- `agents.md` updated with speech usage guidelines and batching.
- `know_fixed_bugs_to_avoid.md` updated with pitfalls and fixes.

Upgrade notes:
- Install Waitress in your `.venv` for more stable HTTP on Windows: `pip install waitress`.
- Ensure `MCP/mcp.py` is not shadowing the `mcp` package; use `vibetts_mcp_server.py`.
- Use `/status` or `/api/v1/status` to check queue metrics.
