#!/usr/bin/env python3
"""
Simple script to monitor Attendee transcript in real-time
"""

import requests
import time
import json

def monitor_transcript(bot_id, api_key, base_url="http://localhost:8000"):
    """Monitor transcript in real-time"""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    last_transcript_length = 0
    
    print(f"🎧 Monitoring transcript for bot: {bot_id}")
    print("=" * 50)
    
    while True:
        try:
            # Get transcript
            url = f"{base_url}/api/v1/bots/{bot_id}/transcript"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            transcript = response.json()
            
            # Check for new entries
            if len(transcript) > last_transcript_length:
                new_entries = transcript[last_transcript_length:]
                last_transcript_length = len(transcript)
                
                for entry in new_entries:
                    speaker = entry.get('speaker_name', 'Unknown')
                    text = entry.get('transcription', '')
                    timestamp = entry.get('timestamp', '')
                    
                    if text.strip():
                        print(f"🎤 {speaker}: {text}")
                        if timestamp:
                            print(f"   ⏰ {timestamp}")
                        print()
            
            # Also check bot status
            status_url = f"{base_url}/api/v1/bots/{bot_id}"
            status_response = requests.get(status_url, headers=headers)
            if status_response.status_code == 200:
                status = status_response.json()
                transcription_state = status.get('transcription_state', 'unknown')
                recording_state = status.get('recording_state', 'unknown')
                
                if transcription_state != 'in_progress':
                    print(f"⚠️ Transcription state: {transcription_state}")
                if recording_state != 'in_progress':
                    print(f"⚠️ Recording state: {recording_state}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(2)  # Check every 2 seconds

if __name__ == "__main__":
    BOT_ID = "bot_TQ7CBSdwllQVEDUn"
    API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
    
    monitor_transcript(BOT_ID, API_KEY) 