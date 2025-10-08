import sys
import os

print("--- RUNNING LATEST MCP SERVER SCRIPT ---", flush=True)

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import via package re-export for better IDE resolution
from MCP.server import FastMCP

# This is the main entry point for the MCP server process.
# It should be run as a separate process from the main VibeType application.

if __name__ == "__main__":
    # The port can be passed as a command-line argument, or default to 9032
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9032

    # Create and run the server
    server = FastMCP(host='127.0.0.1', port=port)

    print(f"VibeTTS MCP Server starting on port {port}...", flush=True)
    server.run()
    print("VibeTTS MCP Server has stopped.", flush=True)
