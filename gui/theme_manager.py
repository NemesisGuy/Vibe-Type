# gui/theme_manager.py

import sv_ttk
import tkinter as tk
from core.config_manager import load_config

def apply_theme(root: tk.Tk):
    """
    Applies the application theme based on the user's configuration.
    The provided tk.Tk() root window will be themed.
    """
    config = load_config()
    theme = config.get("theme", "System")

    print(f"Applying theme: {theme}")

    # 'System' theme will default to dark for a better user experience.
    if theme == "Light":
        sv_ttk.set_theme("light")
    else:
        sv_ttk.set_theme("dark")
