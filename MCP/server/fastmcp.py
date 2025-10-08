import sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer
import json

class _Handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, obj: dict):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args):
        # Route server logs to stdout so the GUI can pick them up
        msg = "%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format%args)
        print(msg, flush=True)

    def do_GET(self):
        if self.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # Default: basic info
        body = ("VibeTTS MCP alive\n" +
                f"method=GET path={self.path}\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        try:
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON: {e}"})
            return

        path = self.path.rstrip('/')
        if path == "/speak":
            text = (payload or {}).get("text")
            if not text:
                self._send_json(400, {"error": "Missing 'text'"})
                return
            try:
                # Enqueue text for sequential TTS playback
                from core import tts as core_tts
                core_tts.speak_text(text)
                print(f"[MCP] /speak accepted: '{text[:60]}{'...' if len(text)>60 else ''}'", flush=True)
                self._send_json(202, {"status": "accepted", "queued": 1})
            except Exception as e:
                print(f"[MCP] /speak error: {e}", flush=True)
                self._send_json(500, {"error": str(e)})
            return

        if path == "/speak_batch":
            texts = (payload or {}).get("texts")
            if not isinstance(texts, list) or not texts:
                self._send_json(400, {"error": "Missing or empty 'texts' array"})
                return
            try:
                from core import tts as core_tts
                accepted = 0
                for t in texts:
                    if not isinstance(t, str) or not t.strip():
                        continue
                    core_tts.speak_text(t)
                    accepted += 1
                print(f"[MCP] /speak_batch accepted {accepted} item(s)", flush=True)
                self._send_json(202, {"status": "accepted", "queued": accepted})
            except Exception as e:
                print(f"[MCP] /speak_batch error: {e}", flush=True)
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "Unknown endpoint"})

class FastMCP:
    """Minimal HTTP-based MCP placeholder.

    Endpoints:
      - GET /health -> "ok"
      - POST /speak {text} -> enqueues one utterance for sequential TTS
      - POST /speak_batch {texts: [...]} -> enqueues many utterances sequentially

    All logs go to stdout line-by-line so the GUI MCP tab can display them.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 9032):
        self.host = host
        self.port = int(port)
        from http.server import ThreadingHTTPServer as _THS  # local alias for type hints
        self._httpd: _THS | None = None
        # Make TCPServer reuse address to reduce TIME_WAIT binding issues on restart
        TCPServer.allow_reuse_address = True

    def run(self):
        # Ensure stdout is line-buffered for immediate GUI updates
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
        print(f"[MCP] Starting FastMCP HTTP server on http://{self.host}:{self.port}", flush=True)
        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), _Handler)
        except OSError as e:
            print(f"[MCP] ERROR: Failed to bind {self.host}:{self.port} -> {e}", flush=True)
            raise

        try:
            print("[MCP] Server ready. Endpoints: GET /health, POST /speak, POST /speak_batch", flush=True)
            self._httpd.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("[MCP] KeyboardInterrupt received, shutting down...", flush=True)
        except Exception as e:
            print(f"[MCP] Unhandled server error: {e}", flush=True)
            raise
        finally:
            try:
                if self._httpd:
                    self._httpd.shutdown()
                    self._httpd.server_close()
                    print("[MCP] Server closed.", flush=True)
            finally:
                self._httpd = None
