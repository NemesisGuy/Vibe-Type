"""Helpers for discovering and loading ZipVoice voice cloning prompts."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.utils import get_resource_path

logger = logging.getLogger(__name__)

SAMPLES_RELATIVE_PATH = os.path.join("zipvoice_tts", "samples")
DEFAULT_SAMPLE_NAME = "optimus_3s"


@dataclass(frozen=True)
class ZipVoiceSample:
    """Metadata for a built-in ZipVoice prompt sample."""

    name: str
    wav_path: str
    text_path: Optional[str]
    display_name: str


@dataclass(frozen=True)
class ZipVoicePrompt:
    """Resolved prompt assets for preparing a ZipVoice session."""

    wav_path: str
    prompt_text: str


def _samples_directory() -> Path:
    return Path(get_resource_path(SAMPLES_RELATIVE_PATH))


def list_builtin_samples() -> List[ZipVoiceSample]:
    """Enumerate bundled ZipVoice samples that ship with VibeType."""

    samples_dir = _samples_directory()
    if not samples_dir.is_dir():
        logger.warning("ZipVoice samples directory does not exist: %s", samples_dir)
        return []

    samples: List[ZipVoiceSample] = []
    for wav_path in sorted(samples_dir.glob("*.wav")):
        text_path = wav_path.with_suffix(".txt")
        if not text_path.is_file():
            logger.debug("Skipping sample without transcript: %s", wav_path)
            continue
        name = wav_path.stem
        display_name = name.replace("_", " ").title()
        samples.append(
            ZipVoiceSample(
                name=name,
                wav_path=str(wav_path),
                text_path=str(text_path),
                display_name=display_name,
            )
        )
    return samples


def get_samples_map() -> Dict[str, ZipVoiceSample]:
    """Return a mapping of sample name -> metadata."""

    return {sample.name: sample for sample in list_builtin_samples()}


def _read_prompt_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Prompt transcript not found: {path}") from exc
    if not text:
        logger.warning("Prompt transcript %s is empty; using filename as fallback text.", path)
        text = path.stem.replace("_", " ")
    return text


def _normalise_path(value: Optional[str]) -> Optional[Path]:
    if not value:
        return None
    expanded = Path(os.path.expanduser(value))
    if not expanded.is_absolute():
        expanded = Path(get_resource_path(value))
    return expanded


def resolve_prompt_from_config(config: Mapping[str, Any]) -> ZipVoicePrompt:
    """Resolve the prompt assets according to the ZipVoice config block."""

    custom_wav_path = _normalise_path(config.get("custom_prompt_wav"))
    custom_text_path = _normalise_path(config.get("custom_prompt_text_path"))
    custom_text_value = (config.get("custom_prompt_text") or "").strip()

    if custom_wav_path:
        if not custom_wav_path.is_file():
            raise FileNotFoundError(f"Custom prompt wav not found: {custom_wav_path}")
        if custom_text_path:
            prompt_text = _read_prompt_text(custom_text_path)
        elif custom_text_value:
            prompt_text = custom_text_value
        else:
            inferred = custom_wav_path.with_suffix(".txt")
            if inferred.is_file():
                prompt_text = _read_prompt_text(inferred)
            else:
                raise ValueError(
                    "Custom prompt requires either 'custom_prompt_text_path' or 'custom_prompt_text'."
                )
        return ZipVoicePrompt(wav_path=str(custom_wav_path), prompt_text=prompt_text)

    samples_map = get_samples_map()
    sample_name = (config.get("sample_name") or DEFAULT_SAMPLE_NAME).strip()
    sample = samples_map.get(sample_name) or next(iter(samples_map.values()), None)
    if sample is None:
        raise FileNotFoundError("No ZipVoice samples with transcripts are available.")
    if sample_name not in samples_map:
        logger.warning("ZipVoice sample '%s' not found. Falling back to '%s'.", sample_name, sample.name)
    assert sample.text_path is not None
    prompt_text = _read_prompt_text(Path(sample.text_path))
    return ZipVoicePrompt(wav_path=sample.wav_path, prompt_text=prompt_text)


def open_zipvoice_samples_folder() -> bool:
    """Open the samples folder in the platform file browser."""

    samples_dir = _samples_directory()
    samples_dir.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(samples_dir))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(samples_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", str(samples_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        logger.error("Failed to open ZipVoice samples directory: %s", exc)
        return False
    return True


def sample_display_names() -> Sequence[str]:
    return [sample.display_name for sample in list_builtin_samples()]


__all__ = [
    "DEFAULT_SAMPLE_NAME",
    "ZipVoicePrompt",
    "ZipVoiceSample",
    "get_samples_map",
    "list_builtin_samples",
    "open_zipvoice_samples_folder",
    "resolve_prompt_from_config",
    "sample_display_names",
]
