import subprocess
import sys
import os

class MCPManager:
    def __init__(self):
        self.proc = None

    def start(self):
        if self.proc and self.proc.poll() is None:
            print("MCP already running.")
            return
        self.proc = subprocess.Popen(
            [sys.executable, os.path.join("MCP", "mcp.py")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("MCP started with PID:", self.proc.pid)

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

    def restart(self):
        self.stop()
        self.start()

    def is_running(self):
        return self.proc and self.proc.poll() is None

