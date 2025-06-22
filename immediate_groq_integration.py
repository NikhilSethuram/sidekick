import requests
import time
import json
import threading
import pyaudio
import numpy as np
from datetime import datetime, timedelta
import os
from groq import Groq
from whisper_live.client import TranscriptionClient

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/73835063753?pwd=cEkds6gogAyNU01DRFa8QDw5eE1btQ.1"
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your actual Groq API key

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

class ImmediateGroqIntegration:
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
                input_device_index=0,
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
        """Monitor microphone input and process with WhisperLive + Groq"""
        print("🎤 Starting microphone monitoring...")
        print("💡 Speak into your microphone to see real-time transcription and AI analysis!")
        print("🚀 Groq processing is ACTIVE - speak now!")
        
        audio_buffer = []
        silence_counter = 0
        
        try:
            while self.is_running:
                # Read audio chunk
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                
                # Check if there's significant audio
                audio_level = np.abs(audio_array).mean()
                
                if audio_level > 100:  # Audio detected
                    silence_counter = 0
                    # Convert to float32 for WhisperLive
                    audio_float = audio_array.astype(np.float32) / 32768.0
                    audio_buffer.extend(audio_float)
                    
                    # Send to WhisperLive
                    if self.whisper_client and len(audio_buffer) >= CHUNK:
                        try:
                            # Convert to int16 for WhisperLive
                            audio_int16 = (np.array(audio_buffer) * 32768.0).astype(np.int16)
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
                                
                                # Clear buffer after processing
                                audio_buffer = []
                                
                        except Exception as e:
                            # WhisperLive might not have a result yet, continue
                            pass
                else:
                    silence_counter += 1
                    # Clear buffer after silence
                    if silence_counter > 10:  # 1 second of silence
                        audio_buffer = []
                        silence_counter = 0
                
        except KeyboardInterrupt:
            print("\n🛑 Microphone monitoring stopped")
        except Exception as e:
            print(f"❌ Microphone monitoring error: {e}")

    def monitor_bot_status(self):
        """Monitor bot status in background"""
        print("📊 Monitoring bot status in background...")
        
        while self.is_running:
            try:
                if self.bot_id:
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
        """Main integration function - starts Groq immediately!"""
        print("🚀 Starting Immediate Groq Integration")
        print(f"📅 Meeting URL: {ZOOM_MEETING_URL}")
        print("🎯 Groq processing starts IMMEDIATELY, bot joins in background!")
        
        # Setup WhisperLive FIRST (before bot)
        print("🤖 Setting up WhisperLive + Groq...")
        if not self.setup_whisper_client():
            print("❌ Cannot continue without WhisperLive")
            return
        
        # Setup microphone FIRST (before bot)
        print("🎤 Setting up microphone...")
        if not self.setup_microphone():
            print("❌ Cannot continue without microphone")
            return
        
        # Start monitoring immediately
        self.is_running = True
        
        # Start microphone monitoring IMMEDIATELY (this is the main feature)
        print("🎤 Starting microphone monitoring IMMEDIATELY...")
        mic_thread = threading.Thread(target=self.monitor_microphone)
        mic_thread.daemon = True
        mic_thread.start()
        
        # Create bot in background
        print("🤖 Creating bot in background...")
        self.bot_id = self.create_bot()
        
        # Start bot status monitoring in background
        bot_thread = threading.Thread(target=self.monitor_bot_status)
        bot_thread.daemon = True
        bot_thread.start()
        
        print("🎯 Integration running!")
        print("💡 Groq is processing your microphone RIGHT NOW!")
        print("🎤 Speak into your microphone to see real-time AI analysis!")
        print("🤖 Bot is joining the meeting in the background...")
        print("🛑 Press Ctrl+C to stop")
        
        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
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
    integration = ImmediateGroqIntegration()
    integration.run()

if __name__ == "__main__":
    main() 