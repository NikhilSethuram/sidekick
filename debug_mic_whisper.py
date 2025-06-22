import pyaudio
import numpy as np
import time
from whisper_live.client import TranscriptionClient

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

def debug_microphone_whisper():
    print("🔍 Debugging microphone and WhisperLive connection...")
    
    # Initialize audio
    print("🎤 Initializing microphone...")
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=0,
        frames_per_buffer=CHUNK
    )
    print("✅ Microphone initialized")
    
    # Initialize WhisperLive client
    print("🤖 Connecting to WhisperLive...")
    try:
        whisper_client = TranscriptionClient(
            "localhost", 9090,
            lang="en", translate=False,
            model="small", use_vad=False
        )
        print("✅ WhisperLive client connected")
    except Exception as e:
        print(f"❌ WhisperLive connection failed: {e}")
        return
    
    print("🎤 Starting audio capture and processing...")
    print("💡 Speak into your microphone now!")
    print("🛑 Press Ctrl+C to stop")
    
    audio_buffer = []
    chunk_count = 0
    
    try:
        while True:
            # Read audio chunk
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)
            
            # Check audio level
            audio_level = np.abs(audio_array).mean()
            chunk_count += 1
            
            if audio_level > 100:  # Audio detected
                print(f"🎵 Chunk {chunk_count}: Audio level {audio_level:.0f}")
                
                # Convert to float32 for WhisperLive
                audio_float = audio_array.astype(np.float32) / 32768.0
                audio_buffer.extend(audio_float)
                
                # Send to WhisperLive every few chunks
                if len(audio_buffer) >= CHUNK * 2:  # Send after 2 chunks
                    try:
                        print(f"📤 Sending {len(audio_buffer)} samples to WhisperLive...")
                        
                        # Convert to int16 for WhisperLive
                        audio_int16 = (np.array(audio_buffer) * 32768.0).astype(np.int16)
                        whisper_client.send_audio(audio_int16.tobytes())
                        
                        # Get transcription result
                        result = whisper_client.get_result()
                        if result and result.strip():
                            print(f"🎤 TRANSCRIBED: {result}")
                            print("✅ WhisperLive is working!")
                        else:
                            print("⏳ No transcription result yet...")
                        
                        # Clear buffer
                        audio_buffer = []
                        
                    except Exception as e:
                        print(f"❌ WhisperLive error: {e}")
                        audio_buffer = []
            else:
                if chunk_count % 50 == 0:  # Print every 50 chunks
                    print(f"🔇 Chunk {chunk_count}: Silent (level {audio_level:.0f})")
                    
    except KeyboardInterrupt:
        print("\n🛑 Debug stopped")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        whisper_client.close()

if __name__ == "__main__":
    debug_microphone_whisper() 