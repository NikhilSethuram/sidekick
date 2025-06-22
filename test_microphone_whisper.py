import pyaudio
import numpy as np
import time
from whisper_live.client import TranscriptionClient

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 16000

def test_microphone_whisper():
    print("🎤 Testing microphone and WhisperLive...")
    
    # Initialize audio
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    # Initialize WhisperLive client
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
    
    print("🎤 Speak into your microphone now...")
    print("💡 Say something like: 'Hello, this is a test of the transcription system'")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        while True:
            # Read audio chunk
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.float32)
            
            if len(audio_array) > 0:
                try:
                    # Convert float32 to int16 (WhisperLive expects int16)
                    audio_int16 = (audio_array * 32768.0).astype(np.int16)
                    
                    # Send to WhisperLive
                    whisper_client.send_audio(audio_int16.tobytes())
                    
                    # Get transcription result
                    result = whisper_client.get_result()
                    if result and result.strip():
                        print(f"🎤 Transcribed: {result}")
                        
                except Exception as e:
                    # WhisperLive might not have a result yet, continue
                    pass
                    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        # Don't call close() on whisper_client as it doesn't have that method

if __name__ == "__main__":
    test_microphone_whisper() 