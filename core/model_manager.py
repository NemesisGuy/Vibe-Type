# core/model_manager.py

import os
import shutil
from tkinter import messagebox, filedialog
from core.utils import get_resource_path

def import_piper_models():
    """Opens a file dialog to import Piper models (.onnx) and their configs (.json)."""
    # Ask user to select one or more .onnx files
    onnx_files = filedialog.askopenfilenames(
        title="Select Piper ONNX Model Files",
        filetypes=[("ONNX Models", "*.onnx")]
    )

    if not onnx_files:
        return False  # User cancelled

    models_dir = get_resource_path("models/piper")
    os.makedirs(models_dir, exist_ok=True)

    imported_count = 0
    errors = []

    for onnx_path in onnx_files:
        try:
            # Derive the expected config path
            config_path = f"{onnx_path}.json"
            model_filename = os.path.basename(onnx_path)
            config_filename = f"{model_filename}.json"

            # Check if both files exist
            if not os.path.exists(config_path):
                errors.append(f"Config file not found for {model_filename}. Expected: {config_filename}")
                continue

            # Define destination paths
            dest_model_path = os.path.join(models_dir, model_filename)
            dest_config_path = os.path.join(models_dir, config_filename)

            # Copy the files
            shutil.copy2(onnx_path, dest_model_path)
            shutil.copy2(config_path, dest_config_path)
            
            imported_count += 1
            print(f"Successfully imported {model_filename} and {config_filename}")

        except Exception as e:
            errors.append(f"Failed to import {os.path.basename(onnx_path)}: {e}")

    # Show summary message
    if imported_count > 0:
        messagebox.showinfo("Import Complete", f"Successfully imported {imported_count} model(s).")
    
    if errors:
        error_summary = "\n".join(errors)
        messagebox.showerror("Import Errors", f"Some models could not be imported:\n\n{error_summary}")

    return imported_count > 0

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
