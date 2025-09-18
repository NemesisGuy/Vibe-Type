# api/api.py
# Refactored for versioned, robust Kokoro TTS API (see api_requirements_and_plan.md)

from flask import Flask, request, jsonify, Response, Blueprint
import numpy as np
import soundfile as sf
import io
import logging
import sys
sys.path.append('..')
from kokoro_tts.kokoro_tts import KokoroTTS, SAMPLE_RATE

app = Flask(__name__)
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# --- Logging setup ---
logger = logging.getLogger("api")
logging.basicConfig(level=logging.INFO)

# --- Utility: Standardized error response ---
def api_error(message, code=500, details=None):
    logger.error(f"API error: {message} | Details: {details}")
    return jsonify({"status": "error", "message": message, "details": details}), code

# --- Initialize KokoroTTS ---
try:
    kokoro_tts = KokoroTTS()
except Exception as e:
    kokoro_tts = None
    logger.critical(f"CRITICAL: Failed to initialize KokoroTTS. API will not work. Error: {e}")

# --- Kokoro TTS Endpoints ---
@api_v1.route('/tts/kokoro/languages', methods=['GET'])
def get_kokoro_languages():
    logger.info("GET /api/v1/tts/kokoro/languages")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    try:
        languages = kokoro_tts.list_languages()
        return jsonify(languages)
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
        return jsonify(voices)
    except Exception as e:
        return api_error("Failed to list voices", 500, str(e))

@api_v1.route('/tts/kokoro/models', methods=['GET'])
def get_kokoro_models():
    logger.info("GET /api/v1/tts/kokoro/models")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    try:
        models = kokoro_tts.list_models()
        return jsonify(models)
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
        return Response(wav_io, mimetype='audio/wav')
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
    language = data.get('language', 'Auto-Detect')
    voice = data.get('voice')
    if not text:
        return api_error("Missing required parameter: text", 400)
    try:
        # Use the same segmentation as synthesis
        segments = kokoro_tts._segment_by_language(text) if language == 'Auto-Detect' else [(language, text)]
        phoneme_results = []
        for lang, seg in segments:
            g2p_engine = kokoro_tts._get_g2p_pipeline(kokoro_tts.LANGUAGE_CONFIG[lang]["lang_code"]) if lang in kokoro_tts.LANGUAGE_CONFIG else None
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
        return jsonify(phoneme_results)
    except Exception as e:
        return api_error("Phoneme breakdown failed", 500, str(e))

@api_v1.route('/tts/kokoro/speak', methods=['POST'])
def speak_kokoro_speech():
    logger.info("POST /api/v1/tts/kokoro/speak")
    if not kokoro_tts:
        return api_error("KokoroTTS not initialized", 500)
    data = request.get_json()
    if not data:
        return api_error("Invalid JSON body", 400)
    text = data.get('text')
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
    import threading
    threading.Thread(target=background_tts, daemon=True).start()
    # Spoof HTTP 200 instead of 202 for compatibility with MCP/agent
    return jsonify({"status": "in_progress", "message": "Speech synthesis started"}), 200

@api_v1.route('/status', methods=['GET'])
def api_status():
    """Simple health/status endpoint for API server."""
    return jsonify({
        "status": "ok",
        "message": "API server is running.",
        "version": "1.0"
    })

# --- Register Blueprint ---
app.register_blueprint(api_v1)

if __name__ == '__main__':
    import socket
    host = '0.0.0.0'
    port = 9031
    # Get local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = '127.0.0.1'
    logger.info(f"API server starting on http://{local_ip}:{port} (and 0.0.0.0:{port})")
    print(f"API server starting on http://{local_ip}:{port} (and 0.0.0.0:{port})")
    app.run(host=host, port=port)
