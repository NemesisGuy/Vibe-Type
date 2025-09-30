# api/api.py
# Refactored for versioned, robust Kokoro TTS API (see api_requirements_and_plan.md)

from flask import Flask, request, jsonify, Response, Blueprint
import numpy as np
import soundfile as sf
import io
import logging
import sys
import os
import threading
import re
import time

# Ensure project root is on sys.path for 'kokoro_tts' imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from kokoro_tts.kokoro_tts import KokoroTTS, SAMPLE_RATE

app = Flask(__name__)
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# --- Logging setup ---
logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

# --- Utility: Standardized error/ok response with Connection: close ---
from flask import make_response

def api_ok(payload, code=200):
    resp = make_response(jsonify(payload), code)
    resp.headers['Connection'] = 'close'
    return resp

def api_error(message, code=500, details=None):
    logger.error(f"API error: {message} | Details: {details}")
    resp = make_response(jsonify({"status": "error", "message": message, "details": details}), code)
    resp.headers['Connection'] = 'close'
    return resp

# --- Initialize KokoroTTS ---
try:
    kokoro_tts = KokoroTTS()
except Exception as e:
    kokoro_tts = None
    logger.critical(f"CRITICAL: Failed to initialize KokoroTTS. API will not work. Error: {e}")

# --- Text normalization to reduce G2P hiccups (smart quotes/dashes, NBSP, mojibake) ---
_MOJI_MAP = {
    '\u2018': "'", '\u2019': "'",  # single quotes
    '\u201C': '"', '\u201D': '"',  # double quotes
    '\u2013': '-',  '\u2014': '-',  # en/em dash
    '\u00A0': ' ',                   # non-breaking space
    '\u2026': '...',                 # ellipsis
}
# Common mojibake patterns when UTF-8 seen as Latin-1
_MOJI_MOJIBAKE = {
    'â€™': "'",
    'â€œ': '"', 'â€�': '"',
    'â€"': '-', 'â€"': '-',
}
_WS_RE = re.compile(r"\s+")

# Fallback mapping if KokoroTTS.LANGUAGE_CONFIG is unavailable
_FALLBACK_LANG_CODES = {
    'English (US)': 'a',
    'Japanese': 'j',
    'Mandarin Chinese': 'z',
    'Spanish': 's',
    'French': 'f',
    'Portuguese (BR)': 'p',
    'Italian': 'i',
    'Hindi': 'h',
}

def _resolve_lang_code(lang_name: str):
    try:
        cfg = getattr(kokoro_tts, 'LANGUAGE_CONFIG', None)
        if isinstance(cfg, dict) and lang_name in cfg and 'lang_code' in cfg[lang_name]:
            return cfg[lang_name]['lang_code']
    except Exception:
        pass
    return _FALLBACK_LANG_CODES.get(lang_name)

def normalize_text(s: str) -> str:
    if not s:
        return s
    # First pass: unicode translate
    s = s.translate(str.maketrans(_MOJI_MAP))
    # Second pass: fix common mojibake sequences
    for bad, good in _MOJI_MOJIBAKE.items():
        if bad in s:
            s = s.replace(bad, good)
    # Collapse whitespace
    s = _WS_RE.sub(' ', s).strip()
    return s

# --- Kokoro TTS Endpoints ---
@api_v1.route('/tts/kokoro/languages', methods=['GET'])
def get_kokoro_languages():
    logger.info("GET /api/v1/tts/kokoro/languages")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    try:
        languages = kokoro_tts.list_languages()
        return api_ok(languages)
    except Exception as e:
        return api_error("Failed to list languages", 500, str(e))

@api_v1.route('/tts/kokoro/voices', methods=['GET'])
def get_kokoro_voices():
    logger.info("GET /api/v1/tts/kokoro/voices")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    try:
        language = request.args.get('language', None)
        voices = kokoro_tts.list_voices(language_name=language)
        return api_ok(voices)
    except Exception as e:
        return api_error("Failed to list voices", 500, str(e))

@api_v1.route('/tts/kokoro/models', methods=['GET'])
def get_kokoro_models():
    logger.info("GET /api/v1/tts/kokoro/models")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    try:
        models = kokoro_tts.list_models()
        return api_ok(models)
    except Exception as e:
        return api_error("Failed to list models", 500, str(e))

@api_v1.route('/tts/kokoro/synthesize', methods=['POST'])
def synthesize_kokoro_speech():
    logger.info("POST /api/v1/tts/kokoro/synthesize")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    data = request.get_json()
    if not data:
        return api_error("Invalid JSON body", 400)
    text = data.get('text')
    # Normalize potentially problematic punctuation/encoding before G2P
    text = normalize_text(text)
    language = data.get('language', 'Auto-Detect')
    voice = data.get('voice')
    speed = float(data.get('speed', 1.0))
    if not all([text, voice]):
        return api_error("Missing required parameters: text, voice", 400)
    try:
        audio_samples = kokoro_tts.synthesize_to_memory(
            text=text,
            language_name=language,
            voice_or_embedding=voice,
            speed=speed
        )
        if audio_samples.size == 0:
            return api_error("Synthesis failed to produce audio", 500)
        wav_io = io.BytesIO()
        sf.write(wav_io, audio_samples, SAMPLE_RATE, format='WAV')
        wav_io.seek(0)
        resp = Response(wav_io, mimetype='audio/wav')
        resp.headers['Connection'] = 'close'
        return resp
    except Exception as e:
        return api_error("Synthesis failed", 500, str(e))

