# vibe_type.py

import logging
import tkinter as tk
import gui.theme_manager
from gui.tray_app import TrayApplication
from core import hotkey_handler
import subprocess
from core.config_manager import load_config
from core.logging_utils import configure_logging
import os
import sys
import threading
import time
import requests

_api_proc = None
_stdout_thread = None
_stderr_thread = None

def _stream_pipe(prefix, pipe):
    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break
            print(f"{prefix} {line.rstrip()}")
    except Exception:
        pass

def maybe_start_api_server():
    global _api_proc, _stdout_thread, _stderr_thread
    config = load_config()
    api_config = config.get('api', {})
    if api_config.get('auto_start', False):
        api_path = os.path.join(os.path.dirname(__file__), 'api', 'api.py')
        project_root = os.path.dirname(__file__)
        host = str(api_config.get('host', '0.0.0.0'))
        port = int(api_config.get('port', 9031))
        print('Auto-starting API server...')
        env = os.environ.copy()
        # Ensure local imports work and output is unbuffered for real-time logs
        env['PYTHONPATH'] = project_root + os.pathsep + env.get('PYTHONPATH', '')
        env['PYTHONUNBUFFERED'] = '1'
        env['PYTHONIOENCODING'] = 'utf-8'
        # Pass host/port to API
        env['VIBETYPE_API_HOST'] = host
        env['VIBETYPE_API_PORT'] = str(port)
        _api_proc = subprocess.Popen(
            [sys.executable, api_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root,
            env=env,
            bufsize=1
        )
        print(f'API server started in background with PID {_api_proc.pid}')
        # Stream logs to console so we see port/IP info from the API
        _stdout_thread = threading.Thread(target=_stream_pipe, args=('API stdout:', _api_proc.stdout), daemon=True)
        _stderr_thread = threading.Thread(target=_stream_pipe, args=('API stderr:', _api_proc.stderr), daemon=True)
        _stdout_thread.start()
        _stderr_thread.start()
        # Readiness probe with brief retries
        base_url = f"http://127.0.0.1:{port}"
        ready_url = f"{base_url}/api/v1/tts/kokoro/languages"
        ok = False
        for _ in range(10):  # up to ~5s
            if _api_proc.poll() is not None:
                break
            try:
                r = requests.get(ready_url, timeout=0.5)
                if r.status_code == 200:
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if _api_proc.poll() is not None:
            try:
                out, err = _api_proc.communicate(timeout=1)
            except Exception:
                out, err = '', ''
            print(f'API server exited early with code {_api_proc.returncode}')
            print('API server stdout:', out)
            print('API server stderr:', err)
        else:
            if ok:
                print(f'API server is up: {base_url} (languages endpoint OK) and host={host}')
            else:
                print('API server is still starting; logs will appear above if there are issues.')

def main():
    """Main function to start VibeType with the correct, stable initialization order."""
    log_file_path = configure_logging()
    logger = logging.getLogger(__name__)
    if log_file_path:
        logger.info("Logging to %s", log_file_path)
    else:
        logger.warning("File logging unavailable; falling back to console-only logging.")
    print("Starting VibeType...")

    # Auto-start API server if enabled in config
    maybe_start_api_server()

    # 1. Create the single, shared root window.
    root = tk.Tk()

    # 2. Apply the theme to this specific root window.
    gui.theme_manager.apply_theme(root)

    # 3. Hide the root window so the app is tray-only.
    root.withdraw()

    # 4. Create the application instance, passing it the themed root window.
    app = TrayApplication(root)

    # 5. Start the background hotkey listener.
    print("Starting hotkey listener...")
    hotkey_handler.start_hotkey_listener()

    # 6. Run the main application loop.
    print("Starting application main loop...")
    app.run()

    print("VibeType stopped.")

if __name__ == "__main__":
    main()
