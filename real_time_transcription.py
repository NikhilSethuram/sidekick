import pyaudio
import numpy as np
import time
import websocket
import json
import threading
import queue

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# WhisperLive server settings
SERVER_URL = "ws://localhost:9090"

class RealTimeTranscription:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.transcription_queue = queue.Queue()
        self.ws = None
        self.is_running = False
        
    def connect_to_server(self):
        """Connect to WhisperLive server"""
        try:
            self.ws = websocket.create_connection(SERVER_URL)
            print(f"✅ Connected to WhisperLive server at {SERVER_URL}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            return False
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio input"""
        if self.is_running:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def send_audio_to_server(self):
        """Send audio chunks to WhisperLive server"""
        while self.is_running:
            try:
                if not self.audio_queue.empty():
                    audio_chunk = self.audio_queue.get()
                    if self.ws:
                        self.ws.send(audio_chunk, websocket.ABNF.OPCODE_BINARY)
                time.sleep(0.01)  # Small delay
            except Exception as e:
                print(f"❌ Error sending audio: {e}")
                break
    
    def receive_transcriptions(self):
        """Receive transcriptions from server"""
        while self.is_running:
            try:
                if self.ws:
                    result = self.ws.recv()
                    if result:
                        try:
                            # Try to parse as JSON (for structured responses)
                            data = json.loads(result)
                            if 'text' in data:
                                print(f"🎯 Transcription: {data['text']}")
                            else:
                                print(f"📝 Server response: {data}")
                        except json.JSONDecodeError:
                            # If not JSON, treat as plain text
                            print(f"📝 Transcription: {result}")
                time.sleep(0.01)
            except Exception as e:
                if self.is_running:  # Only print error if we're supposed to be running
                    print(f"❌ Error receiving transcription: {e}")
                break
    
    def start_transcription(self):
        """Start real-time transcription"""
        print("🎤 Starting real-time transcription...")
        print("💡 Speak into your microphone now!")
        print("🛑 Press Ctrl+C to stop")
        
        # Connect to server
        if not self.connect_to_server():
            return
        
        # Initialize audio
        audio = pyaudio.PyAudio()
        
        # Open audio stream
        stream = audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=0,
            frames_per_buffer=CHUNK,
            stream_callback=self.audio_callback
        )
        
        self.is_running = True
        
        # Start threads
        audio_thread = threading.Thread(target=self.send_audio_to_server)
        transcription_thread = threading.Thread(target=self.receive_transcriptions)
        
        audio_thread.start()
        transcription_thread.start()
        
        # Start audio stream
        stream.start_stream()
        
        try:
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping transcription...")
        finally:
            self.is_running = False
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            if self.ws:
                self.ws.close()
            
            print("✅ Transcription stopped")

if __name__ == "__main__":
    transcriber = RealTimeTranscription()
    transcriber.start_transcription() 