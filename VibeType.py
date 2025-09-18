# vibe_type.py

import tkinter as tk
import gui.theme_manager
from gui.tray_app import TrayApplication
from core import hotkey_handler
import subprocess
from core.config_manager import load_config
import os
import sys

def maybe_start_api_server():
    import time
    config = load_config()
    api_config = config.get('api', {})
    if api_config.get('auto_start', False):
        api_path = os.path.join(os.path.dirname(__file__), 'api', 'api.py')
        print('Auto-starting API server...')
        env = os.environ.copy()
        proc = subprocess.Popen(
            [sys.executable, api_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(__file__),
            env=env
        )
        print(f'API server started in background with PID {proc.pid}')
        # Wait 2 seconds, then check if process is still running
        time.sleep(2)
        if proc.poll() is not None:
            out, err = proc.communicate()
            print(f'API server exited early with code {proc.returncode}')
            print('API server stdout:', out)
            print('API server stderr:', err)
        else:
            print('API server is still running after 2 seconds.')

def main():
    """Main function to start VibeType with the correct, stable initialization order."""
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
