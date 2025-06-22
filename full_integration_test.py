#!/usr/bin/env python3
"""
Full Integration Test: Zoom Bot + Real-time Transcription + Agent Processing
"""

import requests
import time
import json
import threading
import subprocess
import sys
import os
from datetime import datetime
from langchain_core.messages import HumanMessage

# Import the main graph
from core.main_graph import graph

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/75723665614?pwd=rZTszQ9IGCiED5cD9SHgz4rK0p9cP1.1"

class FullIntegrationTest:
    def __init__(self):
        self.bot_id = None
        self.is_running = False
        self.transcript_buffer = []
        self.last_processed_transcript = ""
        self.whisperlive_process = None
        
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

    def process_transcript_with_agents(self, transcript: str):
        """Process transcription through the agent system"""
        if not transcript or transcript.strip() == "" or transcript == self.last_processed_transcript:
            return
            
        self.last_processed_transcript = transcript
        print(f"\n🎯 PROCESSING TRANSCRIPT: {transcript}")
        
        try:
            # Prepare the initial state for the graph
            initial_state = {
                "messages": [HumanMessage(content=transcript)],
            }
            
            print("🤖 Invoking agent system...")
            # Invoke the graph
            final_state = None
            for step in graph.stream(initial_state, {"recursion_limit": 15}):
                step_name = list(step.keys())[0]
                print(f"  → {step_name}")
                final_state = step

            if final_state:
                print("✅ Agent processing complete!")
                # Get the final response
                final_message = final_state[list(final_state.keys())[0]]['messages'][-1]
                print(f"🤖 Agent Response: {final_message.content}")
                
        except Exception as e:
            print(f"❌ Error processing transcript: {e}")

    def start_groq_transcription(self):
        """Start real-time transcription with Groq using subprocess"""
        print("🎤 Starting Groq real-time transcription...")
        print("💡 Speak into your microphone now!")
        print("🤖 Agent system will process your commands in real-time!")
        
        try:
            # Create a simple WhisperLive client script in whisperlive_env
            whisperlive_script = """
import sys
import os
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient
import json

def transcription_callback(transcript, segments):
    if transcript and transcript.strip():
        print(f"TRANSCRIPT: {transcript}")
        sys.stdout.flush()

try:
    client = TranscriptionClient(
        "localhost",
        9090,
        lang="en",
        translate=False,
        model="small",
        use_vad=False,
        transcription_callback=transcription_callback
    )
    
    print("CONNECTED")
    sys.stdout.flush()
    
    client()
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.stdout.flush()
"""
            
            # Write the script to a temporary file
            script_path = "temp_whisperlive_client.py"
            with open(script_path, "w") as f:
                f.write(whisperlive_script)
            
            # Run the script in whisperlive_env
            env = os.environ.copy()
            env['PATH'] = f"{os.path.abspath('whisperlive_env/bin')}:{env['PATH']}"
            env['PYTHONPATH'] = f"{os.path.abspath('whisperlive_env/WhisperLive')}:{env.get('PYTHONPATH', '')}"
            
            self.whisperlive_process = subprocess.Popen(
                [f"{os.path.abspath('whisperlive_env/bin/python')}", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
                universal_newlines=True
            )
            
            print("✅ WhisperLive client started")
            
            # Monitor the output
            def monitor_transcription():
                while self.is_running and self.whisperlive_process.poll() is None:
                    line = self.whisperlive_process.stdout.readline()
                    if line:
                        line = line.strip()
                        if line.startswith("TRANSCRIPT: "):
                            transcript = line[12:]  # Remove "TRANSCRIPT: " prefix
                            print(f"🎤 Heard: {transcript}")
                            # Process with agents
                            self.process_transcript_with_agents(transcript)
                        elif line == "CONNECTED":
                            print("✅ WhisperLive connected to server")
                        elif line.startswith("ERROR: "):
                            print(f"❌ WhisperLive error: {line[7:]}")
            
            # Start monitoring in a separate thread
            threading.Thread(target=monitor_transcription, daemon=True).start()
            
        except Exception as e:
            print(f"❌ Error starting WhisperLive: {e}")
    
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
        
        print("🛑 Stopping transcription due to meeting end...")
    
    def launch_zoom_app(self):
        """Launch Zoom app for visual confirmation"""
        try:
            # Extract meeting ID and password from URL
            meeting_id = "75365573701"
            password = "NH3JuFqVaU2abhZprEU45Db0P4HyGq.1"
            
            zoom_url = f"zoommtg://zoom.us/join?confno={meeting_id}&pwd={password}"
            subprocess.run(["open", zoom_url], check=True)
            print("📱 Zoom app launched")
        except Exception as e:
            print(f"⚠️  Could not launch Zoom app: {e}")
    
    def run(self):
        """Main execution"""
        print("🚀 FULL INTEGRATION TEST")
        print("=" * 60)
        print("🎯 Zoom Bot + Real-time Transcription + Agent Processing")
        print("=" * 60)
        print(f"📋 Meeting URL: {ZOOM_MEETING_URL}")
        
        # Launch Zoom app
        self.launch_zoom_app()
        
        # Create bot
        if not self.create_bot():
            return
        
        self.is_running = True
        
        # Start monitoring bot status
        self.monitor_bot_status()
        
        # Cleanup
        if self.whisperlive_process:
            self.whisperlive_process.terminate()
        
        # Clean up temporary file
        try:
            os.remove("temp_whisperlive_client.py")
        except:
            pass
        
        print("🏁 Integration test completed")

if __name__ == "__main__":
    test = FullIntegrationTest()
    try:
        test.run()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        test.is_running = False
        if test.whisperlive_process:
            test.whisperlive_process.terminate() 