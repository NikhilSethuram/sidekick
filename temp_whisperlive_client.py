
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
