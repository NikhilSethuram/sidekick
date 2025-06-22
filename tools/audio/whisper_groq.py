#!/usr/bin/env python3
"""
Simple test to verify Groq is recording microphone
"""

import sys
import time

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

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
    test_groq_microphone() 