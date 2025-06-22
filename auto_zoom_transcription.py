#!/usr/bin/env python3
"""
Auto Zoom meeting integration with real-time transcription
Automatically joins the specified Zoom meeting and transcribes microphone audio
"""

import sys
import os
import time
import threading
import subprocess
from datetime import datetime

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

# Meeting details
MEETING_ID = "74350336315"
MEETING_PASSWORD = "rHjaMHVjQVZTWxQMvGjjRabqWZVgcK.1"

def join_zoom_meeting():
    """Join the Zoom meeting using the system's default Zoom app"""
    try:
        # Construct Zoom URL
        zoom_url = f"zoommtg://zoom.us/join?confno={MEETING_ID}&pwd={MEETING_PASSWORD}"
        
        print(f"🔗 Joining Zoom meeting: {MEETING_ID}")
        print(f"📱 Opening Zoom app...")
        
        # Open Zoom URL (this will launch the Zoom app)
        subprocess.run(["open", zoom_url], check=True)
        
        print("✅ Zoom meeting launched!")
        print("💡 Please manually join the meeting in the Zoom app")
        print("🎤 Transcription will continue in the background")
        
        return True
    except Exception as e:
        print(f"❌ Error joining Zoom meeting: {e}")
        return False

def start_transcription():
    """Start real-time transcription"""
    print("🎤 Starting real-time transcription...")
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

def main():
    print("🚀 Auto Zoom Meeting + Real-time Transcription")
    print("=" * 50)
    print(f"📋 Meeting ID: {MEETING_ID}")
    print(f"🔐 Password: {MEETING_PASSWORD}")
    print("=" * 50)
    
    # Start transcription in a separate thread
    transcription_thread = threading.Thread(target=start_transcription, daemon=True)
    transcription_thread.start()
    
    # Give transcription a moment to start
    time.sleep(2)
    
    # Join Zoom meeting
    join_zoom_meeting()
    
    print("\n" + "=" * 50)
    print("🎯 System Status:")
    print("✅ Real-time transcription: ACTIVE")
    print("✅ Zoom meeting: LAUNCHED")
    print("💡 Speak clearly to see transcriptions")
    print("🛑 Press Ctrl+C to stop everything")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        print("✅ Transcription stopped")
        print("✅ Zoom meeting can be closed manually")

if __name__ == "__main__":
    main() 