@api_v1.route('/tts/kokoro/phonemes', methods=['POST'])
def get_kokoro_phonemes():
    logger.info("POST /api/v1/tts/kokoro/phonemes")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    data = request.get_json()
    if not data:
        return api_error("Invalid JSON body", 400)
    text = data.get('text')
    # Normalize for G2P stability
    text = normalize_text(text)
    language = data.get('language', 'Auto-Detect')
    voice = data.get('voice')
    if not text:
        return api_error("Missing required parameter: text", 400)
    try:
        # Use the same segmentation as synthesis
        segments = kokoro_tts._segment_by_language(text) if language == 'Auto-Detect' else [(language, text)]
        phoneme_results = []
        for lang, seg in segments:
            code = _resolve_lang_code(lang)
            g2p_engine = kokoro_tts._get_g2p_pipeline(code) if code else None
            if not g2p_engine:
                phoneme_results.append({"language": lang, "text": seg, "phonemes": None, "error": "No G2P engine"})
                continue
            try:
                phonemes = g2p_engine(seg)
                if isinstance(phonemes, tuple) and len(phonemes) == 2:
                    phoneme_str = phonemes[0]
                    tokens = [
                        {"text": getattr(t, 'text', ''), "phonemes": getattr(t, 'phonemes', ''), "whitespace": getattr(t, 'whitespace', '')}
                        for t in phonemes[1]
                    ]
                else:
                    phoneme_str = phonemes
                    tokens = None
                phoneme_results.append({"language": lang, "text": seg, "phonemes": phoneme_str, "tokens": tokens})
            except Exception as g2p_e:
                phoneme_results.append({"language": lang, "text": seg, "phonemes": None, "error": str(g2p_e)})
        return api_ok(phoneme_results)
    except Exception as e:
        # Degrade gracefully: return a single-item array with error info (HTTP 200)
        logger.error(f"phonemes unexpected error: {e}")
        return api_ok([{"language": language, "text": text, "phonemes": None, "error": str(e)}])

@api_v1.route('/tts/kokoro/speak', methods=['POST'])
def speak_kokoro_speech():
    logger.info("POST /api/v1/tts/kokoro/speak")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    data = request.get_json()
    if not data:
        return api_error("Invalid JSON body", 400)
    text = data.get('text')
    # Normalize for G2P stability
    text = normalize_text(text)
    language = data.get('language', 'Auto-Detect')
    voice = data.get('voice')
    speed = float(data.get('speed', 1.0))
    if not all([text, voice]):
        return api_error("Missing required parameters: text, voice", 400)

    def background_tts():
        try:
            kokoro_tts.stream(
                text=text,
                language_name=language,
                voice_or_embedding=voice,
                speed=speed,
                device_index=None,
                interrupt_event=None
            )
            logger.info(f"Background TTS playback completed for text: {text[:40]}...")
        except Exception as e:
            logger.error(f"Background TTS playback failed: {e}")

    # Simple fire-and-forget: spawn daemon thread and return immediately
    thread = threading.Thread(target=background_tts, daemon=True)
    thread.start()

    # Return immediately for MCP/agents compatibility
    return api_ok({"status": "in_progress", "message": "Speech synthesis started"}, 200)

@api_v1.route('/status', methods=['GET'])
def api_status():
    """Simple health/status endpoint for API server (versioned)."""
    return api_ok({
        "status": "ok",
        "message": "API server is running.",
        "version": "1.0"
    })

# Also expose a root-level /status for convenience (non-versioned)
@app.route('/status', methods=['GET'])
def api_status_root():
    return api_ok({
        "status": "ok",
        "message": "API server is running.",
        "version": "1.0"
    })

# Friendly root index so GET / returns helpful info instead of 404
@app.route('/', methods=['GET'])
def api_index():
    return api_ok({
        "message": "VibeType API",
        "version": "1.0",
        "endpoints": {
            "status": "/status",
            "languages": "/api/v1/tts/kokoro/languages",
            "voices": "/api/v1/tts/kokoro/voices",
            "models": "/api/v1/tts/kokoro/models",
            "speak": "/api/v1/tts/kokoro/speak",
            "synthesize": "/api/v1/tts/kokoro/synthesize",
            "phonemes": "/api/v1/tts/kokoro/phonemes"
        }
    })

# --- Register Blueprint ---
app.register_blueprint(api_v1)

if __name__ == '__main__':
    import socket
    # Read overrides from environment
    host = os.environ.get('VIBETYPE_API_HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('VIBETYPE_API_PORT', '9031'))
    except Exception:
        port = 9031
    # Get local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'
    logger.info(f"API server starting on http://{local_ip}:{port} and http://127.0.0.1:{port} (host={host})")
    print(f"API server starting on http://{local_ip}:{port} and http://127.0.0.1:{port} (host={host})")
    # Prefer Waitress if available for better concurrency on Windows
    try:
        import waitress
        waitress.serve(app, host=host, port=port, threads=4)
    except Exception as e:
        logger.info(f"Waitress not available or failed ({e}); falling back to Flask dev server.")
        app.run(host=host, port=port, threaded=True, use_reloader=False)
