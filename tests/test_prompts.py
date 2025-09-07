import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk

# Mock the necessary modules before they are imported by the module we are testing
with patch.dict('sys.modules', {'core.config_manager': MagicMock(), 'core.tts': MagicMock(), 'core.ai': MagicMock(), 'core.model_manager': MagicMock(), 'core.transcript_saver': MagicMock(), 'core.analytics': MagicMock(), 'core.performance_monitor': MagicMock(), 'webbrowser': MagicMock()}):
    from gui.settings_window import create_settings_window

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
            if isinstance(widget, tk.Button) and widget.cget('text') == '✔️ Save':
                save_button = widget
            if isinstance(widget, tk.Text):
                # This is a bit of a hack to identify which text widget is which
                # In a real app, you'd want to give them names or some other identifier
                parent_tab_text = settings_window.nametowidget(widget.winfo_parent()).master.tab(settings_window.nametowidget(widget.winfo_parent()), "text")
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
