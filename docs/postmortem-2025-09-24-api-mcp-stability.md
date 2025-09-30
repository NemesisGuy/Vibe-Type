# Postmortem: API auto-start + MCP TTS stability (2025-09-24)

## Summary
After enabling API auto-start and integrating the MCP speech tool, repeated `speak` calls would hang and the API stopped responding after a few requests. We identified multiple contributing issues and shipped fixes to make the pipeline reliable again.

## Impact
- Users could not make more than ~2–3 TTS requests without the API becoming unresponsive.
- Agent interactions via MCP needed repeated approvals and would occasionally time out.

## Root Causes
1. Subprocess import path: API subprocess launched without project root on `PYTHONPATH` or correct `cwd` → `kokoro_tts` import failure during auto-start.
2. Flask dev server on Windows: Mixed threading + heavy ONNX work → stalls/lingering connections under load.
3. Long-running /speak requests: Client waited for playback; if slow, HTTP sockets lingered (keep-alive) and client timed out.
4. Unbounded background TTS: No watchdog; a stuck stream could block the single worker thread indefinitely.
5. Name collision: Local `MCP/mcp.py` shadowed the `mcp` package → import failures in integrated MCP mode.
6. Network host mismatch: API bound to `0.0.0.0` while MCP clients attempted to connect to the same host instead of `127.0.0.1`.

## What We Changed
- API
  - `speak` returns immediately (HTTP 200, `{ status: "in_progress" }`), with background playback.
  - Added single-worker `ThreadPoolExecutor` + small queue (`MAX_QUEUE=3`) for backpressure; `429` when busy.
  - Added per-job watchdog (`MAX_SPEAK_SECONDS=20`) that interrupts a stuck stream via `interrupt_event`.
  - Added `Connection: close` to responses; added `/status` (root + versioned) and a friendly `/` JSON index.
  - Prefer **Waitress** WSGI on Windows; fallback to Flask `threaded=True`.
  - APi reads `VIBETYPE_API_HOST`/`VIBETYPE_API_PORT` from env and logs resolved URLs.
- MCP
  - Lowered read timeouts; treat read timeouts as accepted success (to avoid blocking the agent).
  - Send `Connection: close`; handle `429` busy; map `0.0.0.0` to `127.0.0.1` for client requests.
  - Added `speak_batch` to reduce repeated approvals.
  - MCP Manager passes env + PYTHONPATH and streams logs back to UI.
- Launcher (VibeType.py)
  - Set PYTHONPATH and unbuffered env for subprocess; stream stdout/stderr.
  - Readiness probe uses `languages` endpoint and prints “API server is up …”.

## Verification
- `/` returns JSON index; `/status` returns health and queue metrics.
- Three back-to-back short `speak` calls return 200 quickly; queue_len increases briefly then returns to 0.
- On overload, API responds `429` instead of hanging; MCP returns `busy`.

## Regression Tests (manual)
- Auto-start in .venv: API logs host/port; `/languages` 200 within ~5s.
- `speak` happy path: Adam/Eric voices on short lines → accepted and audible.
- Busy path: Fire >3 speaks quickly → one returns `429`; subsequent retry succeeds.
- Timeout path: Artificially slow speech → client receives success with timeout note; audio still plays.

## Lessons & Follow-ups
- Prefer production WSGI (Waitress) on Windows for threaded Flask apps.
- Always return fast from fire-and-forget endpoints; use queues and watchdogs for long-running work.
- Avoid HTTP keep-alive for short local control-plane requests that start heavy background work.
- Document the need to avoid local module name collisions (`mcp.py`).
- Add an automated smoke test that hits `/languages`, `/status`, and triggers a short `speak`.

## Action Items
- [ ] Add optional dependency `waitress` to requirements and recommend in README (Windows).
- [ ] Add a tiny CLI smoke test script for `/status` + `speak`.
- [ ] Expose queue metrics in the UI and allow adjusting `MAX_QUEUE`/`MAX_SPEAK_SECONDS`.

