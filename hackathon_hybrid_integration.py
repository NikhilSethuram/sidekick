import requests
import time
import json
import threading
import pyaudio
import numpy as np
import websocket
from datetime import datetime, timedelta
import os
from groq import Groq
from whisper_live.client import TranscriptionClient

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/75735743724?pwd=asK0bOJQwoNYvDaku01izCJblCzMbE.1"
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your actual Groq API key

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

class HackathonHybridIntegration:
    def __init__(self):
        self.bot_id = None
        self.is_running = False
        self.whisper_client = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
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
            print(f"✅ Bot created: {bot_data['id']}")
            return bot_data['id']
        else:
            print(f"❌ Failed to create bot: {response.status_code} - {response.text}")
            return None

    def get_bot_status(self, bot_id):
        """Get the current status of the bot"""
        url = f"{ATTENDEE_BASE_URL}/bots/{bot_id}"
        headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get bot status: {response.status_code}")
            return None

    def setup_whisper_client(self):
        """Initialize WhisperLive client with Groq backend"""
        try:
            self.whisper_client = TranscriptionClient(
                "localhost", 9090,
                lang="en", translate=False,
                model="small", use_vad=False
            )
            print("✅ WhisperLive client initialized with Groq backend")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize WhisperLive client: {e}")
            return False

    def setup_microphone(self):
        """Setup microphone for audio input"""
        try:
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            print("🎤 Microphone initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to setup microphone: {e}")
            return False

    def process_audio_with_ai(self, text):
        """Process transcribed text with Groq AI for action detection"""
        try:
            prompt = f"""
            Analyze this meeting transcript and identify any actionable items or requests:
            
            "{text}"
            
            Look for:
            1. Meeting scheduling requests
            2. Task assignments
            3. Code review requests
            4. Action items
            5. Important decisions
            
            Respond with a JSON object containing:
            - action_type: The type of action detected
            - confidence: 0-1 confidence score
            - summary: Brief summary of the action
            - next_steps: What should be done next
            """
            
            response = groq_client.chat.completions.create(
                model="llama3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content
            print(f"🤖 AI Analysis: {ai_response}")
            
            # Try to parse JSON response
            try:
                parsed = json.loads(ai_response)
                return parsed
            except:
                return {"action_type": "general", "confidence": 0.5, "summary": ai_response, "next_steps": "Review manually"}
                
        except Exception as e:
            print(f"❌ AI processing error: {e}")
            return None

    def monitor_microphone(self):
        """Monitor microphone input and process with WhisperLive"""
        print("🎤 Starting microphone monitoring...")
        print("💡 Speak into your microphone to see real-time transcription and AI analysis!")
        
        try:
            while self.is_running:
                # Read audio chunk
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                
                # Convert to numpy array
                audio_array = np.frombuffer(data, dtype=np.float32)
                
                # Send to WhisperLive
                if self.whisper_client and len(audio_array) > 0:
                    try:
                        # Convert float32 to int16 (WhisperLive expects int16)
                        audio_int16 = (audio_array * 32768.0).astype(np.int16)
                        
                        # Send to WhisperLive
                        self.whisper_client.send_audio(audio_int16.tobytes())
                        
                        # Get transcription result
                        result = self.whisper_client.get_result()
                        if result and result.strip():
                            print(f"🎤 You: {result}")
                            print(f"   📝 Real-time WhisperLive transcription with Groq!")
                            
                            # Process with AI
                            ai_result = self.process_audio_with_ai(result)
                            if ai_result:
                                print(f"   ✨ AI Action Detected: {ai_result.get('action_type', 'unknown')}")
                                print(f"   📋 Summary: {ai_result.get('summary', 'N/A')}")
                                print(f"   🎯 Next Steps: {ai_result.get('next_steps', 'N/A')}")
                            print()
                            
                    except Exception as e:
                        # WhisperLive might not have a result yet, continue
                        pass
                
        except KeyboardInterrupt:
            print("\n🛑 Microphone monitoring stopped")
        except Exception as e:
            print(f"❌ Microphone monitoring error: {e}")

    def monitor_bot_status(self):
        """Monitor bot status in background"""
        print("📊 Monitoring bot status...")
        
        while self.is_running:
            try:
                status = self.get_bot_status(self.bot_id)
                if status:
                    state = status.get('state')
                    transcription_state = status.get('transcription_state', 'unknown')
                    recording_state = status.get('recording_state', 'unknown')
                    
                    print(f"📊 Bot status: {state} | Transcription: {transcription_state} | Recording: {recording_state}")
                    
                    if state in ['ended', 'failed', 'left']:
                        print("🏁 Bot session ended")
                        break
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"❌ Bot status monitoring error: {e}")
                time.sleep(5)

    def run(self):
        """Main integration function"""
        print("🚀 Starting Hackathon Hybrid Integration")
        print(f"📅 Meeting URL: {ZOOM_MEETING_URL}")
        print("🎯 This will join a real Zoom meeting AND process your microphone with AI!")
        
        # Create bot
        self.bot_id = self.create_bot()
        if not self.bot_id:
            print("❌ Failed to create bot. Exiting.")
            return
        
        # Wait for bot to join
        print("⏳ Waiting for bot to join meeting...")
        max_wait = 60  # 60 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = self.get_bot_status(self.bot_id)
            if status:
                state = status.get('state')
                print(f"📊 Bot status: {state}")
                
                if state in ['joined_recording', 'joined']:
                    print("✅ Bot successfully joined and recording")
                    break
                elif state in ['failed', 'left']:
                    print(f"❌ Bot failed to join: {state}")
                    return
            
            time.sleep(2)
        
        if time.time() - start_time >= max_wait:
            print("⏰ Timeout waiting for bot to join")
            return
        
        # Setup WhisperLive
        if not self.setup_whisper_client():
            print("❌ Cannot continue without WhisperLive")
            return
        
        # Setup microphone
        if not self.setup_microphone():
            print("❌ Cannot continue without microphone")
            return
        
        # Start monitoring
        self.is_running = True
        
        # Start bot status monitoring in background
        bot_thread = threading.Thread(target=self.monitor_bot_status)
        bot_thread.daemon = True
        bot_thread.start()
        
        print("🎯 Hybrid integration running!")
        print("💡 The bot is in the Zoom meeting, and your microphone is being processed with AI!")
        print("🎤 Speak into your microphone to see real-time transcription and AI analysis!")
        print("🛑 Press Ctrl+C to stop")
        
        try:
            # Start microphone monitoring (this will block)
            self.monitor_microphone()
        except KeyboardInterrupt:
            print("\n🛑 Stopping integration...")
        finally:
            # Cleanup
            self.is_running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
            if self.whisper_client:
                self.whisper_client.close()
            print("🧹 Cleanup complete")

def main():
    integration = HackathonHybridIntegration()
    integration.run()

if __name__ == "__main__":
    main() 