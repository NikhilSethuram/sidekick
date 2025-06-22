import requests
import time
import json
import websocket
import threading
from datetime import datetime, timedelta
import os
from groq import Groq

# Configuration
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/76995183806?pwd=wcEK4m2ED59zPezpsttvDbQX37FaTC.1"
GROQ_API_KEY = "gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Replace with your actual Groq API key

# Initialize Groq client
groq_client = Groq(api_key=GROQ_API_KEY)

def create_bot():
    """Create a new bot to join the Zoom meeting"""
    url = f"{ATTENDEE_BASE_URL}/bots"
    headers = {
        "Authorization": f"Token {ATTENDEE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "meeting_url": ZOOM_MEETING_URL,
        "bot_name": "CalHacks WhisperBot"
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

def get_bot_status(bot_id):
    """Get the current status of the bot"""
    url = f"{ATTENDEE_BASE_URL}/bots/{bot_id}"
    headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get bot status: {response.status_code}")
        return None

def get_websocket_port(bot_id):
    """Get the WebSocket port for real-time audio streaming"""
    url = f"{ATTENDEE_BASE_URL}/bots/{bot_id}/websocket_port"
    headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get('websocket_port')
    elif response.status_code == 503:
        print("⚠️ WebSocket audio streaming not available for this bot type (normal for Zoom bots)")
        return None
    else:
        print(f"❌ Failed to get WebSocket port: {response.status_code} - {response.text}")
        return None

def get_transcript(bot_id, updated_after=None):
    """Get the transcript for the bot"""
    url = f"{ATTENDEE_BASE_URL}/bots/{bot_id}/transcript"
    headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
    params = {}
    
    if updated_after:
        params['updated_after'] = updated_after.isoformat()
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get transcript: {response.status_code}")
        return []

def process_transcript_with_ai(transcript_text):
    """Process transcript text with Groq AI for action detection"""
    try:
        prompt = f"""
        Analyze this meeting transcript and identify any actionable items or requests:
        
        "{transcript_text}"
        
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
            import json
            parsed = json.loads(ai_response)
            return parsed
        except:
            return {"action_type": "general", "confidence": 0.5, "summary": ai_response, "next_steps": "Review manually"}
            
    except Exception as e:
        print(f"❌ AI processing error: {e}")
        return None

def monitor_transcript(bot_id):
    """Monitor transcript in real-time and process with AI"""
    print("📝 Starting transcript monitoring...")
    last_updated = datetime.now() - timedelta(seconds=30)  # Get last 30 seconds
    seen_utterances = set()
    
    while True:
        try:
            # Get transcript updates
            transcript_data = get_transcript(bot_id, updated_after=last_updated)
            
            if transcript_data:
                for utterance in transcript_data:
                    utterance_id = utterance.get('id')
                    if utterance_id and utterance_id not in seen_utterances:
                        seen_utterances.add(utterance_id)
                        
                        speaker = utterance.get('speaker_name', 'Unknown')
                        text = utterance.get('text', '')
                        confidence = utterance.get('confidence', 0)
                        
                        if text.strip():
                            print(f"🎤 {speaker}: {text} (confidence: {confidence:.2f})")
                            
                            # Process with AI if confidence is high enough
                            if confidence > 0.7:
                                ai_result = process_transcript_with_ai(text)
                                if ai_result:
                                    print(f"✨ AI Action Detected: {ai_result.get('action_type', 'unknown')}")
            
            # Update timestamp for next poll
            last_updated = datetime.now()
            
            # Wait before next poll
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n🛑 Transcript monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Transcript monitoring error: {e}")
            time.sleep(5)

def connect_websocket_audio(websocket_port):
    """Connect to WebSocket for real-time audio streaming"""
    if not websocket_port:
        return
    
    print(f"🎧 Connecting to WebSocket audio stream on port {websocket_port}...")
    
    def on_message(ws, message):
        # Handle incoming audio data
        print(f"🎵 Received audio chunk: {len(message)} bytes")
        # Here you would process the audio with WhisperLive
        # For now, just acknowledge receipt
    
    def on_error(ws, error):
        print(f"❌ WebSocket error: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        print("🔌 WebSocket connection closed")
    
    def on_open(ws):
        print("🔗 WebSocket connection established")
    
    try:
        ws = websocket.WebSocketApp(
            f"ws://localhost:{websocket_port}",
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        ws.run_forever()
    except Exception as e:
        print(f"❌ Failed to connect to WebSocket: {e}")

def main():
    print("🚀 Starting Zoom Bot + WhisperLive Integration")
    print(f"📅 Meeting URL: {ZOOM_MEETING_URL}")
    
    # Create bot
    bot_id = create_bot()
    if not bot_id:
        print("❌ Failed to create bot. Exiting.")
        return
    
    # Wait for bot to join
    print("⏳ Waiting for bot to join meeting...")
    max_wait = 60  # 60 seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = get_bot_status(bot_id)
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
    
    # Try to get WebSocket port (may not be available for Zoom bots)
    websocket_port = get_websocket_port(bot_id)
    
    # Start transcript monitoring in a separate thread
    transcript_thread = threading.Thread(target=monitor_transcript, args=(bot_id,))
    transcript_thread.daemon = True
    transcript_thread.start()
    
    # If WebSocket is available, connect to it
    if websocket_port:
        websocket_thread = threading.Thread(target=connect_websocket_audio, args=(websocket_port,))
        websocket_thread.daemon = True
        websocket_thread.start()
    
    print("🎯 Integration running! Press Ctrl+C to stop.")
    print("💡 Speak in the Zoom meeting to see real-time transcription and AI analysis!")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping integration...")

if __name__ == "__main__":
    main() 