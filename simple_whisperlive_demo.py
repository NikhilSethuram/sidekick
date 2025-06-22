#!/usr/bin/env python3
"""
Simple WhisperLive + Groq Demo for CalHacks
This demonstrates real-time transcription using WhisperLive with Groq backend
"""

import asyncio
import time
import numpy as np
import pyaudio
import threading
from whisper_live.client import TranscriptionClient

class SimpleWhisperLiveDemo:
    def __init__(self):
        self.whisper_client = None
        self.is_recording = False
        self.audio = pyaudio.PyAudio()
        self.sample_rate = 16000
        self.chunk_size = 1024
        self.channels = 1
        
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
            
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio processing"""
        if self.is_recording and self.whisper_client:
            try:
                # Convert audio data to numpy array
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                
                # Send to WhisperLive
                self.whisper_client.send_audio(audio_data.tobytes())
                
                # Get transcription result
                result = self.whisper_client.get_result()
                if result and result.strip():
                    print(f"🎤 Real-time: {result}")
                    print(f"   📝 WhisperLive + Groq transcription!")
                    print()
                    
                    # Process for AI actions
                    self.process_ai_actions(result)
                    
            except Exception as e:
                print(f"❌ Error processing audio: {e}")
                
        return (in_data, pyaudio.paContinue)
        
    def process_ai_actions(self, text):
        """Process transcribed text for AI-driven actions"""
        try:
            text_lower = text.lower()
            
            # Check for meeting scheduling requests
            if any(word in text_lower for word in ['schedule', 'meeting', 'appointment', 'calendar']):
                print(f"   📅 AI Action: Meeting scheduling detected!")
                print(f"      Text: {text}")
                # Here you would integrate with calendar APIs
                
            # Check for GitHub review requests
            if any(word in text_lower for word in ['review', 'github', 'pull request', 'pr', 'code review']):
                print(f"   🔍 AI Action: Code review request detected!")
                print(f"      Text: {text}")
                # Here you would integrate with GitHub API
                
            # Check for task creation
            if any(word in text_lower for word in ['task', 'todo', 'action item', 'follow up']):
                print(f"   ✅ AI Action: Task creation detected!")
                print(f"      Text: {text}")
                # Here you would integrate with task management APIs
                
        except Exception as e:
            print(f"❌ Error in AI action processing: {e}")
            
    def start_recording(self):
        """Start recording from microphone"""
        if not self.setup_whisper_client():
            print("❌ Cannot start recording without WhisperLive")
            return
            
        print("🎤 Starting real-time transcription demo...")
        print("   Speak into your microphone to see real-time transcription!")
        print("   Try saying things like:")
        print("   - 'Schedule a meeting for tomorrow at 2pm'")
        print("   - 'Review the pull request on GitHub'")
        print("   - 'Create a task to follow up with the client'")
        print("   Press Ctrl+C to stop")
        print()
        
        self.is_recording = True
        
        # Open audio stream
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self.audio_callback
        )
        
        stream.start_stream()
        
        try:
            # Keep recording until interrupted
            while self.is_recording:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping recording...")
        finally:
            stream.stop_stream()
            stream.close()
            self.cleanup()
            
    def cleanup(self):
        """Cleanup resources"""
        self.is_recording = False
        if self.whisper_client:
            self.whisper_client.close()
        self.audio.terminate()
        print("✅ Cleanup complete")

def main():
    print("🎯 CalHacks WhisperLive + Groq Real-time Transcription Demo")
    print("=" * 60)
    print()
    
    # Create demo
    demo = SimpleWhisperLiveDemo()
    
    # Start recording
    demo.start_recording()

if __name__ == "__main__":
    main() 