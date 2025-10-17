import sys
import os

# Ensure project root is on sys.path for imports like `from core import tts`
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# All human-readable logs must go to stderr so stdout is reserved for JSON-RPC frames
print("--- STARTING VibeTTS MCP (wrapper -> stdio server) ---", file=sys.stderr, flush=True)

try:
    # Delegate to the canonical stdio MCP server implementation
    from MCP import vibetts_mcp_stdio_server as _stdio
except Exception as e:
    print(
        "ERROR: Failed to import stdio MCP server (MCP/vibetts_mcp_stdio_server.py).\n"
        "Make sure the project is intact and dependencies are installed (pip install mcp).\n"
        f"Detailed error: {e}",
        file=sys.stderr,
        flush=True,
    )
    raise

if __name__ == "__main__":
    # Run with stdio transport so IDEs (JetBrains, etc.) can discover via configured command
    print("VibeTTS MCP server (stdio) is starting...", file=sys.stderr, flush=True)
    _stdio.app.run()
    print("VibeTTS MCP server (stdio) stopped.", file=sys.stderr, flush=True)
