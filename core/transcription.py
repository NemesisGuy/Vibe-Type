# core/transcription.py
import subprocess
import os
import json
from core.utils import get_resource_path, get_config_path

def _find_executable(directory: str) -> str | None:
    """Searches for a whisper executable in the given directory."""
    for exe_name in ["whisper-cli.exe", "whisper.exe", "main.exe"]:
        exe_path = os.path.join(directory, exe_name)
        if os.path.exists(exe_path):
            print(f"Found executable: {exe_path}")
            return exe_path
    return None

def transcribe_audio(audio_file_path: str) -> str:
    """
    Transcribes an audio file using the whisper.cpp executable and returns the text.
    """
    print(f"Attempting to transcribe audio file: {audio_file_path}")

    config = _load_config()
    model_name = config.get('whisper_model', 'base')
    execution_provider = config.get('whisper_execution_provider', 'CPU')

    # --- Path Setup ---
    whisper_dir = get_resource_path("bin/whisper_new")
    whisper_executable = _find_executable(whisper_dir)

    if not whisper_executable:
        return f"Error: Could not find whisper-cli.exe, whisper.exe, or main.exe in '{whisper_dir}'"

    model_path = get_resource_path(os.path.join("models", f"ggml-{model_name}.bin"))
    absolute_audio_path = os.path.abspath(audio_file_path)
    output_file_path = os.path.join(os.path.dirname(absolute_audio_path), "transcription_output")

    # --- Pre-flight Checks ---
    if not os.path.exists(model_path):
        return f"Error: Model file not found at {model_path}"
    if not os.path.exists(absolute_audio_path):
        return f"Error: Audio file not found at {absolute_audio_path}"

    # --- Command Execution ---
    command = [
        whisper_executable,
        "-m", model_path,
        "-f", absolute_audio_path,
        "-l", "en",
        "-otxt",
        "-of", output_file_path
    ]

    # Add execution provider argument
    if execution_provider == "GPU":
        command.append("--gpu") # Assuming --gpu is the correct flag for GPU execution
    # No special flag needed for CPU, as it's usually the default

    try:
        print(f"Executing Whisper from directory: {whisper_dir}")
        subprocess.run(command, capture_output=True, text=True, check=True, cwd=whisper_dir, startupinfo=_get_startup_info())

        transcript_filepath = output_file_path + ".txt"
        with open(transcript_filepath, 'r', encoding='utf-8') as f:
            transcribed_text = f.read().strip()

        os.remove(transcript_filepath)

        print("Transcription successful.")
        return transcribed_text

    except subprocess.CalledProcessError as e:
        error_msg = f"Whisper failed with exit code {e.returncode}.\\nStderr: {e.stderr.strip()}"
        print(error_msg)
        return "Error during transcription. See console for details."
    except FileNotFoundError:
        return "Error: Could not find the transcription output file. Did Whisper run correctly?"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def _load_config():
    config_path = get_config_path()
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    return {
        "whisper_model": config.get("whisper_model", "base"),
        "whisper_execution_provider": config.get("hardware", {}).get("whisper_execution_provider", "CPU")
    }

def _get_startup_info():
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None
