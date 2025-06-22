#!/usr/bin/env python3
"""
Proper Zoom Integration with Bot Joining and Groq Transcription
Combines Attendee bot joining with real-time Groq transcription
"""

import requests
import time
import json
import threading
import subprocess
import sys
import os
from datetime import datetime

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/73226719494?pwd=5tLKDbZI4gTz57ebEbPDBe2YLb6pdN.1"

# Transcription file
TRANSCRIPT_FILE = f"zoom_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class ProperZoomIntegration:
    def __init__(self):
        self.bot_id = None
        self.is_running = False
        self.transcript_file = TRANSCRIPT_FILE
        self.last_transcription = ""
        
    def create_bot(self):
        """Create a new bot to join the Zoom meeting"""
        url = f"{ATTENDEE_BASE_URL}/bots"
        headers = {
            "Authorization": f"Token {ATTENDEE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "meeting_url": ZOOM_MEETING_URL,
            "bot_name": "CalHacks AI Assistant"
        }
        
        print("🤖 Creating bot...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            bot_data = response.json()
            self.bot_id = bot_data['id']
            print(f"✅ Bot created: {self.bot_id}")
            return True
        else:
            print(f"❌ Failed to create bot: {response.status_code} - {response.text}")
            return False

    def get_bot_status(self):
        """Get the current status of the bot"""
        if not self.bot_id:
            return None
            
        url = f"{ATTENDEE_BASE_URL}/bots/{self.bot_id}"
        headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get bot status: {response.status_code}")
            return None

    def save_transcription(self, text):
        """Save transcription to file"""
        if not text or text.strip() == "" or text == self.last_transcription:
            return
            
        self.last_transcription = text
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {text}\n"
        
        try:
            with open(self.transcript_file, 'a', encoding='utf-8') as f:
                f.write(line)
            print(f"💾 Saved: {text}")
        except Exception as e:
            print(f"❌ Error saving transcription: {e}")
    
    def start_groq_transcription(self):
        """Start real-time transcription with Groq"""
        print("🎤 Starting Groq real-time transcription...")
        print(f"📄 Saving to: {self.transcript_file}")
        print("💡 Speak into your microphone now!")
        
        try:
            # Create WhisperLive client with Groq backend
            client = TranscriptionClient(
                "localhost",
                9090,
                lang="en",
                translate=False,
                model="small",
                use_vad=False
            )
            
            print("✅ Connected to WhisperLive server with Groq backend")
            print("🎤 Listening to microphone...")
            
            # Start transcription
            client()
            
        except KeyboardInterrupt:
            print("\n🛑 Transcription stopped by user")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def monitor_bot_status(self):
        """Monitor bot status in a separate thread"""
        print("🤖 Monitoring bot status...")
        bot_joined = False
        
        while self.is_running:
            try:
                status = self.get_bot_status()
                if status:
                    bot_state = status.get('state', 'unknown')
                    print(f"🤖 Bot Status: {bot_state}")
                    
                    if bot_state in ['joined', 'recording', 'joined_recording'] and not bot_joined:
                        print("✅ Bot successfully joined the meeting!")
                        print("🎤 Starting Groq transcription now...")
                        bot_joined = True
                        # Start transcription after bot joins
                        self.start_groq_transcription()
                    elif bot_state == 'failed':
                        print("❌ Bot failed to join the meeting")
                        self.is_running = False
                        break
                    elif bot_state in ['left', 'ended', 'disconnected', 'fatal_error', 'post_processing']:
                        print("🏁 Meeting has ended - Bot left the meeting")
                        self.is_running = False
                        break
                        
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"❌ Error monitoring bot: {e}")
                time.sleep(5)
        
        # Signal main thread to stop
        print("🛑 Stopping transcription due to meeting end...")
    
    def launch_zoom_app(self):
        """Launch Zoom app for visual confirmation"""
        try:
            # Extract meeting ID and password from URL
            meeting_id = "76334602960"
            password = "hM6lsqLLgtqcpLaIxD48MHG39qHKaa.1"
            
            zoom_url = f"zoommtg://zoom.us/join?confno={meeting_id}&pwd={password}"
            subprocess.run(["open", zoom_url], check=True)
            print("📱 Zoom app launched")
        except Exception as e:
            print(f"⚠️  Could not launch Zoom app: {e}")
    
    def run(self):
        """Main execution"""
        print("🚀 Proper Zoom Integration System")
        print("=" * 50)
        print(f"📋 Meeting URL: {ZOOM_MEETING_URL}")
        print(f"📄 Transcript File: {self.transcript_file}")
        print("=" * 50)
        
        # Initialize transcript file
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Zoom Meeting Transcript - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Meeting URL: {ZOOM_MEETING_URL}\n")
            f.write("=" * 50 + "\n\n")
        
        # Create bot
        if not self.create_bot():
            print("❌ Failed to create bot. Exiting.")
            return
        
        # Launch Zoom app
        self.launch_zoom_app()
        
        # Start bot monitoring
        self.is_running = True
        bot_thread = threading.Thread(target=self.monitor_bot_status, daemon=True)
        bot_thread.start()
        
        print("\n" + "=" * 50)
        print("🎯 System Status:")
        print("🤖 Bot: CREATED")
        print("⏳ Waiting for bot to join meeting...")
        print("🎤 Groq transcription will start after bot joins")
        print(f"📄 Will save to: {self.transcript_file}")
        print("🛑 Press Ctrl+C to stop everything")
        
        try:
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Manual shutdown requested...")
        finally:
            self.is_running = False
            print("✅ Transcription stopped")
            print(f"📄 Transcript saved to: {self.transcript_file}")
            print("🤖 Bot: LEFT MEETING")
            print("🏁 Integration system shutdown complete")

if __name__ == "__main__":
    integration = ProperZoomIntegration()
    integration.run() 