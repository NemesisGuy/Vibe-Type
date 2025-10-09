import sys
import os
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from socketserver import TCPServer
import threading
import importlib
import glob

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import tts as core_tts

print("--- RUNNING LATEST MCP SERVER SCRIPT (INLINE IMPLEMENTATION) ---", flush=True)

# --- Server Implementation (formerly in fastmcp.py) ---
class _MCPHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args):
        msg = "%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args)
        print(msg, flush=True)

    # Utilities
    def _json(self, code: int, obj: dict):
        data = json.dumps(obj).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)

    def _read_json_body(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode('utf-8')) if raw else {}
        except Exception as e:
            self._json(400, {"error": f"Invalid JSON: {e}"})
            return None

    # Endpoints
    def do_GET(self):
        if self.path == '/health':
            body = b"ok"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
            return
        # default index info
        info = {
            "status": "ok",
            "endpoints": ["GET /health", "POST /speak", "POST /speak_batch", "POST /phonemes"],
            "message": "VibeType MCP"
        }
        self._json(200, info)

    def do_POST(self):
        path = self.path.rstrip('/')
        payload = self._read_json_body()
        if payload is None:
            return  # error already sent

        if path == '/speak':
            text = (payload or {}).get('text')
            if not text:
                self._json(400, {"error": "Missing 'text'"})
                return
            try:
                core_tts.speak_text(text)
                print(f"[MCP] /speak accepted: '{text[:60]}{'...' if len(text)>60 else ''}'", flush=True)
                self._json(202, {"status": "accepted", "queued": 1})
            except Exception as e:
                print(f"[MCP] /speak error: {e}", flush=True)
                self._json(500, {"error": str(e)})
            return

        if path == '/speak_batch':
            items = (payload or {}).get('items')  # Changed 'texts' to 'items'
            if not isinstance(items, list) or not items:
                self._json(400, {"error": "Missing or empty 'items' array"})
                return
            try:
                accepted = 0
                for item in items:  # Iterate through list of objects
                    # Extract text from each object
                    t = item.get('text') if isinstance(item, dict) else item
                    if not isinstance(t, str) or not t.strip():
                        continue
                    core_tts.speak_text(t)
                    accepted += 1
                print(f"[MCP] /speak_batch accepted {accepted} item(s)", flush=True)
                self._json(202, {"status": "accepted", "queued": accepted})
            except Exception as e:
                print(f"[MCP] /speak_batch error: {e}", flush=True)
                self._json(500, {"error": str(e)})
            return

        if path == '/phonemes':
            text = (payload or {}).get('text')
            language = (payload or {}).get('language', 'Auto-Detect')
            if not text or not isinstance(text, str):
                self._json(400, {"error": "Missing 'text'"})
                return
            try:
                # Ensure Kokoro TTS is initialized before use
                core_tts._initialize_kokoro_tts()
                kt = getattr(core_tts, 'kokoro_tts_instance', None)
                if not kt:
                    self._json(503, {"error": "Kokoro TTS not initialized or is disabled."})
                    return

                segments = kt.phonemize_text(text, language_name=language)

                # Check for errors within segments
                has_errors = any(seg.get('error') and seg['error'] is not None for seg in segments)
                if not segments or has_errors:
                    print(f"[MCP] /phonemes error response: {segments}", flush=True)
                    self._json(500, {"error": "Phoneme generation failed.", "details": segments})
                    return

                self._json(200, {"status": "ok", "count": len(segments), "segments": segments})
            except Exception as e:
                print(f"[MCP] /phonemes critical error: {e}", flush=True)
                self._json(500, {"error": str(e)})
            return

        self._json(404, {"error": "Unknown endpoint"})

class FastMCP:  # Keep name for backward compatibility
    def __init__(self, host: str = '127.0.0.1', port: int = 9032):
        self.host = host
        self.port = int(port)
        self._httpd: ThreadingHTTPServer | None = None
        TCPServer.allow_reuse_address = True

    def run(self):
        try:
            sys.stdout.reconfigure(line_buffering=True)
        except Exception:
            pass
        print(f"[MCP] Starting FastMCP HTTP server on http://{self.host}:{self.port}", flush=True)
        # Preload TTS heavy modules to reduce first-call latency
        try:
            from core import tts as _p  # noqa: F401
            print("[MCP] Preloaded core.tts", flush=True)
        except Exception as e:
            print(f"[MCP] Warning: preload failed: {e}", flush=True)
        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), _MCPHandler)
        except OSError as e:
            print(f"[MCP] ERROR: Failed to bind {self.host}:{self.port} -> {e}", flush=True)
            raise
        try:
            print("[MCP] Server ready. Endpoints: /health, /speak, /speak_batch, /phonemes", flush=True)
            self._httpd.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("[MCP] KeyboardInterrupt received, shutting down...", flush=True)
        except Exception as e:
            print(f"[MCP] Unhandled server error: {e}", flush=True)
            raise
        finally:
            if self._httpd:
                try:
                    self._httpd.shutdown()
                    self._httpd.server_close()
                finally:
                    print("[MCP] Server closed.", flush=True)
                    self._httpd = None

# --- Main Entrypoint ---
if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9032
    server = FastMCP(host='127.0.0.1', port=port)
    print(f"VibeTTS MCP Server starting on port {port}...", flush=True)
    server.run()
    print("VibeTTS MCP Server has stopped.", flush=True)
