#!/usr/bin/env python3
"""
Simple test to verify Groq is recording microphone
"""

import sys
import time

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

def run_transcription_client(on_transcription):
    """
    Initializes and runs the TranscriptionClient with a callback for transcriptions.

    Args:
        on_transcription (callable): A function to be called when a transcription is received.
                                     It should accept a single string argument.
    """
    try:
        client = TranscriptionClient(
            "localhost",
            9090,
            lang="en",
            translate=False,
            model="small",
            use_vad=False,
            transcription_callback=lambda text, segments: on_transcription(text)
        )
        print("✅ Connected to WhisperLive server")
        print("🎤 Listening to microphone...")
        client()
    except KeyboardInterrupt:
        print("\n🛑 Transcription stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_groq_microphone():
    print("🎤 Testing Groq Microphone Recording...")
    print("💡 Speak into your microphone now!")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        # Create client
        client = TranscriptionClient(
            "localhost",
            9090,
            lang="en",
            translate=False,
            model="small",
            use_vad=False
        )
        
        print("✅ Connected to WhisperLive server")
        print("🎤 Listening to microphone...")
        
        # Start transcription
        client()
        
    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Example of how to use the new function with a simple printer callback
    def print_transcription(text):
        print("TRANSCRIPTION:", text)

    run_transcription_client(print_transcription) 