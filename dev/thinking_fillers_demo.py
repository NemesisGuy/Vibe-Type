# dev/thinking_fillers_demo.py

"""
Demo script to test the thinking fillers system independently.
This helps verify that the filler phrases work correctly with TTS.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.thinking_fillers import thinking_fillers
import time

def mock_tts_callback(text):
    """Mock TTS function that just prints what would be spoken"""
    print(f"[TTS MOCK] Speaking: '{text}'")

def demo_thinking_fillers():
    """Demonstrates the thinking fillers system"""
    print("=== Thinking Fillers Demo ===")
    print("This demo shows how filler phrases would work during AI processing.")
    print("In real use, these would be spoken via TTS while Ollama thinks.\n")

    # Set up the mock TTS
    thinking_fillers.set_speak_callback(mock_tts_callback)

    print("1. Testing individual filler phrases:")
    for i in range(5):
        phrase = thinking_fillers.get_random_filler()
        print(f"   Filler {i+1}: {phrase}")

    print("\n2. Testing short filler phrases:")
    for i in range(5):
        phrase = thinking_fillers.get_random_filler(short=True)
        print(f"   Short {i+1}: {phrase}")

    print("\n3. Testing completion phrases:")
    for i in range(3):
        phrase = thinking_fillers.get_completion_phrase()
        print(f"   Completion {i+1}: {phrase}")

    print("\n4. Simulating AI thinking session (10 seconds):")
    print("   Starting thinking mode...")

    thinking_fillers.start_thinking_mode(
        initial_delay=0.5,  # Start after 0.5 seconds
        interval_min=1.0,   # Fast demo intervals
        interval_max=2.5
    )

    # Simulate AI processing time
    time.sleep(10)

    print("   Stopping thinking mode...")
    thinking_fillers.stop_thinking_mode()

    # Show completion
    completion = thinking_fillers.get_completion_phrase()
    print(f"   {completion}")
    print("   [AI would now speak the actual response]")

    print("\nDemo complete! In VibeType, these phrases will be spoken")
    print("via your configured TTS engine while Ollama processes requests.")

if __name__ == "__main__":
    demo_thinking_fillers()
