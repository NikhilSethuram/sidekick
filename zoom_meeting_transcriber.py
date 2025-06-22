#!/usr/bin/env python3
"""
Zoom Meeting Transcriber
"""

import requests
import time
import sys
import threading
import subprocess
from datetime import datetime

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/72201851531?pwd=dGBCv75I7MDMcvgF0u3enf16M40aO5.1"
class ZoomMeetingTranscriber:
    def __init__(self):
        """Initialize Zoom meeting transcriber"""
        self.transcript_file = f"transcript.txt"
        self.whisper_client = None
        self.bot_id = None
        self.bot_joined = False
        self.is_running = True
        
        print("🎤 Zoom Meeting Transcriber Initialized")
        print(f"📋 Meeting: {ZOOM_MEETING_URL}")
        print(f"📄 Saving to: {self.transcript_file}")
        
        # Initialize transcript file
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Zoom Meeting Transcript - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Meeting: {ZOOM_MEETING_URL}\n")
            f.write("=" * 50 + "\n\n")

    # =================== ZOOM BOT MANAGEMENT ===================
    
    def create_zoom_bot(self):
        """Create a bot to join the Zoom meeting"""
        url = f"{ATTENDEE_BASE_URL}/bots"
        headers = {
            "Authorization": f"Token {ATTENDEE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "meeting_url": ZOOM_MEETING_URL,
            "bot_name": "Sidekick",
            "metadata": {
                "purpose": "Meeting transcription",
                "created_by": "zoom_meeting_transcriber"
            }
        }
        
        print("🤖 Creating Zoom bot...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            bot_data = response.json()
            self.bot_id = bot_data['id']
            print(f"✅ Bot created successfully: {self.bot_id}")
            return True
        else:
            print(f"❌ Failed to create bot: {response.status_code} - {response.text}")
            return False

    def get_bot_status(self):
        """Get current bot status"""
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

    def monitor_bot_status(self):
        """Monitor bot status and start transcription when bot joins"""
        print("👀 Monitoring bot status...")
        
        while self.is_running:
            try:
                bot_data = self.get_bot_status()
                if bot_data:
                    bot_state = bot_data.get('state', 'unknown')
                    
                    if not self.bot_joined:
                        if bot_state in ['joining', 'waiting_room']:
                            print(f"🤖 Bot Status: {bot_state}")
                        elif bot_state in ['joined', 'joined_recording', 'joined_not_recording', 'in_meeting']:
                            print(f"✅ Bot joined meeting! Status: {bot_state}")
                            self.bot_joined = True
                            # Start transcription
                            self._start_transcription()
                        elif bot_state in ['failed', 'fatal_error']:
                            print(f"❌ Bot failed to join: {bot_state}")
                            self.is_running = False
                            break
                    else:
                        # Bot already joined, check if meeting ended
                        if bot_state in ['left', 'ended', 'post_processing']:
                            print(f"🏁 Meeting ended - Bot status: {bot_state}")
                            self.is_running = False
                            break
                        
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"❌ Error monitoring bot: {e}")
                time.sleep(5)

    def launch_zoom_app(self):
        """Launch Zoom app for user to see the meeting"""
        try:
            # Extract meeting details from URL
            meeting_id = ZOOM_MEETING_URL.split("/j/")[1].split("?")[0]
            password = ZOOM_MEETING_URL.split("pwd=")[1]
            
            zoom_url = f"zoommtg://zoom.us/join?confno={meeting_id}&pwd={password}"
            subprocess.run(["open", zoom_url], check=True)
            print("📱 Zoom app launched for you to join manually")
        except Exception as e:
            print(f"⚠️  Could not launch Zoom app: {e}")

    # =================== TRANSCRIPTION ===================
    
    def _on_transcription_received(self, text: str, segments=None):
        """Handle new transcription from WhisperLive"""
        if not text or not text.strip():
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Show live transcription
        print(f"🎤 [{timestamp}] {text}")
        
        # Save to transcript file
        try:
            with open(self.transcript_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {text}\n")
        except Exception as e:
            print(f"❌ Error saving transcript: {e}")
    
    def _start_transcription(self):
        """Start WhisperLive transcription in separate thread"""
        print("🎤 Starting real-time meeting transcription...")
        
        def transcription_worker():
            try:
                self.whisper_client = TranscriptionClient(
                    "localhost",
                    9090,
                    lang="en",
                    translate=False,
                    model="small",
                    use_vad=True,
                    no_speech_thresh=0.2,
                    transcription_callback=self._on_transcription_received
                )
                
                print("✅ Connected to WhisperLive server")
                print("🎤 Listening to meeting audio...")
                print("💡 All speech will be transcribed and saved to file")
                
                # Start transcription (this blocks)
                self.whisper_client()
                
            except Exception as e:
                print(f"❌ WhisperLive error: {e}")
                self.is_running = False
        
        # Start transcription in separate thread
        transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
        transcription_thread.start()

    # =================== TRANSCRIPT PROCESSING ===================
    
    def _process_transcript_for_streamlit(self):
        """Process the generated transcript and update main_graph.py for Streamlit interface"""
        try:
            import subprocess
            import sys
            
            print("🔄 Running transcript integration script...")
            
            # Use the dedicated update_transcript.py script
            result = subprocess.run([
                sys.executable, 'update_transcript.py', self.transcript_file
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Successfully integrated transcript with Streamlit interface")
                print(result.stdout)
            else:
                print(f"⚠️  Transcript integration warning: {result.stderr}")
                # Try auto-integration as fallback
                result = subprocess.run([
                    sys.executable, 'update_transcript.py'
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print("✅ Fallback auto-integration successful")
                    print(result.stdout)
                else:
                    print(f"❌ Failed to integrate transcript: {result.stderr}")
            
        except Exception as e:
            print(f"❌ Error processing transcript for Streamlit: {e}")
            print("💡 You can manually run: python update_transcript.py")
    
    # =================== MAIN EXECUTION ===================
    
    def _finalize_transcript(self):
        """Finalize transcript file and update main_graph.py for Streamlit"""
        try:
            with open(self.transcript_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\nMeeting ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"\n📄 Final transcript saved to: {self.transcript_file}")
            
            # Process transcript for Streamlit interface
            print("🔄 Processing transcript for Streamlit interface...")
            self._process_transcript_for_streamlit()
            
        except Exception as e:
            print(f"❌ Error finalizing transcript: {e}")

    def run(self):
        """Main execution"""
        print("🚀 Starting Zoom Meeting Transcriber")
        print("=" * 50)
        
        # Create and join Zoom meeting
        if not self.create_zoom_bot():
            print("❌ Failed to create bot. Exiting.")
            return
        
        # Launch Zoom app for user
        self.launch_zoom_app()
        
        print("\n" + "=" * 50)
        print("🎯 SYSTEM STATUS:")
        print("🤖 Zoom Bot: CREATED & JOINING")
        print("⏳ Waiting for bot to join meeting...")
        print("🎤 Transcription will start once bot joins")
        print("🛑 Press Ctrl+C to stop")
        print("=" * 50)
        
        # Start bot monitoring
        self.is_running = True
        bot_thread = threading.Thread(target=self.monitor_bot_status, daemon=True)
        bot_thread.start()
        
        try:
            # Keep main thread alive
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Transcription stopped by user")
        finally:
            self.is_running = False
            self._finalize_transcript()
            
            print("\n" + "=" * 50)
            print("✅ TRANSCRIPTION COMPLETE")
            print(f"📄 Transcript saved to: {self.transcript_file}")
            print("🏁 Zoom Meeting Transcriber Shutdown Complete")
            print("=" * 50)

def main():
    """Main function"""
    transcriber = ZoomMeetingTranscriber()
    transcriber.run()

if __name__ == "__main__":
    main() 