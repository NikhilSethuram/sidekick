import pyaudio
import numpy as np
import time

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16  # Changed to int16
CHANNELS = 1
RATE = 16000

def test_microphone():
    print("🎤 Testing microphone input...")
    
    # Initialize audio
    audio = pyaudio.PyAudio()
    
    # Use device 0 (MacBook Pro Microphone)
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=0,  # Explicitly use device 0
        frames_per_buffer=CHUNK
    )
    
    print("🎤 Speak into your microphone now...")
    print("💡 Say something like: 'Hello, this is a test'")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        while True:
            # Read audio chunk
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_array = np.frombuffer(data, dtype=np.int16)
            
            # Check if there's any audio (not just silence)
            if np.abs(audio_array).mean() > 100:  # Threshold for audio detection
                print(f"🎵 Audio detected! Level: {np.abs(audio_array).mean():.0f}")
                
                # Convert to float32 for WhisperLive
                audio_float = audio_array.astype(np.float32) / 32768.0
                
                # Here you would send to WhisperLive
                # For now, just confirm audio is being captured
                print(f"   Audio sample: {audio_float[:5]}")  # Show first 5 samples
                
            time.sleep(0.1)  # Small delay
                    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()

if __name__ == "__main__":
    test_microphone() 