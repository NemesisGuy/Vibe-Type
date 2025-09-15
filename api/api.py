# api/api.py

from flask import Flask, request, jsonify, Response
import numpy as np
import soundfile as sf
import io

# Assume KokoroTTS class is in the parent directory
import sys
sys.path.append('..')
from kokoro_tts.kokoro_tts import KokoroTTS

app = Flask(__name__)

# Initialize KokoroTTS
# This might take a moment on first startup
try:
    kokoro_tts = KokoroTTS()
except Exception as e:
    kokoro_tts = None
    print(f"CRITICAL: Failed to initialize KokoroTTS. API will not work. Error: {e}")

@app.route('/api/tts/kokoro/languages', methods=['GET'])
def get_kokoro_languages():
    if not kokoro_tts:
        return jsonify({"error": "KokoroTTS not initialized"}), 500
    
    try:
        languages = kokoro_tts.list_languages()
        return jsonify(languages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts/kokoro/voices', methods=['GET'])
def get_kokoro_voices():
    if not kokoro_tts:
        return jsonify({"error": "KokoroTTS not initialized"}), 500

    try:
        language = request.args.get('language', None)
        voices = kokoro_tts.list_voices(language_name=language)
        return jsonify(voices)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts/kokoro/synthesize', methods=['POST'])
def synthesize_kokoro_speech():
    if not kokoro_tts:
        return jsonify({"error": "KokoroTTS not initialized"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    text = data.get('text')
    language = data.get('language', 'Auto-Detect')
    voice = data.get('voice')
    speed = float(data.get('speed', 1.0))

    if not all([text, voice]):
        return jsonify({"error": "Missing required parameters: text, voice"}), 400

    try:
        audio_samples = kokoro_tts.synthesize_to_memory(
            text=text,
            language_name=language,
            voice_or_embedding=voice,
            speed=speed
        )

        if audio_samples.size == 0:
            return jsonify({"error": "Synthesis failed to produce audio"}), 500

        # Convert numpy array to WAV in memory
        wav_io = io.BytesIO()
        sf.write(wav_io, audio_samples, kokoro_tts.SAMPLE_RATE, format='WAV')
        wav_io.seek(0)

        return Response(wav_io, mimetype='audio/wav')

    except Exception as e:
        return jsonify({"error": f"Synthesis failed: {str(e)}"}), 500

if __name__ == '__main__':
    # Note: This is a development server. For production, use a proper WSGI server.
    app.run(host='0.0.0.0', port=5000)
