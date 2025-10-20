"""Helpers for discovering and loading ZipVoice voice cloning prompts."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional, Sequence, Union

from core.utils import get_resource_path

import torch

if TYPE_CHECKING:  # pragma: no cover - typing only
    from zipvoice_tts.session import ZipVoiceStreamingSession

logger = logging.getLogger(__name__)

SAMPLES_RELATIVE_PATH = os.path.join("zipvoice_tts", "samples")
PROFILES_RELATIVE_PATH = os.path.join("zipvoice_tts", "profiles")
DEFAULT_SAMPLE_NAME = "optimus_3s"
_MODEL_SUFFIX_MAP = {
    "zipvoice": "_base",
    "zipvoice_distill": "_distilled",
}
_LEGACY_SUFFIXES = {
    "zipvoice_distill": ["_distill"],
}


def _normalize_model_name(model_name: Optional[str]) -> Optional[str]:
    if not model_name:
        return None
    normalized = model_name.strip().lower()
    return normalized or None


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

    wav_path: Optional[str]
    prompt_text: str
    profile_path: Optional[str] = None
    profile_metadata: Optional[Mapping[str, Any]] = None


def _samples_directory() -> Path:
    return Path(get_resource_path(SAMPLES_RELATIVE_PATH))


def ensure_samples_directory() -> Path:
    """Make sure the ZipVoice samples directory exists and return it."""

    directory = _samples_directory()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _profiles_directory() -> Path:
    return Path(get_resource_path(PROFILES_RELATIVE_PATH))


def ensure_profiles_directory() -> Path:
    directory = _profiles_directory()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def open_zipvoice_profiles_folder() -> bool:
    """Open the persisted ZipVoice profiles directory in the file browser."""

    profiles_dir = ensure_profiles_directory()
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(profiles_dir))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(profiles_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["xdg-open", str(profiles_dir)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        logger.error("Failed to open ZipVoice profiles directory: %s", exc)
        return False
    return True


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


def _load_profile_metadata(path: Path) -> Dict[str, Any]:
    try:
        payload = torch.load(path, map_location="cpu")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Voice profile not found: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid ZipVoice profile format: {path}")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    prompt_text = payload.get("prompt_text") or ""
    return {
        "prompt_text": prompt_text,
        "model_stamp": payload.get("model_stamp"),
        "params": payload.get("params"),
        "profile_version": payload.get("profile_version"),
        "metadata": metadata,
    }


def resolve_prompt_from_config(config: Mapping[str, Any]) -> ZipVoicePrompt:
    """Resolve the prompt assets according to the ZipVoice config block."""

    custom_profile_path = _normalise_path(config.get("custom_prompt_profile"))
    custom_wav_path = _normalise_path(config.get("custom_prompt_wav"))
    custom_text_path = _normalise_path(config.get("custom_prompt_text_path"))
    custom_text_value = (config.get("custom_prompt_text") or "").strip()

    if custom_profile_path:
        metadata = _load_profile_metadata(custom_profile_path)
        prompt_text = metadata.get("prompt_text") or custom_profile_path.stem.replace("_", " ")
        return ZipVoicePrompt(
            wav_path=None,
            prompt_text=prompt_text,
            profile_path=str(custom_profile_path),
            profile_metadata=metadata.get("metadata") or {},
        )

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


_PROFILE_FILENAME_PATTERN = re.compile(r"[^a-z0-9._-]+")


def _slugify(name: str) -> str:
    lowered = name.strip().lower()
    slug = _PROFILE_FILENAME_PATTERN.sub("-", lowered).strip("-")
    return slug or "profile"


def _all_suffixes_for_model(model_name: Optional[str]) -> List[str]:
    normalized = _normalize_model_name(model_name)
    if not normalized:
        return []
    suffixes: List[str] = []
    primary = _MODEL_SUFFIX_MAP.get(normalized)
    if primary:
        suffixes.append(primary)
    suffixes.extend(_LEGACY_SUFFIXES.get(normalized, []))
    if not suffixes:
        suffixes.append(f"_{_slugify(normalized)}")
    return suffixes


def _profile_suffix(model_name: Optional[str]) -> str:
    suffixes = _all_suffixes_for_model(model_name)
    return suffixes[0] if suffixes else ""


def profile_path_for_name(name: str, model_name: Optional[str] = None) -> Path:
    suffixes = _all_suffixes_for_model(model_name)
    resolved_name = name.strip()
    if suffixes and not any(resolved_name.endswith(sfx) for sfx in suffixes):
        resolved_name = f"{resolved_name}{suffixes[0]}"
    slug = _slugify(resolved_name)
    directory = ensure_profiles_directory()
    return directory / f"{slug}.pt"


def list_saved_profiles(model_name: Optional[str] = None) -> List[Dict[str, Any]]:
    directory = ensure_profiles_directory()
    profiles: List[Dict[str, Any]] = []
    model_filter = _normalize_model_name(model_name)
    for path in sorted(directory.glob("*.pt")):
        try:
            meta = _load_profile_metadata(path)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to read ZipVoice profile %s: %s", path.name, exc)
            continue
        metadata = meta.get("metadata") or {}
        profile_model = _normalize_model_name(metadata.get("model_name"))
        if model_filter and profile_model and profile_model != model_filter:
            continue
        if model_filter and profile_model is None:
            # Legacy profile without metadata: show only when no filter specified.
            continue
        profiles.append({
            "name": path.stem,
            "path": str(path),
            "prompt_text": meta.get("prompt_text", ""),
            "metadata": metadata,
            "model_name": profile_model,
        })
    return profiles


def load_voice_embedding(name_or_path: Union[str, Path]) -> Dict[str, Any]:
    """Load a saved ZipVoice voice profile payload for inspection."""

    candidate = Path(name_or_path)
    if not candidate.suffix:
        candidate = profile_path_for_name(candidate.name)
    if not candidate.exists():
        raise FileNotFoundError(f"Voice profile not found: {candidate}")

    data = torch.load(candidate, map_location="cpu")
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected ZipVoice profile format in {candidate}")
    data.setdefault("_path", str(candidate))
    return data


def delete_voice_profile(name_or_path: Union[str, Path]) -> bool:
    """Remove a saved voice profile; returns True if a file was deleted."""

    candidate = Path(name_or_path)
    candidates: List[Path] = []
    seen: set[Path] = set()
    if candidate.suffix:
        candidates.append(candidate)
    else:
        base_name = candidate.name
        path_no_suffix = profile_path_for_name(base_name)
        candidates.append(path_no_suffix)
        seen.add(path_no_suffix)
        for model_key in _MODEL_SUFFIX_MAP:
            candidate_path = profile_path_for_name(base_name, model_key)
            if candidate_path not in seen:
                candidates.append(candidate_path)
                seen.add(candidate_path)
            for suffix in _all_suffixes_for_model(model_key):
                if base_name.endswith(suffix):
                    combined_name = base_name
                else:
                    combined_name = f"{base_name}{suffix}"
                legacy_path = profile_path_for_name(combined_name)
                if legacy_path not in seen:
                    candidates.append(legacy_path)
                    seen.add(legacy_path)

    for path in candidates:
        if not path.exists():
            continue
        try:
            path.unlink()
            return True
        except OSError as exc:
            logger.error("Failed to delete ZipVoice profile %s: %s", path, exc)
            return False
    return False


def save_voice_profile(
    session: "ZipVoiceStreamingSession",
    name: str,
    metadata: Optional[Mapping[str, Any]] = None,
    overwrite: bool = True,
) -> Path:
    """Export the active ZipVoice prompt from a session into the profiles directory."""

    model_variant = _normalize_model_name(getattr(session, "params", {}).get("model_name")) if hasattr(session, "params") else None
    destination = profile_path_for_name(name, model_variant)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Voice profile already exists: {destination}")

    export_metadata = dict(metadata or {})
    if model_variant:
        export_metadata["model_name"] = model_variant
    session.export_prompt_profile(destination, metadata=export_metadata, overwrite=True)
    return destination


def save_voice_embedding(
    embedding_source: Union["ZipVoiceStreamingSession", Dict[str, Any]],
    name: str,
    metadata: Optional[Mapping[str, Any]] = None,
    overwrite: bool = True,
) -> Path:
    """Persist a ZipVoice voice embedding payload under a friendly *name*.

    Accepts either an active :class:`ZipVoiceStreamingSession` or a pre-built
    dictionary payload that mirrors the structure saved on disk. The helper is
    intentionally lightweight so experimental tools can persist embeddings
    without depending on the session class directly.
    """

    if TYPE_CHECKING:  # pragma: no cover - appease static analyzers
        from zipvoice_tts.session import ZipVoiceStreamingSession

    if hasattr(embedding_source, "export_prompt_profile"):
        session = embedding_source  # type: ignore[assignment]
        return save_voice_profile(session, name, metadata=metadata, overwrite=overwrite)

    if not isinstance(embedding_source, dict):
        raise TypeError("save_voice_embedding expects a ZipVoice session or a dict payload")

    payload = dict(embedding_source)
    payload.setdefault("metadata", {})
    if metadata:
        combined_meta = dict(payload.get("metadata") or {})
        combined_meta.update(metadata)
        payload["metadata"] = combined_meta

    model_variant = _normalize_model_name(payload.get("metadata", {}).get("model_name") or payload.get("model_name"))
    destination = profile_path_for_name(name, model_variant)
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Voice profile already exists: {destination}")

    if model_variant:
        payload["metadata"]["model_name"] = model_variant

    tmp_path = destination.with_suffix(".tmp")
    torch.save(payload, tmp_path)
    tmp_path.replace(destination)
    logger.info("Saved ZipVoice embedding -> %s", destination)
    return destination


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
    "PROFILES_RELATIVE_PATH",
    "ZipVoicePrompt",
    "ZipVoiceSample",
    "blend_voice_profiles",
    "ensure_samples_directory",
    "ensure_profiles_directory",
    "get_samples_map",
    "delete_voice_profile",
    "load_voice_embedding",
    "list_saved_profiles",
    "list_builtin_samples",
    "open_zipvoice_profiles_folder",
    "open_zipvoice_samples_folder",
    "profile_path_for_name",
    "resolve_prompt_from_config",
    "save_voice_embedding",
    "save_voice_profile",
    "sample_display_names",
]


def blend_voice_profiles(
    profile_paths: Sequence[Union[str, Path]],
    weights: Optional[Sequence[float]],
    name: str,
    metadata: Optional[Mapping[str, Any]] = None,
    overwrite: bool = False,
) -> Path:
    """Create a blended ZipVoice embedding from multiple saved profiles.

    The helper loads each profile, validates that they share the same model
    configuration, and computes a weighted average of the stored prompt
    features/RMS/duration before saving a new profile via
    :func:`save_voice_embedding`.
    """

    if len(profile_paths) < 2:
        raise ValueError("blend_voice_profiles requires at least two source profiles")

    resolved_paths = [Path(p) for p in profile_paths]
    source_names = [path.stem for path in resolved_paths]
    for path in resolved_paths:
        if not path.exists():
            raise FileNotFoundError(f"Voice profile not found: {path}")

    if weights is None:
        weight_tensor = torch.ones(len(resolved_paths), dtype=torch.float32)
    else:
        if len(weights) != len(resolved_paths):
            raise ValueError("weights length must match number of profiles")
        weight_tensor = torch.tensor(weights, dtype=torch.float32)

    if torch.all(weight_tensor == 0):
        raise ValueError("At least one weight must be non-zero")

    weight_tensor = weight_tensor / weight_tensor.sum()

    payloads: List[Dict[str, Any]] = []
    for path in resolved_paths:
        payload = torch.load(path, map_location="cpu")
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid ZipVoice profile format: {path}")
        payload["_path"] = str(path)
        payloads.append(payload)

    anchor_payload = payloads[int(torch.argmax(weight_tensor).item())]

    profile_version = anchor_payload.get("profile_version")
    model_stamp = anchor_payload.get("model_stamp")
    params = anchor_payload.get("params")
    if profile_version is None or model_stamp is None or params is None:
        raise ValueError("Anchor profile is missing required metadata")

    for payload in payloads:
        if payload.get("profile_version") != profile_version:
            raise ValueError("Cannot blend profiles with different profile versions")
        if payload.get("model_stamp") != model_stamp:
            raise ValueError("Cannot blend profiles created with different model checkpoints")
        if payload.get("params") != params:
            raise ValueError("Cannot blend profiles with differing runtime parameters")

    feature_tensors: List[torch.Tensor] = []
    durations: List[float] = []
    rms_values: List[float] = []
    normalised_model_name: Optional[str] = None
    source_metadata: List[Dict[str, Any]] = []

    for payload, weight in zip(payloads, weight_tensor.tolist()):
        features = payload.get("prompt_features")
        if features is None:
            raise ValueError("Profile is missing prompt_features")
        feature_tensor = features if isinstance(features, torch.Tensor) else torch.tensor(features)
        feature_tensor = feature_tensor.to(dtype=torch.float32)
        feature_tensors.append(feature_tensor)
        durations.append(float(payload.get("prompt_duration", 0.0)))
        rms_values.append(float(payload.get("prompt_rms", 0.0)))
        source_metadata.append({
            "path": payload.get("_path", ""),
            "weight": weight,
        })
        meta = payload.get("metadata") or {}
        candidate_model = _normalize_model_name(meta.get("model_name") or payload.get("model_name"))
        if candidate_model:
            if normalised_model_name and candidate_model != normalised_model_name:
                raise ValueError("Cannot blend profiles from different model variants")
            normalised_model_name = candidate_model

    base_leading_shape = feature_tensors[0].shape[:-2] if feature_tensors[0].ndim >= 2 else tuple()
    feature_dim = feature_tensors[0].shape[-1] if feature_tensors[0].ndim >= 1 else None
    seq_axis = (feature_tensors[0].ndim - 2) if feature_tensors[0].ndim >= 2 else (feature_tensors[0].ndim - 1)

    if feature_dim is None or feature_dim <= 0:
        raise ValueError("Profiles contain malformed prompt feature tensors")

    for tensor in feature_tensors:
        if tensor.ndim != feature_tensors[0].ndim:
            raise ValueError("Profiles have mismatched feature tensor ranks")
        if tensor.ndim >= 2 and tensor.shape[:-2] != base_leading_shape:
            raise ValueError("Profiles have incompatible batch/channel dimensions")
        if tensor.shape[-1] != feature_dim:
            raise ValueError("Profiles have differing feature vector sizes; blend profiles created on the same checkpoint")

    sequence_lengths = [tensor.shape[seq_axis] for tensor in feature_tensors]
    min_sequence = min(sequence_lengths)
    if min_sequence <= 0:
        raise ValueError("Profiles contain empty prompt feature sequences")

    if any(length != min_sequence for length in sequence_lengths):
        logger.debug(
            "ZipVoice blending crops sequences to %d (original lengths: %s)",
            min_sequence,
            sequence_lengths,
        )

    aligned = [torch.narrow(tensor, seq_axis, 0, min_sequence) for tensor in feature_tensors]
    stacked = torch.stack(aligned, dim=0)
    expanded_weights = weight_tensor.view(-1, *([1] * (stacked.ndim - 1)))
    blended_features = torch.sum(stacked * expanded_weights, dim=0)

    duration_factors = []
    for tensor, duration, original_length in zip(feature_tensors, durations, sequence_lengths):
        scale = min_sequence / original_length if original_length else 1.0
        duration_factors.append(duration * scale)
    blended_duration = float(sum(w * d for w, d in zip(weight_tensor.tolist(), duration_factors)))
    blended_rms = float(sum(w * r for w, r in zip(weight_tensor.tolist(), rms_values)))

    blended_payload = {
        key: value
        for key, value in anchor_payload.items()
        if key not in {"prompt_features", "prompt_rms", "prompt_duration", "metadata", "_path"}
    }
    blended_payload["prompt_features"] = blended_features.cpu()
    blended_payload["prompt_rms"] = blended_rms
    blended_payload["prompt_duration"] = blended_duration

    base_metadata = dict(anchor_payload.get("metadata") or {})
    base_metadata["blend_sources"] = source_metadata
    base_metadata.setdefault("source_sample", base_metadata.get("source_sample"))
    if normalised_model_name:
        base_metadata["model_name"] = normalised_model_name
    if metadata:
        extra_meta = dict(metadata)
        base_metadata.update(extra_meta)
    blended_payload["metadata"] = base_metadata

    blended_payload["prompt_text"] = "Blend: " + ", ".join(source_names)

    return save_voice_embedding(blended_payload, name, metadata=None, overwrite=overwrite)
