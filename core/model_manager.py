# core/model_manager.py

import os
from tkinter import messagebox
from core.utils import get_resource_path

def delete_piper_model(model_filename: str):
    """Deletes the specified Piper model and its associated .json file."""
    if not model_filename:
        messagebox.showerror("Error", "No model selected.")
        return False

    if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete the model '{model_filename}'?"):
        return False

    try:
        model_path = get_resource_path(os.path.join("models", "piper", model_filename))
        config_path = f"{model_path}.json"

        if os.path.exists(model_path):
            os.remove(model_path)
            print(f"Deleted model file: {model_path}")
        else:
            print(f"Model file not found: {model_path}")

        if os.path.exists(config_path):
            os.remove(config_path)
            print(f"Deleted config file: {config_path}")
        else:
            print(f"Config file not found: {config_path}")

        messagebox.showinfo("Success", f"Model '{model_filename}' has been deleted.")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to delete model '{model_filename}'.\n\nError: {e}")
        return False
