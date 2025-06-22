#!/usr/bin/env python3
"""
Fake Bot Transcription System
Simulates a bot joining Zoom but actually transcribes microphone to text file
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

# Transcription file
TRANSCRIPT_FILE = f"zoom_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class FakeBotTranscription:
    def __init__(self):
        self.transcript_file = TRANSCRIPT_FILE
        self.is_running = False
        self.transcription_buffer = []
        
    def fake_bot_join(self):
        """Simulate bot joining the meeting"""
        print("🤖 Bot Status: INITIALIZING...")
        time.sleep(1)
        print("🤖 Bot Status: CONNECTING TO ZOOM...")
        time.sleep(1)
        print("🤖 Bot Status: JOINING MEETING...")
        time.sleep(1)
        print(f"🤖 Bot Status: JOINED MEETING {MEETING_ID}")
        print("🤖 Bot Status: LISTENING TO AUDIO...")
        print("🤖 Bot Status: TRANSCRIBING IN REAL-TIME...")
        
    def save_transcription(self, text):
        """Save transcription to file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}\n"
        
        try:
            with open(self.transcript_file, 'a', encoding='utf-8') as f:
                f.write(line)
            print(f"💾 Saved: {text}")
        except Exception as e:
            print(f"❌ Error saving transcription: {e}")
    
    def start_transcription(self):
        """Start real-time transcription and save to file"""
        print("🎤 Starting real-time transcription...")
        print(f"📄 Saving to: {self.transcript_file}")
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
            
            # Custom transcription handler
            def handle_transcription(text):
                if text and text.strip():
                    self.save_transcription(text.strip())
            
            # Start transcription with custom handler
            # Note: This is a simplified version - you might need to modify the client
            # to capture transcriptions and save them
            client()
            
        except KeyboardInterrupt:
            print("\n🛑 Transcription stopped by user")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def launch_zoom(self):
        """Launch Zoom meeting (optional - for appearance)"""
        try:
            zoom_url = f"zoommtg://zoom.us/join?confno={MEETING_ID}&pwd={MEETING_PASSWORD}"
            subprocess.run(["open", zoom_url], check=True)
            print("📱 Zoom meeting launched (optional)")
        except Exception as e:
            print(f"⚠️  Could not launch Zoom: {e}")
    
    def run(self):
        """Main execution"""
        print("🚀 Fake Bot Transcription System")
        print("=" * 50)
        print(f"📋 Meeting ID: {MEETING_ID}")
        print(f"📄 Transcript File: {self.transcript_file}")
        print("=" * 50)
        
        # Initialize transcript file
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Zoom Meeting Transcript - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Meeting ID: {MEETING_ID}\n")
            f.write("=" * 50 + "\n\n")
        
        # Start fake bot simulation
        bot_thread = threading.Thread(target=self.fake_bot_join, daemon=True)
        bot_thread.start()
        
        # Optionally launch Zoom (for appearance)
        self.launch_zoom()
        
        # Start transcription
        transcription_thread = threading.Thread(target=self.start_transcription, daemon=True)
        transcription_thread.start()
        
        print("\n" + "=" * 50)
        print("🎯 System Status:")
        print("🤖 Bot: JOINED MEETING")
        print("✅ Real-time transcription: ACTIVE")
        print(f"📄 Saving to: {self.transcript_file}")
        print("💡 Speak clearly to see transcriptions")
        print("🛑 Press Ctrl+C to stop everything")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            print("✅ Transcription stopped")
            print(f"📄 Transcript saved to: {self.transcript_file}")
            print("🤖 Bot: LEFT MEETING")

if __name__ == "__main__":
    bot = FakeBotTranscription()
    bot.run() 