#!/usr/bin/env python3
"""
Simple WhisperLive client for real-time transcription from microphone
"""

import sys
import os

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

def main():
    print("🎤 Starting WhisperLive real-time transcription...")
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
        
        # Start transcription
        client()
        
    except KeyboardInterrupt:
        print("\n🛑 Transcription stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 