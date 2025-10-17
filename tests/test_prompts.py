import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import tkinter as tk
from tkinter import ttk

# Prepare mocks for modules that settings_window imports at module load time
core_config_manager_mock = MagicMock()
core_tts_mock = MagicMock()
core_tts_mock.get_available_sapi_voices.return_value = []
core_tts_mock.get_kokoro_voices.return_value = []
core_tts_mock.get_output_devices.return_value = {"Default Device": 0}
core_tts_mock.play_test_sound.return_value = None
core_tts_mock.speak_text.return_value = None
core_tts_mock.trigger_kokoro_model_download.return_value = None
core_tts_mock.open_benchmark_folder.return_value = None
core_tts_mock.get_kokoro_models.return_value = []
core_tts_mock.trigger_kokoro_benchmark.return_value = None
core_tts_mock.test_kokoro_voice.return_value = None
core_tts_mock.get_piper_model_files.return_value = []
core_tts_mock.get_voices_for_piper_model.return_value = []
core_tts_mock.test_sapi_voice.return_value = None
core_tts_mock.test_piper_voice.return_value = None
core_tts_mock.test_openai_voice.return_value = None
core_tts_mock.get_kokoro_languages.return_value = ["English (US)"]
sample_stub = SimpleNamespace(name="zipvoice_sample", display_name="Sample Voice", wav_path="sample.wav", text_path="sample.txt")
core_tts_mock.get_zipvoice_samples.return_value = [sample_stub]
core_tts_mock.test_zipvoice_voice.return_value = None

zipvoice_manager_mock = MagicMock()
zipvoice_manager_mock.open_zipvoice_samples_folder.return_value = True

# Mock the necessary modules before they are imported by the module we are testing
with patch.dict('sys.modules', {
    'core.config_manager': core_config_manager_mock,
    'core.tts': core_tts_mock,
    'core.ai': MagicMock(),
    'core.model_manager': MagicMock(),
    'core.transcript_saver': MagicMock(),
    'core.analytics': MagicMock(),
    'core.performance_monitor': MagicMock(),
    'core.zipvoice_manager': zipvoice_manager_mock,
    'webbrowser': MagicMock()
}):
    from gui.settings_window import create_settings_window
    settings_window_module = sys.modules.get('gui.settings_window')

if settings_window_module is not None:
    sys.modules['gui.settings_window'] = settings_window_module

class TestPromptSettings(unittest.TestCase):

    def setUp(self):
        # Create a root window for the tests
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the main window

    def tearDown(self):
        # Destroy the root window after tests
        self.root.destroy()

    @patch('gui.settings_window.load_config')
    @patch('gui.settings_window.save_config')
    @patch('gui.settings_window.messagebox')
    def test_save_prompts(self, mock_messagebox, mock_save_config, mock_load_config):
        # Arrange
        # Mock the loaded configuration
        initial_config = {
            'theme': 'Dark',
            'enable_text_injection': True,
            'ai_providers': {
                'Ollama': {
                    'enabled': True,
                    'api_url': 'http://localhost:11434',
                    'model': 'llama3',
                    'speak_response': True,
                    'webhook_enabled': False,
                    'webhook_url': '',
                    'prompts': {
                        'Summarize': 'Initial summarize prompt',
                        'Explain': 'Initial explain prompt',
                        'Correct': 'Initial correct prompt',
                        'Chat': 'Initial chat prompt'
                    }
                }
            },
            'active_tts_provider': 'Windows SAPI',
            'tts_providers': {},
            'hardware': {},
            'audio': {},
            'history': {},
            'user_experience': {},
            'privacy': {},
            'hotkeys': {}
        }
        mock_load_config.return_value = initial_config

        # Create the settings window
        settings_window = create_settings_window(self.root)

        # Find the save button and the prompt entry widgets
        save_button = None
        prompt_entries = {}

        def find_widgets(widget):
            nonlocal save_button
            widget_class = widget.winfo_class()
            if widget_class in {"TButton", "Button"} and widget.cget('text') == '✔️ Save':
                save_button = widget
            if isinstance(widget, tk.Text):
                parent_tab_text = None
                ancestor = widget
                while True:
                    parent_name = ancestor.winfo_parent()
                    if not parent_name:
                        break
                    ancestor = settings_window.nametowidget(parent_name)
                    master = getattr(ancestor, "master", None)
                    if master is not None and hasattr(master, "tab"):
                        parent_tab_text = master.tab(ancestor, "text")
                        break
                if parent_tab_text in ["Summarize", "Explain", "Correct", "Chat"]:
                    prompt_entries[parent_tab_text] = widget
            for child in widget.winfo_children():
                find_widgets(child)

        find_widgets(settings_window)

        # Act
        # Simulate user modifying the prompts
        new_summarize_prompt = "New and improved summarize prompt"
        prompt_entries["Summarize"].delete("1.0", tk.END)
        prompt_entries["Summarize"].insert("1.0", new_summarize_prompt)

        # Simulate clicking the save button
        save_button.invoke()

        # Assert
        # Check that save_config was called with the correct configuration
        mock_save_config.assert_called_once()
        saved_config = mock_save_config.call_args[0][0]
        self.assertEqual(saved_config['ai_providers']['Ollama']['prompts']['Summarize'], new_summarize_prompt)
        self.assertEqual(saved_config['ai_providers']['Ollama']['prompts']['Explain'], 'Initial explain prompt') # Ensure others are unchanged

if __name__ == '__main__':
    unittest.main()
