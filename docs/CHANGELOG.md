# Changelog

All notable changes to this project are documented here.

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

