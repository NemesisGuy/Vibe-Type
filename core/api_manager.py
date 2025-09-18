# core/api_manager.py

import multiprocessing
import time
import os
import requests
from core.config_manager import load_config

# --- Globals for managing the server process ---
api_process = None

def start_api_server():
    """Starts the Flask API server in a separate process."""
    global api_process
    if api_process and api_process.is_alive():
        print("API server is already running.")
        return

    config = load_config()
    api_config = config.get('api', {})
    port = api_config.get('port', 5000)

    # We run the api.py script as a separate module in a new process
    process = multiprocessing.Process(target=run_flask_app, args=(port,))
    process.daemon = True
    process.start()
    api_process = process
    print(f"API server started on port {port} with PID {api_process.pid}")

def stop_api_server():
    """Stops the API server process."""
    global api_process
    if api_process and api_process.is_alive():
        print(f"Stopping API server with PID {api_process.pid}...")
        api_process.terminate()
        api_process.join(timeout=5) # Wait for graceful termination
        if api_process.is_alive():
            print("Process did not terminate gracefully, killing.")
            api_process.kill()
        api_process = None
        print("API server stopped.")
    else:
        print("API server is not running.")

def restart_api_server():
    """Restarts the API server."""
    stop_api_server()
    time.sleep(1) # Give the OS a moment to release the port
    start_api_server()

def run_flask_app(port):
    """This function is the entry point for the new process."""
    # We import here to ensure it's loaded in the new process context
    from api.api import app
    # Use waitress as a production-ready WSGI server instead of Flask's dev server
    try:
        import waitress
        waitress.serve(app, host='0.0.0.0', port=port)
    except ImportError:
        print("Waitress not found. Falling back to Flask's development server (not recommended for production).")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Failed to run Flask app: {e}")

def is_api_running():
    """Checks if the API server is running and responsive."""
    global api_process
    config = load_config()
    api_config = config.get('api', {})
    port = api_config.get('port', 5000)
    # Check process (if managed by GUI)
    if api_process and api_process.is_alive():
        # Try to ping the API endpoint
        try:
            resp = requests.get(f"http://localhost:{port}/api/v1/tts/kokoro/languages", timeout=1)
            if resp.status_code == 200:
                return "running"
            else:
                return "error"
        except Exception:
            return "error"
    else:
        # Try to ping anyway (in case started externally)
        try:
            resp = requests.get(f"http://localhost:{port}/api/v1/tts/kokoro/languages", timeout=1)
            if resp.status_code == 200:
                return "running"
            else:
                return "stopped"
        except Exception:
            return "stopped"
