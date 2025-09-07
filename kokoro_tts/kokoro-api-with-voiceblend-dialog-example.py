import os
import sys
import numpy as np
import io
import re
import time
import requests
import platform
import psutil
import asyncio
import random
from scipy.io.wavfile import write as write_wav
import uvicorn
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field, model_validator
from fastapi.middleware.cors import CORSMiddleware
from kokoro_onnx import Kokoro, Tokenizer
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
MODEL_FILES = [
    {"filename": "kokoro-v1.0.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx", "description": "Full Precision (FP32)"},
    {"filename": "kokoro-v1.0.fp16.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.fp16.onnx", "description": "Half Precision (FP16)"},
    {"filename": "kokoro-v1.0.int8.onnx", "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx", "description": "Quantized (INT8)"}
]
VOICES_FILE = "voices-v1.0.bin"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/" + VOICES_FILE
voices_path = os.path.join(MODELS_DIR, VOICES_FILE)

MODEL_FILE = "kokoro-v1.0.int8.onnx"
model_path = os.path.join(MODELS_DIR, MODEL_FILE)

def download_file_robust(url: str, destination: str):
    logger.info(f"Downloading {os.path.basename(destination)}...")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            with open(destination, 'wb') as f, tqdm(
                total=total_size, unit='iB', unit_scale=True, desc=os.path.basename(destination)
            ) as bar:
                for chunk in r.iter_content(chunk_size=8192):
                    size = f.write(chunk)
                    bar.update(size)
        if total_size != 0 and os.path.getsize(destination) != total_size:
            logger.error(f"Download failed. File is incomplete: {destination}")
            sys.exit(1)
        logger.info("Download verified and complete.")
    except Exception as e:
        logger.error(f"Failed to download model file. Error: {e}")
        sys.exit(1)

def download_models_if_missing():
    os.makedirs(MODELS_DIR, exist_ok=True)
    for model_info in MODEL_FILES:
        model_path = os.path.join(MODELS_DIR, model_info["filename"])
        if not os.path.exists(model_path):
            download_file_robust(model_info["url"], model_path)
    if not os.path.exists(voices_path):
        download_file_robust(VOICES_URL, voices_path)

download_models_if_missing()

logger.info("Loading model and tokenizer...")
tokenizer = Tokenizer()
kokoro = Kokoro(model_path, voices_path)
SAMPLE_RATE = 24000
logger.info("Model and voices loaded successfully. API is ready.")

