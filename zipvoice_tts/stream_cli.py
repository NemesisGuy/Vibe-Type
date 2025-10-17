"""Interactive ZipVoice streaming demo with live PyAudio playback.

The script keeps the ZipVoice streaming pipeline warm (ONNX Runtime or native
PyTorch), accepts text lines from stdin without blocking the user while
inference is running, and streams the generated speech to the default PyAudio
output device. Optionally, each generated chunk can also be written to disk.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import logging
import queue
import threading
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np
import torch

from zipvoice_streaming import ZipVoiceStreamingSession
from zipvoice_streaming.session import AudioChunk

logger = logging.getLogger(__name__)


def _parse_providers(value: Sequence[str] | None) -> Optional[Sequence[str]]:
    if not value:
        return None
    providers: List[str] = []
    for entry in value:
        providers.extend([item.strip() for item in entry.split(",") if item.strip()])
    return providers or None


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ZipVoice streaming CLI demo")
    parser.add_argument("--prompt-wav", required=True, help="Reference prompt wav")
    parser.add_argument(
        "--prompt-text",
        help="Prompt transcription. Provide this or --prompt-text-path.",
    )
    parser.add_argument(
        "--prompt-text-path",
        help="Path to a file containing the prompt transcription.",
    )
    parser.add_argument("--model-name", default="zipvoice", choices=["zipvoice", "zipvoice_distill"])
    parser.add_argument("--backend", default="onnx", choices=["onnx", "torch"], help="Inference backend")
    parser.add_argument("--onnx-int8", action="store_true", help="Use the int8 ONNX weights (backend=onnx)")
    parser.add_argument("--model-dir", help="Local directory containing model assets", default=None)
    parser.add_argument("--torch-checkpoint", help="Specific checkpoint file when backend=torch", default=None)
    parser.add_argument("--torch-device", help="Device for the PyTorch model (backend=torch)", default=None)
    parser.add_argument("--providers", nargs="*", help="Execution providers for ONNX Runtime (backend=onnx)")
    parser.add_argument(
        "--vocoder-device",
        default="cpu",
        help="Device for the PyTorch vocoder (e.g. cpu, cuda, cuda:0)",
    )
    parser.add_argument(
        "--save-chunks",
        action="store_true",
        help="Persist streamed chunks as chunk_XXXX.wav in --output-dir",
    )
    parser.add_argument("--output-dir", default="stream_chunks", help="Directory for saved wav chunks")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser


def read_prompt_text(args: argparse.Namespace) -> str:
    if args.prompt_text_path:
        return Path(args.prompt_text_path).read_text(encoding="utf-8")
    if args.prompt_text:
        return args.prompt_text
    raise ValueError("Provide either --prompt-text or --prompt-text-path")


def synthesis_worker(
    session: ZipVoiceStreamingSession,
    text_queue: "queue.Queue[Optional[str]]",
    audio_queue: "asyncio.Queue[Optional[AudioChunk]]",
    loop: asyncio.AbstractEventLoop,
) -> None:
    while True:
        text = text_queue.get()
        if text is None:
            text_queue.task_done()
            loop.call_soon_threadsafe(audio_queue.put_nowait, None)
            break

        logger.info("Synthesising text: %s", text)
        try:
            for chunk in session.synthesize_text(text):
                loop.call_soon_threadsafe(audio_queue.put_nowait, chunk)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to synthesise text")
        finally:
            text_queue.task_done()


def input_worker(text_queue: "queue.Queue[Optional[str]]") -> None:
    print("Type text and press enter to stream audio. Empty line quits.\n")
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        line = line.strip()
        if not line:
            break
        text_queue.put(line)

    text_queue.put(None)


def _save_chunk(path: Path, audio: torch.Tensor, sample_rate: int) -> Path:
    try:
        torchaudio = importlib.import_module("torchaudio")
    except ImportError as exc:  # pragma: no cover - runtime dependency hint
        raise RuntimeError(
            "torchaudio is required when --save-chunks is enabled. Install it via 'pip install torchaudio'."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(path), audio.unsqueeze(0), sample_rate=sample_rate)
    return path


async def playback_loop(
    audio_queue: "asyncio.Queue[Optional[AudioChunk]]",
    sample_rate: int,
    save_dir: Optional[Path],
) -> int:
    try:
        pyaudio = importlib.import_module("pyaudio")
    except ImportError as exc:  # pragma: no cover - runtime dependency hint
        raise RuntimeError(
            "PyAudio is required for live playback. Install it via 'pip install pyaudio'."
        ) from exc

    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paFloat32,
        channels=1,
        rate=sample_rate,
        output=True,
    )

    chunk_idx = 0
    try:
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                audio_queue.task_done()
                break

            audio_np = chunk.audio.numpy().astype(np.float32)
            stream.write(audio_np.tobytes())

            if save_dir is not None:
                chunk_path = save_dir / f"chunk_{chunk_idx:04d}.wav"
                saved_path = await asyncio.to_thread(_save_chunk, chunk_path, chunk.audio, sample_rate)
                logger.info(
                    "Saved %s (%.2fs, inference %.2fs)",
                    saved_path.name,
                    audio_np.shape[0] / sample_rate,
                    chunk.inference_seconds,
                )
            else:
                logger.info(
                    "Chunk %d | %.2fs | inference %.2fs",
                    chunk_idx,
                    audio_np.shape[0] / sample_rate,
                    chunk.inference_seconds,
                )

            chunk_idx += 1
            audio_queue.task_done()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    return chunk_idx


async def async_main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))

    prompt_text = read_prompt_text(args)
    if args.backend != "onnx" and args.providers:
        logger.warning("Ignoring --providers because backend=%s", args.backend)
    if args.backend == "torch" and args.onnx_int8:
        logger.warning("--onnx-int8 has no effect when backend=torch")

    if args.vocoder_device:
        args.vocoder_device = args.vocoder_device.strip()
    if args.model_dir:
        args.model_dir = args.model_dir.strip() or None
    if args.torch_checkpoint:
        args.torch_checkpoint = args.torch_checkpoint.strip() or None
    if args.torch_device:
        args.torch_device = args.torch_device.strip() or None

    providers = _parse_providers(args.providers) if args.backend == "onnx" else None

    session = ZipVoiceStreamingSession(
        model_name=args.model_name,
        onnx_int8=args.onnx_int8,
        model_dir=args.model_dir,
        providers=providers,
        backend=args.backend,
        torch_checkpoint=args.torch_checkpoint,
        torch_device=args.torch_device,
        vocoder_device=args.vocoder_device,
    )
    session.prepare_prompt(args.prompt_wav, prompt_text)

    loop = asyncio.get_running_loop()
    audio_queue: "asyncio.Queue[Optional[AudioChunk]]" = asyncio.Queue()
    text_queue: "queue.Queue[Optional[str]]" = queue.Queue()

    worker = threading.Thread(
        target=synthesis_worker,
        args=(session, text_queue, audio_queue, loop),
        daemon=True,
    )
    worker.start()

    save_dir = Path(args.output_dir) if args.save_chunks else None
    playback_task = asyncio.create_task(playback_loop(audio_queue, session.sampling_rate, save_dir))

    try:
        await asyncio.to_thread(input_worker, text_queue)
        await asyncio.to_thread(text_queue.join)
        await audio_queue.join()
        processed = await playback_task
    finally:
        worker.join(timeout=1.0)
        session.close()

    print(f"Generated {processed} chunks.")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
