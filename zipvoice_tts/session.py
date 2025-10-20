"""ZipVoice streaming helpers.

Copy this module into another project when you want a ready-to-use ZipVoice
"warm" session. The only runtime requirements are the main :mod:`zipvoice`
package, Hugging Face access for automatic downloads, and PyTorch/ONNX Runtime
depending on the backend you select.

The session keeps either the ONNX export or the native PyTorch checkpoint
resident in memory together with the Vocos vocoder so that successive text
chunks can be synthesised with minimal latency. Both synchronous generators and
async queue based helpers are exposed, making integration with GUIs or network
services straightforward.

Example
-------
>>> session = ZipVoiceStreamingSession(backend="torch", torch_device="cuda")
>>> session.prepare_prompt("prompt.wav", "Prompt transcription")
>>> for chunk in session.synthesize_text("Hello world"):
...     play_audio(chunk.audio.numpy(), chunk.sample_rate)
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import importlib
import json
import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

import safetensors.torch
import torch
from torch import Tensor
import numpy as np

from huggingface_hub import hf_hub_download

try:
    from lhotse.utils import fix_random_seed
except Exception:  # pragma: no cover - optional dependency
    def fix_random_seed(seed: int) -> None:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

PROMPT_CACHE_VERSION = 1
VOICE_PROFILE_VERSION = 1

from .vendor import ensure_vendor_zipvoice

ensure_vendor_zipvoice()

from zipvoice.bin.infer_zipvoice import get_vocoder

try:  # Optional ONNX backend support
    from zipvoice.bin.infer_zipvoice_onnx import OnnxModel, sample as onnx_sample
    _ONNX_IMPORT_ERROR: Optional[BaseException] = None
except Exception as exc:  # pragma: no cover - allow environments without onnxruntime
    OnnxModel = None  # type: ignore[assignment]
    onnx_sample = None  # type: ignore[assignment]
    _ONNX_IMPORT_ERROR = exc
from zipvoice.models.zipvoice import ZipVoice
from zipvoice.models.zipvoice_distill import ZipVoiceDistill
from zipvoice.tokenizer.tokenizer import (
    EmiliaTokenizer,
    EspeakTokenizer,
    LibriTTSTokenizer,
    SimpleTokenizer,
)
from zipvoice.utils.common import AttributeDict
from zipvoice.utils.feature import VocosFbank
from zipvoice.utils.infer import (
    add_punctuation,
    chunk_tokens_punctuation,
    load_prompt_wav,
    remove_silence,
    rms_norm,
)
from zipvoice.utils.checkpoint import load_checkpoint

logger = logging.getLogger(__name__)

HUGGINGFACE_REPO = "k2-fsa/ZipVoice"
# Map model variants to their Hugging Face subdirectories.
MODEL_DIR = {
    "zipvoice": "zipvoice",
    "zipvoice_distill": "zipvoice_distill",
}
MODEL_DEFAULTS: Dict[str, Dict[str, float]] = {
    "zipvoice": {"num_step": 16, "guidance_scale": 1.0},
    "zipvoice_distill": {"num_step": 8, "guidance_scale": 3.0},
}


@dataclass
class AudioChunk:
    """Represents a single chunk of streamed audio."""

    audio: Tensor
    sample_rate: int
    text: str
    inference_seconds: float
    total_elapsed_seconds: float


class ZipVoiceStreamingSession:
    """Keep a ZipVoice (ONNX or PyTorch) + Vocos pipeline warm for streaming use."""

    def __init__(
        self,
        *,
        model_name: str = "zipvoice",
        onnx_int8: bool = False,
        model_dir: Optional[str] = None,
        vocoder_path: Optional[str] = None,
        tokenizer: str = "emilia",
        lang: str = "en-us",
        providers: Optional[Sequence[str]] = None,
        backend: str = "onnx",
        torch_checkpoint: Optional[str] = None,
        torch_device: Optional[str] = None,
        vocoder_device: str = "cpu",
        feat_scale: float = 0.1,
        speed: float = 1.0,
        t_shift: float = 1.0,
        target_rms: float = 0.1,
        num_step: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        remove_long_sil: bool = False,
        prompt_trim_edge_silence: bool = True,
        max_total_seconds: float = 25.0,
        num_thread: int = 6,
        seed: Optional[int] = None,
    ) -> None:
        # Collect runtime configuration in an attribute-friendly mapping.
        self.params = AttributeDict()
        self.params.model_name = model_name
        self.params.onnx_int8 = onnx_int8
        self.params.model_dir = Path(model_dir) if model_dir else None
        self.params.vocoder_path = vocoder_path
        self.params.tokenizer = tokenizer
        self.params.lang = lang
        self.params.providers = list(providers) if providers else None
        # Normalise backend selection so downstream logic can branch cleanly.
        backend = backend.lower()
        if backend not in {"onnx", "torch"}:
            raise ValueError("backend must be 'onnx' or 'torch'")
        self.params.backend = backend
        self.params.torch_checkpoint = torch_checkpoint
        self.params.torch_device = torch_device
        self.torch_device: Optional[torch.device] = None
        if backend == "torch":
            # Respect caller's explicit device, otherwise auto-pick a sensible default.
            if torch_device is not None:
                self.torch_device = torch.device(torch_device)
            else:
                if torch.cuda.is_available():
                    self.torch_device = torch.device("cuda", 0)
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.torch_device = torch.device("mps")
                else:
                    self.torch_device = torch.device("cpu")
            assert self.torch_device is not None
            if self.torch_device.type == "cuda" and not torch.cuda.is_available():
                raise ValueError(
                    "CUDA torch backend requested but torch.cuda.is_available() is False."
                )
            if (
                self.torch_device.type == "mps"
                and not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
            ):
                raise ValueError(
                    "MPS torch backend requested but torch.backends.mps.is_available() is False."
                )
        elif torch_device is not None:
            logger.warning("torch_device argument ignored because backend='onnx'")
        self.vocoder_device = torch.device(vocoder_device)
        if self.vocoder_device.type == "cuda" and not torch.cuda.is_available():
            raise ValueError(
                "CUDA vocoder requested but torch.cuda.is_available() is False."
            )
        self.params.feat_scale = feat_scale
        self.params.speed = speed
        self.params.t_shift = t_shift
        self.params.target_rms = target_rms
        self.params.remove_long_sil = remove_long_sil
        self.params.prompt_trim_edge_silence = prompt_trim_edge_silence
        self.params.max_total_seconds = max_total_seconds
        self.params.num_thread = num_thread
        self.params.seed = int(seed) if isinstance(seed, int) else None

        defaults = MODEL_DEFAULTS.get(model_name, {})
        self.params.num_step = num_step or defaults.get("num_step") or 16
        self.params.guidance_scale = (
            guidance_scale if guidance_scale is not None else defaults.get("guidance_scale", 1.0)
        )

        self._onnx_sample = None
        if self.params.backend == "onnx":
            if OnnxModel is None or onnx_sample is None:
                details = "" if _ONNX_IMPORT_ERROR is None else f" ({_ONNX_IMPORT_ERROR})"
                raise RuntimeError(
                    "ZipVoice ONNX backend requested but onnxruntime is not available. "
                    "Install onnxruntime-gpu (or onnxruntime) compiled for your NumPy version, or switch backend='torch'."
                    + details
                )
            (
                self.text_encoder_path,
                self.fm_decoder_path,
                self.model_config_path,
                token_file,
            ) = self._resolve_onnx_paths()
            self.torch_checkpoint_path: Optional[Path] = None
            self._onnx_sample = onnx_sample
        else:
            (
                self.torch_checkpoint_path,
                self.model_config_path,
                token_file,
            ) = self._resolve_torch_assets()
            self.text_encoder_path = None
            self.fm_decoder_path = None
            self._onnx_sample = None

        self.tokenizer = self._build_tokenizer(token_file)
        self.model_config = self._load_config(self.model_config_path)
        self.sampling_rate = self.model_config["feature"]["sampling_rate"]
        self._model_config_stamp = self._build_path_stamp(self.model_config_path)
        self._prompt_cache_root = self._initialise_prompt_cache_dir()
        if self.params.backend == "onnx":
            assert self.text_encoder_path is not None
            assert self.fm_decoder_path is not None
            try:
                self.model = OnnxModel(
                    str(self.text_encoder_path),
                    str(self.fm_decoder_path),
                    num_thread=num_thread,
                    providers=self.params.providers,
                )
            except Exception as exc:  # pragma: no cover - bubble up with guidance
                if "Numpy is not available" in str(exc):
                    numpy_version = getattr(np, "__version__", "unknown")
                    raise RuntimeError(
                        "ONNX Runtime failed to initialize because it was built against NumPy 1.x. "
                        f"Detected NumPy {numpy_version}. Install `numpy<2` and reinstall onnxruntime/torchaudio, or upgrade to an \n"
                        "onnxruntime build compiled for NumPy 2.x."
                    ) from exc
                raise
        else:
            try:
                torch.set_num_threads(num_thread)
            except RuntimeError as exc:
                logger.warning("Unable to set torch threads: %s", exc)
            if hasattr(torch, "set_num_interop_threads"):
                try:
                    torch.set_num_interop_threads(num_thread)
                except RuntimeError as exc:
                    logger.warning("Unable to set torch interop threads: %s", exc)
            self.model = self._load_torch_model()

        # Load the Vocos vocoder once so subsequent chunks decode without disk I/O.
        self.vocoder = get_vocoder(self.params.vocoder_path)
        self.vocoder.to(self.vocoder_device)
        self.vocoder.eval()

        if self.model_config["feature"]["type"] != "vocos":
            raise NotImplementedError(
                f"Unsupported feature type: {self.model_config['feature']['type']}"
            )
        self.feature_extractor = VocosFbank()

        self.prompt_tokens: Optional[List[List[int]]] = None
        self.prompt_tokens_str: Optional[Sequence[str]] = None
        self.prompt_features: Optional[Tensor] = None
        self.prompt_rms: Optional[float] = None
        self.prompt_text: Optional[str] = None
        self.prompt_duration: Optional[float] = None
        self._seed_counter: int = 0

        self._text_queue: Optional[asyncio.Queue[str]] = None

        logger.info(
            "Initialised ZipVoice streaming session with backend=%s | vocoder_device=%s",
            self.params.backend,
            self.vocoder_device,
        )
        if self.params.backend == "torch":
            logger.info(
                "Torch checkpoint=%s | model_device=%s",
                self.torch_checkpoint_path,
                self.torch_device,
            )
        else:
            logger.info("ONNX providers=%s", self.params.providers or "default")

    # ------------------------------------------------------------------
    # Initialisation helpers
    # ------------------------------------------------------------------
    def _resolve_onnx_paths(self) -> Sequence[Path]:
        if self.params.onnx_int8:
            text_encoder_name = "text_encoder_int8.onnx"
            fm_decoder_name = "fm_decoder_int8.onnx"
        else:
            text_encoder_name = "text_encoder.onnx"
            fm_decoder_name = "fm_decoder.onnx"

        if self.params.model_dir is not None:
            model_dir = self.params.model_dir
            if not model_dir.is_dir():
                raise FileNotFoundError(f"Model directory {model_dir} does not exist")

            required = [text_encoder_name, fm_decoder_name, "model.json", "tokens.txt"]
            for filename in required:
                path = model_dir / filename
                if not path.is_file():
                    raise FileNotFoundError(f"Missing file {path}")

            return (
                model_dir / text_encoder_name,
                model_dir / fm_decoder_name,
                model_dir / "model.json",
                model_dir / "tokens.txt",
            )

        repo_subdir = MODEL_DIR[self.params.model_name]
        text_encoder_path = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/{text_encoder_name}")
        )
        fm_decoder_path = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/{fm_decoder_name}")
        )
        config_path = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/model.json")
        )
        token_file = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/tokens.txt")
        )
        return text_encoder_path, fm_decoder_path, config_path, token_file

    def _resolve_torch_assets(self) -> Tuple[Path, Path, Path]:
        # Optional direct path to a checkpoint overrides model_dir/HF resolution.
        checkpoint_override = self.params.torch_checkpoint
        if checkpoint_override is not None:
            override_path = Path(checkpoint_override)
            if override_path.is_file():
                config_path = override_path.parent / "model.json"
                token_file = override_path.parent / "tokens.txt"
                for path in (config_path, token_file):
                    if not path.is_file():
                        raise FileNotFoundError(f"Missing required file {path} for torch backend")
                return override_path, config_path, token_file
            if override_path.is_absolute():
                raise FileNotFoundError(f"Torch checkpoint {override_path} does not exist")

        if self.params.model_dir is not None:
            model_dir = self.params.model_dir
            if not model_dir.is_dir():
                raise FileNotFoundError(f"Model directory {model_dir} does not exist")

            config_path = model_dir / "model.json"
            token_file = model_dir / "tokens.txt"
            for path in (config_path, token_file):
                if not path.is_file():
                    raise FileNotFoundError(f"Missing file {path}")

            if checkpoint_override:
                ckpt_path = model_dir / checkpoint_override
                if not ckpt_path.is_file():
                    raise FileNotFoundError(f"Torch checkpoint {ckpt_path} does not exist")
            else:
                candidates = ["model.safetensors", "model.pt"]
                ckpt_path = None
                for candidate in candidates:
                    candidate_path = model_dir / candidate
                    if candidate_path.is_file():
                        ckpt_path = candidate_path
                        break
                if ckpt_path is None:
                    raise FileNotFoundError(
                        f"No torch checkpoint found in {model_dir}. Expected one of {candidates}"
                    )
            return ckpt_path, config_path, token_file

        # Fall back to downloading the official pretrained asset bundle.
        repo_subdir = MODEL_DIR[self.params.model_name]
        ckpt_filename = checkpoint_override or "model.pt"
        ckpt_path = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/{ckpt_filename}")
        )
        config_path = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/model.json")
        )
        token_file = Path(
            hf_hub_download(HUGGINGFACE_REPO, filename=f"{repo_subdir}/tokens.txt")
        )
        return ckpt_path, config_path, token_file

    def _load_torch_model(self) -> torch.nn.Module:
        if self.torch_checkpoint_path is None:
            raise RuntimeError("Torch backend selected but checkpoint path was not resolved")
        if self.torch_device is None:
            raise RuntimeError("Torch backend selected but torch_device is not initialised")

        # Align tokenizer metadata with the Torch model constructor.
        tokenizer_config = {"vocab_size": self.tokenizer.vocab_size, "pad_id": self.tokenizer.pad_id}
        if self.params.model_name == "zipvoice":
            model = ZipVoice(
                **self.model_config["model"],
                **tokenizer_config,
            )
        elif self.params.model_name == "zipvoice_distill":
            model = ZipVoiceDistill(
                **self.model_config["model"],
                **tokenizer_config,
            )
        else:
            raise ValueError(f"Unsupported model_name {self.params.model_name}")

        ckpt_path = self.torch_checkpoint_path
        if str(ckpt_path).endswith(".safetensors"):
            safetensors.torch.load_model(model, str(ckpt_path))
        elif str(ckpt_path).endswith(".pt") or str(ckpt_path).endswith(".ckpt"):
            load_checkpoint(filename=ckpt_path, model=model, strict=True)
        else:
            raise NotImplementedError(
                f"Unsupported torch checkpoint format: {ckpt_path}. Expected .pt, .ckpt, or .safetensors"
            )

        model = model.to(self.torch_device)
        model.eval()
        return model

    def _build_tokenizer(self, token_file: Path):
        tok = self.params.tokenizer
        if tok == "emilia":
            return EmiliaTokenizer(token_file=token_file)
        if tok == "libritts":
            return LibriTTSTokenizer(token_file=token_file)
        if tok == "espeak":
            return EspeakTokenizer(token_file=token_file, lang=self.params.lang)
        if tok == "simple":
            return SimpleTokenizer(token_file=token_file)
        raise ValueError(f"Unknown tokenizer type: {tok}")

    def _load_config(self, config_path: Path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _apply_prompt_cache(self, cache: Dict[str, Any]) -> None:
        prompt_features = cache["prompt_features"]
        if not isinstance(prompt_features, torch.Tensor):
            prompt_features = torch.tensor(prompt_features, dtype=torch.float32)
        else:
            prompt_features = prompt_features.detach().clone().to(dtype=torch.float32)
        self.prompt_features = prompt_features
        self.prompt_tokens = cache["prompt_tokens"]
        self.prompt_tokens_str = cache["prompt_tokens_str"]
        self.prompt_rms = float(cache["prompt_rms"])
        self.prompt_text = cache["prompt_text"]
        self.prompt_duration = float(cache["prompt_duration"])
        self._reset_seed_counter()

    def _current_prompt_cache_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "model_name": self.params.model_name,
            "backend": self.params.backend,
            "onnx_int8": bool(self.params.onnx_int8),
            "feat_scale": float(self.params.feat_scale),
            "tokenizer": self.params.tokenizer,
            "sampling_rate": int(self.sampling_rate),
        }
        if self.params.model_dir is not None:
            params["model_dir_stamp"] = self._build_path_stamp(self.params.model_dir)
        return params

    def _initialise_prompt_cache_dir(self) -> Optional[Path]:
        cache_root = Path(os.path.expanduser("~")) / ".VibeType" / "cache" / "zipvoice_prompts"
        try:
            cache_root.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - cache failures are non-fatal
            logger.debug("ZipVoice prompt cache disabled; could not create %s: %s", cache_root, exc)
            return None
        return cache_root

    @staticmethod
    def _build_path_stamp(path: Optional[Path]) -> str:
        if path is None:
            return ""
        resolved = Path(path).resolve()
        try:
            stat = resolved.stat()
            mtime = getattr(stat, "st_mtime_ns", None)
            if mtime is None:
                mtime = int(stat.st_mtime * 1_000_000_000)
            return f"{resolved}|{mtime}|{stat.st_size}"
        except OSError:
            return str(resolved)

    def _reset_seed_counter(self) -> None:
        self._seed_counter = 0

    def _apply_inference_seed(self, offset: int) -> None:
        base_seed = self.params.seed
        if base_seed is None:
            return
        seed_value = int(base_seed + offset) & 0xFFFFFFFF
        fix_random_seed(seed_value)
        random.seed(seed_value)
        np.random.seed(seed_value)

    @staticmethod
    def _prompt_text_hash(prompt_text: str) -> str:
        return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    def _make_prompt_cache_key(self, prompt_wav: str, prompt_text: str) -> Tuple[str, Dict[str, Any]]:
        wav_path = Path(prompt_wav)
        wav_signature = self._build_path_stamp(wav_path)
        params = self._current_prompt_cache_params()
        descriptor = {
            "version": PROMPT_CACHE_VERSION,
            "wav_signature": wav_signature,
            "prompt_text_hash": self._prompt_text_hash(prompt_text),
            "model_stamp": self._model_config_stamp,
            "params": params,
        }
        payload = json.dumps(descriptor, sort_keys=True).encode("utf-8")
        cache_key = hashlib.sha256(payload).hexdigest()
        return cache_key, descriptor

    def _load_prompt_cache(self, cache_path: Path, descriptor: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not cache_path.is_file():
            return None
        try:
            data = torch.load(cache_path, map_location="cpu")
        except Exception as exc:  # pragma: no cover - cache is optional
            logger.debug("Failed to read ZipVoice prompt cache %s: %s", cache_path, exc)
            return None

        if not isinstance(data, dict):
            return None
        if data.get("version") != PROMPT_CACHE_VERSION:
            return None
        if data.get("model_stamp") != self._model_config_stamp:
            return None
        if data.get("wav_signature") != descriptor.get("wav_signature"):
            return None
        if data.get("prompt_text_hash") != descriptor.get("prompt_text_hash"):
            return None

        params = data.get("params")
        if not isinstance(params, dict):
            return None
        if params != self._current_prompt_cache_params():
            return None

        required_keys = {
            "prompt_features",
            "prompt_tokens",
            "prompt_tokens_str",
            "prompt_rms",
            "prompt_text",
            "prompt_duration",
        }
        if not required_keys.issubset(data.keys()):
            return None

        return data

    def _save_prompt_cache(self, cache_path: Path, payload: Dict[str, Any]) -> None:
        tmp_path = cache_path.with_suffix(".tmp")
        try:
            torch.save(payload, tmp_path)
            tmp_path.replace(cache_path)
            logger.debug("Saved ZipVoice prompt cache %s", cache_path.name)
        except Exception as exc:  # pragma: no cover - cache writes are best-effort
            logger.debug("Failed to write ZipVoice prompt cache %s: %s", cache_path, exc)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # Prompt preparation
    # ------------------------------------------------------------------
    def prepare_prompt(self, prompt_wav: str, prompt_text: str) -> None:
        """Load and cache prompt features for subsequent streaming."""

        prompt_text = add_punctuation(prompt_text)

        cache_path: Optional[Path] = None
        cache_descriptor: Optional[Dict[str, Any]] = None
        if self._prompt_cache_root is not None:
            try:
                cache_key, cache_descriptor = self._make_prompt_cache_key(prompt_wav, prompt_text)
                cache_path = self._prompt_cache_root / f"{cache_key}.pt"
                cached = self._load_prompt_cache(cache_path, cache_descriptor)
                if cached:
                    self._apply_prompt_cache(cached)
                    logger.info(
                        "Loaded cached ZipVoice prompt embedding (%s)", cache_path.name
                    )
                    return
            except Exception as exc:  # pragma: no cover - cache failures are non-fatal
                logger.debug("ZipVoice prompt cache unavailable: %s", exc, exc_info=True)
                cache_path = None
                cache_descriptor = None

        wav = load_prompt_wav(prompt_wav, sampling_rate=self.sampling_rate)
        if self.params.prompt_trim_edge_silence:
            wav = remove_silence(wav, self.sampling_rate, only_edge=False, trail_sil=200)

        wav, prompt_rms = rms_norm(wav, self.params.target_rms)
        prompt_duration = wav.shape[-1] / self.sampling_rate

        if prompt_duration > 20:
            logger.warning(
                "Prompt audio is %.1fs which is quite long; consider a 1-3s prompt for best quality.",
                prompt_duration,
            )
        elif prompt_duration > 10:
            logger.info(
                "Prompt audio is %.1fs. Longer prompts increase inference latency.",
                prompt_duration,
            )

        features = self.feature_extractor.extract(wav, sampling_rate=self.sampling_rate)
        features = features.unsqueeze(0) * self.params.feat_scale

        prompt_tokens = self.tokenizer.texts_to_tokens([prompt_text])[0]
        prompt_token_ids = self.tokenizer.tokens_to_token_ids([prompt_tokens])

        self.prompt_tokens = prompt_token_ids
        self.prompt_tokens_str = prompt_tokens
        self.prompt_features = features
        self.prompt_rms = float(prompt_rms)
        self.prompt_text = prompt_text
        self.prompt_duration = prompt_duration
        self._reset_seed_counter()

        if cache_path and cache_descriptor:
            payload = {
                "version": PROMPT_CACHE_VERSION,
                "model_stamp": self._model_config_stamp,
                "params": self._current_prompt_cache_params(),
                "prompt_text_hash": cache_descriptor["prompt_text_hash"],
                "prompt_text": prompt_text,
                "prompt_features": self.prompt_features.detach().cpu(),
                "prompt_tokens": self.prompt_tokens,
                "prompt_tokens_str": self.prompt_tokens_str,
                "prompt_rms": self.prompt_rms,
                "prompt_duration": self.prompt_duration,
                "wav_signature": cache_descriptor["wav_signature"],
            }
            self._save_prompt_cache(cache_path, payload)

    # ------------------------------------------------------------------
    # Voice profile persistence
    # ------------------------------------------------------------------
    def export_prompt_profile(
        self,
        destination: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = True,
    ) -> Path:
        """Persist the currently prepared prompt as a reusable voice profile."""

        self._ensure_prompt_ready()

        dest_path = Path(destination)
        if dest_path.exists() and not overwrite:
            raise FileExistsError(f"Profile already exists: {dest_path}")
        if dest_path.suffix.lower() != ".pt":
            dest_path = dest_path.with_suffix(".pt")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        payload: Dict[str, Any] = {
            "profile_version": VOICE_PROFILE_VERSION,
            "model_stamp": self._model_config_stamp,
            "params": self._current_prompt_cache_params(),
            "prompt_text": self.prompt_text,
            "prompt_features": self.prompt_features.detach().cpu(),
            "prompt_tokens": self.prompt_tokens,
            "prompt_tokens_str": self.prompt_tokens_str,
            "prompt_rms": self.prompt_rms,
            "prompt_duration": self.prompt_duration,
            "metadata": metadata or {},
        }

        tmp_path = dest_path.with_suffix(".tmp")
        torch.save(payload, tmp_path)
        tmp_path.replace(dest_path)
        logger.info("Saved ZipVoice voice profile -> %s", dest_path)
        return dest_path

    def load_prompt_profile(self, profile: Union[str, Path]) -> Dict[str, Any]:
        """Load a previously exported voice profile and activate it."""

        profile_path = Path(profile)
        if not profile_path.is_file():
            raise FileNotFoundError(f"Voice profile not found: {profile_path}")

        data = torch.load(profile_path, map_location="cpu")
        if not isinstance(data, dict):
            raise ValueError(f"Invalid ZipVoice profile format: {profile_path}")

        version = data.get("profile_version")
        if version != VOICE_PROFILE_VERSION:
            raise ValueError(
                f"Profile {profile_path} has version {version}; expected {VOICE_PROFILE_VERSION}."
            )

        if data.get("model_stamp") != self._model_config_stamp:
            raise ValueError(
                "Voice profile was created with a different ZipVoice model configuration. "
                "Recreate the profile using the current model weights."
            )

        params = data.get("params")
        if params != self._current_prompt_cache_params():
            raise ValueError(
                "Voice profile parameters do not match current session settings (backend/providers)."
            )

        required = {
            "prompt_features",
            "prompt_tokens",
            "prompt_tokens_str",
            "prompt_rms",
            "prompt_duration",
            "prompt_text",
        }
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Voice profile missing required fields: {missing}")

        self._apply_prompt_cache(data)
        logger.info("Loaded ZipVoice voice profile <- %s", profile_path)
        metadata = data.get("metadata")
        return metadata if isinstance(metadata, dict) else {}

    # ------------------------------------------------------------------
    # Core streaming helpers
    # ------------------------------------------------------------------
    def _ensure_prompt_ready(self) -> None:
        if self.prompt_tokens is None or self.prompt_features is None:
            raise RuntimeError("Prompt not initialised. Call prepare_prompt(...) first.")

    def _chunk_text(self, text: str) -> Sequence[Sequence[str]]:
        text = add_punctuation(text)
        tokens_str = self.tokenizer.texts_to_tokens([text])[0]

        prompt_token_count = len(getattr(self, "prompt_tokens_str", [])) or 1
        prompt_duration = self.prompt_duration or 3.0
    # Use the prompt to estimate a per-token duration and cap chunk length.
        token_duration = (prompt_duration / (prompt_token_count * self.params.speed))
        max_tokens = max(1, int((self.params.max_total_seconds - prompt_duration) / token_duration))
        return chunk_tokens_punctuation(tokens_str, max_tokens=max_tokens)

    def _synthesise_chunk(self, token_ids: List[int]) -> Tensor:
        assert self.prompt_tokens is not None
        assert self.prompt_features is not None

        if self.params.backend == "onnx":
            # Use the ONNX Runtime sampler on the exported text encoder + decoder pair.
            if self._onnx_sample is None:
                raise RuntimeError(
                    "ZipVoice ONNX backend is unavailable in this environment. Switch backend='torch'."
                )
            pred_features = self._onnx_sample(
                model=self.model,
                tokens=[token_ids],
                prompt_tokens=self.prompt_tokens,
                prompt_features=self.prompt_features,
                speed=self.params.speed,
                t_shift=self.params.t_shift,
                guidance_scale=self.params.guidance_scale,
                num_step=self.params.num_step,
            )
        else:
            # Native PyTorch path mirrors the CLI by calling model.sample().
            assert self.torch_device is not None
            batch_tokens = [token_ids]
            prompt_tokens = self.prompt_tokens
            if len(prompt_tokens) != len(batch_tokens):
                prompt_tokens = prompt_tokens * len(batch_tokens)

            prompt_features = self.prompt_features.to(self.torch_device)
            batch_prompt_features = prompt_features.repeat(len(batch_tokens), 1, 1)
            prompt_features_lens = torch.full(
                (len(batch_tokens),),
                prompt_features.size(1),
                device=self.torch_device,
                dtype=torch.long,
            )

            with torch.inference_mode():
                (
                    pred_features,
                    pred_features_lens,
                    _,
                    _,
                ) = self.model.sample(
                    tokens=batch_tokens,
                    prompt_tokens=prompt_tokens,
                    prompt_features=batch_prompt_features,
                    prompt_features_lens=prompt_features_lens,
                    speed=self.params.speed,
                    t_shift=self.params.t_shift,
                    duration="predict",
                    num_step=self.params.num_step,
                    guidance_scale=self.params.guidance_scale,
                )

            pred_len = int(pred_features_lens[0])
            pred_features = pred_features[:, :pred_len, :]

        # Restore feature orientation and undo the training-time scaling factor.
        pred_features = pred_features.permute(0, 2, 1) / self.params.feat_scale
        if pred_features.device != self.vocoder_device:
            pred_features = pred_features.to(self.vocoder_device)
        wav = self.vocoder.decode(pred_features).squeeze(1).clamp(-1, 1)
        wav = wav.to("cpu")

        if self.prompt_rms and self.prompt_rms < self.params.target_rms:
            wav = wav * self.prompt_rms / self.params.target_rms

        if self.params.remove_long_sil:
            wav = remove_silence(wav, self.sampling_rate, only_edge=False, trail_sil=0)

        return wav.squeeze(0).cpu()

    def synthesize_text(self, text: str) -> Iterator[AudioChunk]:
        """Generate audio chunks for the provided text."""
        self._ensure_prompt_ready()
        self._reset_seed_counter()
        self._apply_inference_seed(0)
        start_t = dt.datetime.now()

        token_chunks_str = self._chunk_text(text)
        token_chunks = self.tokenizer.tokens_to_token_ids(token_chunks_str)
        if not token_chunks:
            raise ValueError(
                "Input text resulted in no tokens. Provide text with supported characters."
            )

        for chunk_tokens, chunk_tokens_str in zip(token_chunks, token_chunks_str):
            chunk_text = "".join(chunk_tokens_str)
            chunk_start = dt.datetime.now()
            wav = self._synthesise_chunk(chunk_tokens)
            inference_seconds = (dt.datetime.now() - chunk_start).total_seconds()
            total_elapsed = (dt.datetime.now() - start_t).total_seconds()
            yield AudioChunk(
                audio=wav,
                sample_rate=self.sampling_rate,
                text=chunk_text,
                inference_seconds=inference_seconds,
                total_elapsed_seconds=total_elapsed,
            )

    # ------------------------------------------------------------------
    # Async helpers
    # ------------------------------------------------------------------
    async def stream_from_queue(self) -> AsyncIterator[AudioChunk]:
        """Yield audio chunks for texts submitted via :meth:`submit_text`.

        The queue allows other coroutines to call :meth:`submit_text` with
        arbitrary text fragments. Call :meth:`close_queue` to stop the stream.
        """

        if self._text_queue is None:
            self._text_queue = asyncio.Queue()

        start_t = dt.datetime.now()
        while True:
            text = await self._text_queue.get()
            if text is None:
                self._text_queue.task_done()
                break

            for chunk in self.synthesize_text(text):
                # Adjust total elapsed to be relative to queue start
                adjusted_chunk = AudioChunk(
                    audio=chunk.audio,
                    sample_rate=chunk.sample_rate,
                    text=chunk.text,
                    inference_seconds=chunk.inference_seconds,
                    total_elapsed_seconds=(dt.datetime.now() - start_t).total_seconds(),
                )
                yield adjusted_chunk

            self._text_queue.task_done()

    async def submit_text(self, text: str) -> None:
        if self._text_queue is None:
            self._text_queue = asyncio.Queue()
        await self._text_queue.put(text)

    async def close_queue(self) -> None:
        if self._text_queue is None:
            return
        await self._text_queue.put(None)  # type: ignore[arg-type]
        await self._text_queue.join()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def synthesize_to_file(self, text: str, path: str) -> None:
        """Synthesize *text* and write the concatenated result to *path*."""
        try:
            torchaudio = importlib.import_module("torchaudio")
        except ImportError as exc:
            raise RuntimeError(
                "torchaudio is required for synthesize_to_file. Install it via 'pip install torchaudio'."
            ) from exc

        audio_segments: List[Tensor] = []
        for chunk in self.synthesize_text(text):
            audio_segments.append(chunk.audio.unsqueeze(0))

        if not audio_segments:
            raise ValueError("No audio chunks were generated for the provided text")
        full_audio = torch.cat(audio_segments, dim=-1)
        torchaudio.save(path, full_audio, sample_rate=self.sampling_rate)

    def warm(self) -> None:
        """Run a tiny dummy synthesis to ensure kernels are initialised."""
        if self.prompt_tokens is None or self.prompt_features is None:
            raise RuntimeError("Cannot warm session before preparing a prompt")
        dummy_text = "Test"
        list(self.synthesize_text(dummy_text))

    def close(self) -> None:
        """Release large tensors."""
        self.prompt_tokens = None
        self.prompt_features = None
        self.prompt_rms = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


__all__ = ["AudioChunk", "ZipVoiceStreamingSession"]