app = FastAPI(title="Kokoro TTS Service", version="FINAL-STABLE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceComponent(BaseModel):
    voice: str
    weight: float = Field(..., ge=0.0, le=1.0)

class DialogueLine(BaseModel):
    text: str
    voice: Optional[str] = None
    blend_components: Optional[List[VoiceComponent]] = None
    delay: Optional[float] = 0.0
    speed: float = Field(1.0, ge=0.25, le=2.0)

    @model_validator(mode='before')
    def check_voice_or_blend(cls, values):
        if not (bool(values.get('voice')) ^ bool(values.get('blend_components'))):
            raise ValueError('Each line must have "voice" or "blend_components", not both.')
        return values

class SynthesizeRequest(BaseModel):
    script: List[DialogueLine]

class BenchmarkResult(BaseModel):
    model_name: str
    description: str
    size_mb: float
    load_time: float
    inference_time: float
    duration: float
    rtf: float
    mem_usage: float

class BenchmarkResponse(BaseModel):
    results: List[BenchmarkResult]
    system_info: dict
    recommendation: dict

class SetModelRequest(BaseModel):
    model_name: str

class RandomSpeakerRequest(BaseModel):
    text: str
    speed: float = Field(1.0, ge=0.25, le=2.0)

class RandomCustomVoiceRequest(BaseModel):
    text: str
    speed: float = Field(1.0, ge=0.25, le=2.0)
    num_voices: int = Field(2, ge=2, le=3)

async def generate_full_audio(script: List[DialogueLine]):
    logger.info(f"Generating audio for script with {len(script)} lines")
    start_time = time.time()
    all_samples = []
    chunk_size = 10  # Process 10 lines at a time
    for chunk_idx, i in enumerate(range(0, len(script), chunk_size)):
        chunk = script[i:i + chunk_size]
        logger.debug(f"Processing chunk {chunk_idx + 1} ({len(chunk)} lines)")
        chunk_samples = []
        for idx, line in enumerate(chunk):
            logger.debug(f"Processing line {i + idx + 1}: {line.text[:50]}...")
            voice_or_style = None
            if line.blend_components:
                final_style = np.zeros(256, dtype=np.float16)
                total_weight = sum(c.weight for c in line.blend_components)
                for c in line.blend_components:
                    if c.voice in kokoro.get_voices():
                        final_style = np.add(final_style, kokoro.get_voice_style(c.voice) * c.weight)
                if total_weight > 0:
                    final_style /= total_weight
                voice_or_style = final_style
            elif line.voice and line.voice in kokoro.get_voices():
                voice_or_style = line.voice
            if voice_or_style is None:
                logger.warning(f"Skipping line {i + idx + 1}: No valid voice or blend components")
                continue
            if line.delay and line.delay > 0:
                chunk_samples.append(np.zeros(int(line.delay * SAMPLE_RATE), dtype=np.float32))
            phonemes = tokenizer.phonemize(line.text, lang="en-us")
            if not phonemes:
                logger.warning(f"Skipping line {i + idx + 1}: No phonemes generated")
                continue
            line_start = time.time()
            samples, _ = await asyncio.to_thread(kokoro.create, phonemes, voice=voice_or_style, speed=line.speed, is_phonemes=True)
            logger.debug(f"Line {i + idx + 1} synthesis took {time.time() - line_start:.2f} seconds")
            chunk_samples.append(samples.astype(np.float32))
        if chunk_samples:
            all_samples.append(np.concatenate(chunk_samples))
        logger.debug(f"Chunk {chunk_idx + 1} completed in {time.time() - start_time:.2f} seconds")
    full_audio = np.concatenate(all_samples) if all_samples else np.array([], dtype=np.float32)
    logger.info(f"Total audio generation took {time.time() - start_time:.2f} seconds")
    return full_audio

@app.get("/benchmark", response_model=BenchmarkResponse)
async def benchmark_models():
    logger.info("Running benchmark...")
    start_time = time.time()
    benchmark_text = "This is a standard sentence for benchmarking."
    phonemes = tokenizer.phonemize(benchmark_text, lang="en-us")
    results = []
    process = psutil.Process()
    mem_before_all = process.memory_info().rss / (1024 * 1024)
    model_timeout = 30

    for model_info in MODEL_FILES:
        filename = model_info["filename"]
        model_path = os.path.join(MODELS_DIR, filename)
        file_size_mb = os.path.getsize(model_path) / (1024 * 1024)

        logger.debug(f"Benchmarking model: {filename}")
        try:
            start_load_time = time.perf_counter()
            kokoro_instance = Kokoro(model_path, voices_path)
            end_load_time = time.perf_counter()
            load_time = end_load_time - start_load_time
            if load_time > model_timeout:
                logger.warning(f"Model {filename} load time exceeded {model_timeout}s, skipping")
                continue

            mem_after_load = process.memory_info().rss / (1024 * 1024)

            start_infer_time = time.perf_counter()
            samples, sample_rate = kokoro_instance.create(phonemes, voice="am_adam", is_phonemes=True)
            end_infer_time = time.perf_counter()
            inference_time = end_infer_time - start_infer_time
            if inference_time > model_timeout:
                logger.warning(f"Model {filename} inference time exceeded {model_timeout}s, skipping")
                del kokoro_instance
                continue

            mem_after_infer = process.memory_info().rss / (1024 * 1024)
            model_mem_usage = mem_after_infer - mem_before_all

            audio_duration = len(samples) / sample_rate
            rtf = inference_time / audio_duration

            results.append({
                "model_name": filename,
                "description": model_info["description"],
                "size_mb": file_size_mb,
                "load_time": load_time,
                "inference_time": inference_time,
                "duration": audio_duration,
                "rtf": rtf,
                "mem_usage": model_mem_usage
            })

            del kokoro_instance
        except Exception as e:
            logger.error(f"Failed to benchmark model {filename}: {str(e)}")
            continue

    if not results:
        logger.error("No models successfully benchmarked")
        raise HTTPException(status_code=500, detail="No models could be benchmarked due to timeouts or errors")

    system_info = {
        "cpu": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "total_ram_gb": psutil.virtual_memory().total / (1024**3)
    }

    fastest_inference = min(results, key=lambda x: x["rtf"])
    highest_quality = next((r for r in results if r["model_name"].endswith('.onnx') and 'fp' not in r["model_name"] and 'int' not in r["model_name"]), None)
    best_balanced = next((r for r in results if r["model_name"].endswith('int8.onnx')), fastest_inference)

    recommendation = {
        "best_balanced": {
            "model_name": best_balanced["model_name"],
            "description": best_balanced["description"],
            "reason": f"Offers a good balance of speed (RTF: {best_balanced['rtf']:.2f}) and memory usage ({best_balanced['mem_usage']:.0f} MB)."
        },
        "fastest": {
            "model_name": fastest_inference["model_name"],
            "description": fastest_inference["description"],
            "reason": f"Lowest Real-Time Factor (RTF: {fastest_inference['rtf']:.2f})."
        },
        "highest_quality": {
            "model_name": highest_quality["model_name"] if highest_quality else None,
            "description": highest_quality["description"] if highest_quality else None,
            "reason": f"Highest fidelity, but uses the most memory ({highest_quality['mem_usage']:.0f} MB)." if highest_quality else None
        }
    }

    logger.info(f"Benchmark completed in {time.time() - start_time:.2f} seconds")
    return {"results": results, "system_info": system_info, "recommendation": recommendation}

@app.post("/set-model")
async def set_model(request: SetModelRequest):
    global kokoro, model_path
    requested_model = request.model_name
    if requested_model not in [m["filename"] for m in MODEL_FILES]:
        raise HTTPException(status_code=400, detail=f"Invalid model: {requested_model}. Available models: {[m['filename'] for m in MODEL_FILES]}")
    new_model_path = os.path.join(MODELS_DIR, requested_model)
    if not os.path.exists(new_model_path):
        raise HTTPException(status_code=400, detail=f"Model file {requested_model} not found.")
    try:
        logger.info(f"Switching to model: {requested_model}")
        model_path = new_model_path
        del kokoro
        kokoro = Kokoro(model_path, voices_path)
        return {"status": f"Successfully switched to model {requested_model}"}
    except Exception as e:
        logger.error(f"Failed to switch model: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to switch model: {str(e)}")

@app.post("/random-speaker")
async def random_speaker(request: RandomSpeakerRequest):
    try:
        voices = kokoro.get_voices()
        if not voices:
            raise HTTPException(status_code=400, detail="No voices available.")
        random_voice = random.choice(voices)
        logger.info(f"Selected random voice: {random_voice}")
        script = [{"text": request.text, "voice": random_voice, "speed": request.speed}]
        full_audio = await generate_full_audio(script)
        if full_audio.size == 0:
            return Response(content=b"", media_type="audio/wav")
        max_val = np.max(np.abs(full_audio))
        if max_val > 0:
            full_audio /= max_val
        buffer = io.BytesIO()
        write_wav(buffer, SAMPLE_RATE, full_audio)
        buffer.seek(0)
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={"X-Selected-Voice": random_voice}
        )
    except Exception as e:
        logger.error(f"Random speaker error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/random-custom-voice")
