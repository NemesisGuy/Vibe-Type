# VibeType MCP Server

This lightweight HTTP server lets you drive local speech via simple endpoints and see live logs in the MCP tab.

Endpoints
- GET /health
  - Returns: ok
  - Use to check readiness.
- POST /speak
  - Body: { "text": "Hello world" }
  - Queues a single utterance for sequential playback (no overlap).
  - Returns 202 { status: "accepted", queued: 1 }
- POST /speak_batch
  - Body: { "texts": ["one", "two", "three"] }
  - Queues all items sequentially; they will play one after another.
  - Returns 202 { status: "accepted", queued: N }

Queue behavior
- All speak requests use the app’s central TTS queue (core/tts.py), guaranteeing sequential playback and respecting the current TTS provider.
- Use “Interrupt speech” in the app to stop current playback and clear the queue.

GUI integration (Settings → 🛠️ MCP)
- Start/Stop/Restart MCP controls
- Live log panel
- Clear Logs button
- Ping MCP /health button (shows Healthy/Unreachable)
- Test Speak (Hello) button (enqueues a short test line)
- Auto-start MCP on launch setting

Quick tests (Windows cmd.exe)
```bat
cd /d C:\Users\Reign\Documents\Python Projects\VibeType
python MCP\vibetts_mcp_server.py
```
In a second terminal:
```bat
curl http://127.0.0.1:9032/health
curl -s -X POST http://127.0.0.1:9032/speak -H "Content-Type: application/json" -d "{\"text\":\"Hello from MCP\"}"
curl -s -X POST http://127.0.0.1:9032/speak_batch -H "Content-Type: application/json" -d "{\"texts\":[\"one\",\"two\",\"three\"]}"
```

Notes
- The MCP server uses the current TTS provider and output device you’ve configured in the app.
- If you hear overlapping audio from other sources, MCP enqueued items will still play sequentially on the app’s main TTS path.
- Logs stream line-by-line to the MCP tab; if you don’t see updates, click Restart MCP.

