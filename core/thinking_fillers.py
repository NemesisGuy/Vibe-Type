# core/thinking_fillers.py

import random
import threading
import time
from typing import Optional, Callable

class ThinkingFillers:
    """
    Manages filler phrases that can be spoken while the LLM is processing a request.
    Provides variety and natural-sounding pauses during AI thinking time.
    """

    def __init__(self):
        self.filler_phrases = [
            # Thinking indicators
            "Let me think about that for a moment...",
            "Processing your request...",
            "Hmm, interesting question. Give me a second...",
            "Let me consider this carefully...",
            "Working on that now...",
            "One moment while I analyze this...",
            "Thinking through the best response...",
            "Let me process this information...",

            # Short pauses
            "Just a moment...",
            "Hold on...",
            "Give me a sec...",
            "Almost there...",
            "Nearly done...",
            "Just finishing up...",

            # Professional responses
            "Analyzing your input...",
            "Formulating a response...",
            "Gathering my thoughts...",
            "Composing an answer...",
            "Reviewing the details...",

            # Conversational
            "That's a good question...",
            "Interesting point...",
            "Let me see here...",
            "Alright, working on it...",
            "Bear with me for a moment...",

            # Technical context
            "Querying the language model...",
            "Running inference...",
            "Processing tokens...",
            "Generating response...",

            # Friendly delays
            "Putting together a good answer for you...",
            "Making sure I get this right...",
            "Taking a moment to think this through...",
            "Want to give you the best response...",
        ]

        self.short_phrases = [
            "Thinking...",
            "Processing...",
            "Working...",
            "Computing...",
            "Analyzing...",
            "Considering...",
            "Hmm...",
            "Let's see...",
        ]

        self.is_active = False
        self.filler_thread: Optional[threading.Thread] = None
        self.speak_callback: Optional[Callable] = None
        self.stop_event = threading.Event()

    def set_speak_callback(self, callback: Callable):
        """Set the TTS callback function to use for speaking fillers"""
        self.speak_callback = callback

    def get_random_filler(self, short=False) -> str:
        """Get a random filler phrase"""
        if short:
            return random.choice(self.short_phrases)
        return random.choice(self.filler_phrases)

    def start_thinking_mode(self, initial_delay=1.0, interval_min=3.0, interval_max=7.0):
        """
        Start speaking filler phrases at random intervals while LLM thinks.

        Args:
            initial_delay: Seconds to wait before first filler
            interval_min: Minimum seconds between fillers
            interval_max: Maximum seconds between fillers
        """
        if self.is_active or not self.speak_callback:
            return

        self.is_active = True
        self.stop_event.clear()

        def filler_worker():
            # Initial delay before first filler
            if self.stop_event.wait(initial_delay):
                return

            phrase_count = 0
            while not self.stop_event.is_set() and self.is_active:
                # Get a filler phrase
                if phrase_count > 2:  # Use shorter phrases after a few longer ones
                    phrase = self.get_random_filler(short=True)
                else:
                    phrase = self.get_random_filler(short=False)

                # Speak the filler
                try:
                    self.speak_callback(phrase)
                except Exception as e:
                    print(f"Error speaking filler: {e}")

                phrase_count += 1

                # Wait for next interval
                wait_time = random.uniform(interval_min, interval_max)
                if self.stop_event.wait(wait_time):
                    break

        self.filler_thread = threading.Thread(target=filler_worker, daemon=True)
        self.filler_thread.start()

    def stop_thinking_mode(self):
        """Stop the filler phrase system"""
        self.is_active = False
        self.stop_event.set()

        if self.filler_thread and self.filler_thread.is_alive():
            try:
                self.filler_thread.join(timeout=1.0)
            except Exception as e:
                print(f"Warning: Error stopping thinking filler thread: {e}")

        # Clear any pending TTS requests to prevent queue buildup, but don't interrupt ongoing speech
        try:
            if self.speak_callback:
                # Only clear the queue if no speech is currently playing
                import core.tts
                if not hasattr(core.tts, 'current_playback') or core.tts.current_playback is None:
                    # Clear the queue without interrupting current speech
                    while not core.tts.tts_queue.empty():
                        try:
                            core.tts.tts_queue.get_nowait()
                        except:
                            break
                # Don't call stop_speech() to avoid interrupting explanations
        except Exception as e:
            print(f"Warning: Could not clear TTS queue: {e}")

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_thinking_mode()
        except Exception:
            pass  # Ignore errors during cleanup

    def add_custom_phrase(self, phrase: str, is_short=False):
        """Add a custom filler phrase"""
        if is_short:
            self.short_phrases.append(phrase)
        else:
            self.filler_phrases.append(phrase)

    def get_completion_phrase(self) -> str:
        """Get a phrase to indicate thinking is complete"""
        completion_phrases = [
            "Alright, here's what I think...",
            "Okay, I've got it...",
            "Here's my response...",
            "After thinking about it...",
            "So here's what I found...",
            "Let me share my thoughts...",
            "Here's what I came up with...",
            "Alright, here we go...",
        ]
        return random.choice(completion_phrases)

# Global instance for easy access
thinking_fillers = ThinkingFillers()
