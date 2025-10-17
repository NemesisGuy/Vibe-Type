# ZipVoice Streaming Session

This folder contains a small helper module that keeps the ZipVoice model (ONNX
Runtime or native PyTorch) and the Vocos vocoder warm so text can be pushed
continuously and converted to
speech without repeatedly downloading or reloading the model. It is aimed at
integrating ZipVoice into interactive assistants or any other application where
sentences arrive incrementally.

## Key features

- Keeps the chosen ZipVoice backend and the PyTorch vocoder alive between calls.
- Accepts new text snippets while reusing the same prompt voice.
- Exposes both synchronous generators and an async queue interface for easy
    integration with GUI, WebSocket, or voice assistant back ends.
- Ships with a PyAudio-powered CLI demo that keeps inference responsive while
    you continue typing.
- Lets you keep the PyTorch model and vocoder on CUDA (or CPU) to compare
    latency trade-offs easily.
- Works with CUDA (or CPU) ONNX Runtime providers and with native PyTorch
    checkpoints.

## Usage overview

```python
from zipvoice_streaming import ZipVoiceStreamingSession

session = ZipVoiceStreamingSession(
    model_name="zipvoice",
    backend="onnx",
    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
)
session.prepare_prompt("samples/optimus_3s.wav", open("samples/optimus_3s.txt").read())

# Synchronous chunked synthesis
for chunk in session.synthesize_text("Autobots, roll out!"):
    play(chunk.audio.numpy(), rate=chunk.sample_rate)

# Async queue streaming
async def produce():
    await session.submit_text("First sentence.")
    await session.submit_text("Another thought...")
    await session.close_queue()

async def consume():
    async for chunk in session.stream_from_queue():
        stream_audio(chunk.audio)

```

Pass `backend="torch"` (and optionally `torch_device="cuda"`) to reuse the
native PyTorch checkpoint instead of the ONNX Runtime export.

## Vendored ZipVoice code

The directory now ships with a vendored copy of the original `zipvoice`
package under `zipvoice_streaming/vendor`. If you make upstream changes, run

```powershell
python zipvoice_streaming/_vendorize.py
```

to refresh the snapshot. When the vendored package is present, the streaming
helpers automatically route imports through it so you can drop this folder into
another project without additional dependencies beyond PyTorch, torchaudio,
onnxruntime, safetensors, and the datasets referenced by the model weights.

## CLI demo with live playback

The `stream_cli.py` module offers an interactive demo that streams the generated
audio to your default output device via PyAudio. While inference is running you
can continue to enter new lines of text; they are queued and spoken in order
without reloading the model.

```powershell
python -m zipvoice_streaming.stream_cli `
    --prompt-wav ..\samples\optimus_3s.wav `
    --prompt-text-path ..\samples\optimus_3s.txt `
    --backend onnx `
    --providers CUDAExecutionProvider CPUExecutionProvider `
    --vocoder-device cuda
```

To use the native PyTorch checkpoint instead, switch backends and optionally
choose a device for the model:

```powershell
python -m zipvoice_streaming.stream_cli `
    --prompt-wav ..\samples\optimus_3s.wav `
    --prompt-text-path ..\samples\optimus_3s.txt `
    --backend torch `
    --torch-device cuda `
    --vocoder-device cuda
```

Add `--save-chunks` if you also want each streamed segment written to
`stream_chunks/chunk_XXXX.wav` (`torchaudio` is required for this option).

You can now import this helper from another project, attach your own networking
layer, and feed text in near real time while reusing the ZipVoice model.
