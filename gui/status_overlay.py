# gui/status_overlay.py

import tkinter as tk

class StatusOverlay(tk.Toplevel):
    """A small, borderless window to display the application's current status."""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.overrideredirect(True)  # Make it a borderless window
        self.attributes('-topmost', True) # Keep it on top of other windows
        self.attributes('-alpha', 0.85) # Make it slightly transparent

        # Position the window at the bottom-center of the screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"+{(screen_width // 2) - 150}+{(screen_height) - 100}")

        self.status_label = tk.Label(self, text="Initializing...",
                                     font=("Arial", 12, "bold"),
                                     bg="#2b2b2b", fg="white",
                                     padx=15, pady=8)
        self.status_label.pack()

        self._after_id = None
        self.withdraw() # Start hidden

    def update_status(self, text: str):
        """Updates the text on the overlay and makes it visible."""
        self.status_label.config(text=text)
        self.deiconify()
        
        # Automatically hide the window after a few seconds
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(3000, self.withdraw) # Hide after 3 seconds

    def hide(self):
        """Hides the overlay window."""
        self.withdraw()
