import subprocess
import sys
import os
import threading
from core.config_manager import load_config

class MCPManager:
    def __init__(self):
        self.proc = None
        self.log_callback = None
        self._stdout_thread = None
        self._stderr_thread = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def _read_stream(self, stream):
        try:
            for line in iter(stream.readline, ''):
                if not line:
                    break
                if self.log_callback:
                    self.log_callback(line.rstrip())
        except Exception:
            # Silently ignore stream read errors (process may be closing)
            pass

    def start(self):
        if self.proc and self.proc.poll() is None:
            print("MCP already running.")
            return
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        # Force unbuffered output so GUI receives lines immediately
        env.setdefault("PYTHONUNBUFFERED", "1")
        # Ensure PYTHONPATH includes project root for local imports
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
        # Align MCP with API host/port from config
        cfg = load_config()
        api_cfg = cfg.get('api', {})
        env['VIBETYPE_API_HOST'] = str(api_cfg.get('host', '127.0.0.1'))
        env['VIBETYPE_API_PORT'] = str(api_cfg.get('port', 9031))
        # Use vibetts_mcp_server.py to avoid import collision with the 'mcp' package
        server_script = os.path.join("MCP", "vibetts_mcp_server.py")
        self.proc = subprocess.Popen(
            [sys.executable, server_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
            cwd=project_root  # Set working directory to project root
        )
        print("MCP started with PID:", self.proc.pid)
        if self.log_callback:
            self._stdout_thread = threading.Thread(target=self._read_stream, args=(self.proc.stdout,), daemon=True)
            self._stderr_thread = threading.Thread(target=self._read_stream, args=(self.proc.stderr,), daemon=True)
            self._stdout_thread.start()
            self._stderr_thread.start()

    def stop(self):
        if not self.proc:
            print("MCP not running.")
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        print("MCP stopped.")
        self.proc = None
        self._stdout_thread = None
        self._stderr_thread = None

    def restart(self):
        self.stop()
        self.start()

    def is_running(self):
        return self.proc is not None and self.proc.poll() is None
