# KokoroTTS Usage Examples

This document provides clear examples of how to use the `KokoroTTS` class for high-quality, local text-to-speech synthesis.

## Basic Synthesis

This example shows the simplest way to generate speech from a string of text and save it to a file.

```python
from kokoro_tts import KokoroTTS
import soundfile as sf

# 1. Initialize the TTS engine
# This will download the necessary models on the first run.
tts = KokoroTTS()

# 2. Define the text and voice
text = "The sky above the port was the color of television, tuned to a dead channel."
language = "English (US)"
voice = "en_us_01" # An example voice

# 3. Generate audio samples to an in-memory NumPy array
audio_samples = tts.synthesize_to_memory(text, language, voice)

# 4. Save the audio to a file
sf.write("output.wav", audio_samples, tts.SAMPLE_RATE)

print("Audio saved to output.wav")
```

## Multi-Language Synthesis with Auto-Detect

The `KokoroTTS` engine can automatically detect the language of the input text and switch voices accordingly. This is useful for synthesizing text that contains multiple languages.

```python
from kokoro_tts import KokoroTTS
import soundfile as sf

# 1. Initialize the TTS engine
tts = KokoroTTS()

# 2. Define your multi-language text
# This example contains English and Japanese.
text = "Hello world. 「こんにちは、世界」"

# 3. Set the language to "Auto-Detect"
# The voice you provide will be used for the primary language (English in this case).
# The engine will automatically select the correct voice for other languages.
language = "Auto-Detect"
voice = "en_us_02"

# 4. Generate the audio
audio_samples = tts.synthesize_to_memory(text, language, voice)

# 5. Save the audio to a file
sf.write("multi_language_output.wav", audio_samples, tts.SAMPLE_RATE)

print("Multi-language audio saved to multi_language_output.wav")
```

## Streaming Synthesis

For long passages of text, you can use the `stream` method to start playback immediately while the rest of the audio is generated in the background. This provides a much more responsive experience.

```python
import threading
from kokoro_tts import KokoroTTS

# 1. Initialize the TTS engine
tts = KokoroTTS()

# 2. Define the text and voice
text = "This is a long passage of text that will be streamed. The first sentence will play almost instantly, while the rest is synthesized in the background. This provides a very responsive user experience."
language = "English (US)"
voice = "en_us_03"

# 3. Create an event to allow for interruption (optional)
interrupt_event = threading.Event()

# 4. Start the stream in a separate thread to avoid blocking
# The audio will play directly to your default audio device.
stream_thread = threading.Thread(
    target=tts.stream,
    args=(text, language, voice, 1.0, None, interrupt_event)
)

print("Starting audio stream...")
stream_thread.start()

# You can interrupt the speech at any time by setting the event
# import time
# time.sleep(3)
# print("Interrupting speech.")
# interrupt_event.set()

# Wait for the stream to finish
stream_thread.join()
print("Stream finished.")
```
