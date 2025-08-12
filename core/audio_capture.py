# core/audio_capture.py

import sounddevice as sd
import soundfile as sf
import threading
import queue

# Global instance to control recording
recorder = None

class AudioRecorder:
    def __init__(self, filename="temp_recording.wav", samplerate=44100, channels=1):
        self.filename = filename
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.q = queue.Queue()
        self.thread = None

    def _rec_thread(self):
        with sf.SoundFile(self.filename, mode='w', samplerate=self.samplerate, channels=self.channels) as file:
            with sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback):
                print("Recording started...")
                self.recording = True
                while self.recording:
                    file.write(self.q.get())
                print("Recording stopped.")

    def _callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status)
        self.q.put(indata.copy())

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._rec_thread)
            self.thread.start()

    def stop(self):
        self.recording = False
        if self.thread is not None:
            self.thread.join()
            self.thread = None

def start_capture():
    """Starts audio capture."""
    global recorder
    if recorder is None:
        recorder = AudioRecorder()
    recorder.start()

def stop_capture():
    """Stops audio capture."""
    global recorder
    if recorder is not None:
        recorder.stop()
        # To allow for a new recording next time
        recorder = None