async def random_custom_voice(request: RandomCustomVoiceRequest):
    try:
        voices = kokoro.get_voices()
        if len(voices) < request.num_voices:
            raise HTTPException(status_code=400, detail=f"Not enough voices available for blending (requested {request.num_voices}, available {len(voices)}).")
        selected_voices = random.sample(voices, request.num_voices)
        weights = np.random.dirichlet(np.ones(request.num_voices))
        blend_components = [{"voice": voice, "weight": float(weight)} for voice, weight in zip(selected_voices, weights)]
        logger.info(f"Blended voices: {blend_components}")
        script = [{"text": request.text, "blend_components": blend_components, "speed": request.speed}]
        full_audio = await generate_full_audio(script)
        if full_audio.size == 0:
            return Response(content=b"", media_type="audio/wav")
        max_val = np.max(np.abs(full_audio))
        if max_val > 0:
            full_audio /= max_val
        buffer = io.BytesIO()
        write_wav(buffer, SAMPLE_RATE, full_audio)
        buffer.seek(0)
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={"X-Blended-Voices": json.dumps(blend_components)}
        )
    except Exception as e:
        logger.error(f"Random custom voice error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "Kokoro TTS API is running."}

@app.get("/voices", response_model=List[str])
async def get_voices():
    return sorted(kokoro.get_voices())

@app.post("/synthesize-stream")
async def synthesize_stream(request: SynthesizeRequest):
    q = asyncio.Queue(maxsize=20)
    async def producer():
        chunk_size = 10
        for chunk_idx, i in enumerate(range(0, len(request.script), chunk_size)):
            chunk = request.script[i:i + chunk_size]
            logger.debug(f"Streaming chunk {chunk_idx + 1} ({len(chunk)} lines)")
            for line in chunk:
                voice_or_style = None
                if line.blend_components:
                    final_style = np.zeros(256, dtype=np.float16)
                    total_weight = sum(c.weight for c in line.blend_components)
                    for c in line.blend_components:
                        if c.voice in kokoro.get_voices():
                            final_style = np.add(final_style, kokoro.get_voice_style(c.voice) * c.weight)
                    if total_weight > 0:
                        final_style /= total_weight
                    voice_or_style = final_style
                elif line.voice and line.voice in kokoro.get_voices():
                    voice_or_style = line.voice
                if voice_or_style is None:
                    continue
                if line.delay and line.delay > 0:
                    await q.put(np.zeros(int(line.delay * SAMPLE_RATE), dtype=np.float32))
                sentences = re.split(r'(?<=[.?!])\s*', line.text)
                sentences = [s.strip() for s in sentences if s.strip()]
                for sentence in sentences:
                    phonemes = tokenizer.phonemize(sentence, lang="en-us")
                    if not phonemes:
                        continue
                    samples, _ = await asyncio.to_thread(kokoro.create, phonemes, voice=voice_or_style, speed=line.speed, is_phonemes=True)
                    await q.put(samples)
            logger.debug(f"Chunk {chunk_idx + 1} streamed")
        await q.put(None)
    async def stream_generator():
        asyncio.create_task(producer())
        while True:
            samples = await q.get()
            if samples is None:
                break
            yield samples.astype(np.float32).tobytes()
    headers = {"X-Sample-Rate": str(SAMPLE_RATE)}
    return StreamingResponse(stream_generator(), media_type="application/octet-stream", headers=headers)

@app.post("/synthesize-wav")
async def synthesize_wav(request: SynthesizeRequest):
    try:
        logger.info(f"Received synthesis request with {len(request.script)} lines")
        full_audio = await generate_full_audio(request.script)
        if full_audio.size == 0:
            logger.warning("No audio generated")
            return Response(content=b"", media_type="audio/wav")
        max_val = np.max(np.abs(full_audio))
        if max_val > 0:
            full_audio /= max_val
        buffer = io.BytesIO()
        write_wav(buffer, SAMPLE_RATE, full_audio)
        buffer.seek(0)
        logger.info("Synthesis completed successfully")
        return Response(content=buffer.getvalue(), media_type="audio/wav")
    except Exception as e:
        logger.error(f"Synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, workers=1)


#blending eaxple 2

#
#     """
# pip install -U kokoro-onnx soundfile
#
# wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
# wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
# python examples/with_blending.py
# """

#import numpy as np
#import soundfile as sf

#from kokoro_onnx import Kokoro

# #kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
# nicole: np.ndarray = kokoro.get_voice_style("af_nicole")
# michael: np.ndarray = kokoro.get_voice_style("am_michael")
# blend = np.add(nicole * (50 / 100), michael * (50 / 100))
# samples, sample_rate = kokoro.create(
#     "Hello. This audio is generated by Kokoro!",
#     voice=blend,
#     speed=1.0,
#     lang="en-us",
# )
# sf.write("audio.wav", samples, sample_rate)
# print("Created audio.wav")
