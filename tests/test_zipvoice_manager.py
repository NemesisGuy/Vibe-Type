import os
import unittest
from pathlib import Path

from core.zipvoice_manager import (
    DEFAULT_SAMPLE_NAME,
    list_builtin_samples,
    resolve_prompt_from_config,
)


class ZipVoiceManagerTests(unittest.TestCase):
    def test_builtin_samples_have_assets(self):
        samples = list_builtin_samples()
        self.assertGreater(len(samples), 0, "ZipVoice samples should include at least one entry")
        for sample in samples:
            self.assertTrue(os.path.isfile(sample.wav_path), f"Missing wav file for sample {sample.name}")
            self.assertIsNotNone(sample.text_path, f"Sample {sample.name} should have a transcript path")
            if sample.text_path:
                self.assertTrue(os.path.isfile(sample.text_path), f"Missing transcript for sample {sample.name}")

    def test_resolve_prompt_returns_text(self):
        prompt = resolve_prompt_from_config({'sample_name': DEFAULT_SAMPLE_NAME})
        self.assertTrue(os.path.isfile(prompt.wav_path))
        self.assertTrue(prompt.prompt_text.strip())

    def test_resolve_prompt_unknown_sample_falls_back(self):
        fallback_prompt = resolve_prompt_from_config({'sample_name': 'does_not_exist'})
        default_prompt = resolve_prompt_from_config({'sample_name': DEFAULT_SAMPLE_NAME})
        self.assertTrue(fallback_prompt.prompt_text.strip())
        self.assertTrue(Path(fallback_prompt.wav_path).is_file())
        self.assertEqual(Path(fallback_prompt.wav_path).suffix.lower(), '.wav')
        self.assertNotEqual(fallback_prompt.prompt_text, "")
        self.assertEqual(Path(fallback_prompt.wav_path).suffix, Path(default_prompt.wav_path).suffix)


if __name__ == '__main__':
    unittest.main()
