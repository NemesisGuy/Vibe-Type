# gui/tray_app.py

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
import tkinter as tk
import queue
import webbrowser

# Import from core
from core.config_manager import load_config, save_config
import gui.settings_window
from gui.status_overlay import StatusOverlay
from core.app_state import register_status_callback, register_command_queue

class TrayApplication:
    """Manages the system tray icon and application lifecycle in a stable, multi-threaded way."""
    def __init__(self, root: tk.Tk):
        # This class now accepts a pre-configured root window.
        self.root = root
        self.command_queue = queue.Queue()
        self.settings_window = None
        self.status_overlay = StatusOverlay(self.root) # Create the overlay window

        # --- State Management ---
        self.status_lock = threading.Lock()
        self.status = "VibeType - Idle"
        self._load_state_from_config()

        # --- Icon Management ---
        self.status_icons = {
            "Idle": self._create_image(64, 64, 'black', 'white'),
            "Listening": self._create_image(64, 64, 'blue', 'white'),
            "Transcribing": self._create_image(64, 64, 'yellow', 'black'),
            "AI Processing": self._create_image(64, 64, 'purple', 'white'),
            "AI Processing Clipboard": self._create_image(64, 64, 'purple', 'white'),
            "Speaking": self._create_image(64, 64, 'green', 'white'),
        }

        # Register callbacks after core components are initialized.
        register_status_callback(self._update_status_and_overlay) # Use the new combined callback
        register_command_queue(self.command_queue)

    def _load_state_from_config(self):
        config = load_config()
        self.ai_mode = config.get('ai_mode', 'Assistant')
        self.show_overlay = config.get('user_experience', {}).get('show_status_overlay', True)

    def _create_image(self, width, height, color1, color2):
        image = Image.new("RGB", (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)
        return image

    # --- Methods to be called from the Main (UI) Thread ---

    def _process_queue(self):
        try:
            while not self.command_queue.empty():
                command, args = self.command_queue.get_nowait()
                if hasattr(self, command):
                    getattr(self, command)(*args)
        finally:
            if self.root.winfo_exists():
                self.root.after(100, self._process_queue)

    def _open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        
        self.settings_window = gui.settings_window.create_settings_window(self.root, self._on_settings_saved)
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_force()

    def _on_settings_saved(self):
        self._load_state_from_config()
        if self.tray_icon:
            self.tray_icon.update_menu()

    def _shutdown(self):
        print("Shutdown command received. Stopping services...")
        if self.tray_icon:
            self.tray_icon.stop()
        if self.status_overlay:
            self.status_overlay.destroy()
        if self.root.winfo_exists():
            self.root.quit()

    # --- Methods to be called from the Tray Icon Thread ---

    def _update_status_and_overlay(self, status: str):
        """Updates both the tray icon and the status overlay."""
        with self.status_lock:
            self.status = status
        
        simple_status = status.split(' - ')[-1]
        
        # Update tray icon
        if self.tray_icon:
            new_icon = self.status_icons.get(simple_status, self.status_icons["Idle"])
            self.tray_icon.icon = new_icon
            self.tray_icon.title = self.status
            self.tray_icon.update_menu()

        # Update overlay window
        if self.show_overlay and self.status_overlay:
            # Since this is called from a non-UI thread, we need to schedule the UI update
            self.root.after(0, self.status_overlay.update_status, simple_status)

    def _toggle_overlay(self):
        """Toggles the visibility of the status overlay."""
        self.show_overlay = not self.show_overlay
        config = load_config()
        if 'user_experience' not in config:
            config['user_experience'] = {}
        config['user_experience']['show_status_overlay'] = self.show_overlay
        save_config(config)
        if not self.show_overlay and self.status_overlay:
            self.root.after(0, self.status_overlay.hide)
        if self.tray_icon:
            self.tray_icon.update_menu()

    def _get_menu(self):
        with self.status_lock:
            status_text = self.status

        yield item(status_text, None, enabled=False)
        yield pystray.Menu.SEPARATOR
        yield item('Settings', lambda: self.command_queue.put(('_open_settings', ())))
        yield item(
            'AI Mode',
            pystray.Menu(
                item('Assistant', lambda: self._set_ai_mode('Assistant'), checked=lambda item: self.ai_mode == 'Assistant', radio=True),
                item('Corrector', lambda: self._set_ai_mode('Corrector'), checked=lambda item: self.ai_mode == 'Corrector', radio=True),
                item('Summarizer', lambda: self._set_ai_mode('Summarizer'), checked=lambda item: self.ai_mode == 'Summarizer', radio=True)
            )
        )
        yield item('Show Status Overlay', self._toggle_overlay, checked=lambda item: self.show_overlay)
        yield pystray.Menu.SEPARATOR
        yield item('Help', lambda: webbrowser.open("https://github.com/thewh1teagle/vibetranscribe"))
        yield item('Exit', lambda: self.command_queue.put(('_shutdown', ())))

    def _set_ai_mode(self, mode_name: str):
        print(f"Setting AI mode to: {mode_name}")
        self.ai_mode = mode_name
        config = load_config()
        config['ai_mode'] = mode_name
        save_config(config)
        if self.tray_icon:
            self.tray_icon.update_menu()

    def _run_tray_icon(self):
        """The target for the tray icon thread."""
        initial_icon = self.status_icons["Idle"]
        self.tray_icon = pystray.Icon("VibeType", initial_icon, "VibeType", menu=self._get_menu())
        print("Starting tray icon...")
        self.tray_icon.run()

    def run(self):
        """Starts the application and blocks until exit."""
        tray_thread = threading.Thread(target=self._run_tray_icon, daemon=True)
        tray_thread.start()

        self._process_queue()
        self.root.mainloop()

        print("Application has exited.")
