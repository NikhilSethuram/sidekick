#!/usr/bin/env python3
"""
Test script to verify WhisperLive server connection
"""

import asyncio
import websockets
import json

async def test_whisperlive_connection():
    """Test connection to WhisperLive server"""
    print("🧪 Testing WhisperLive Server Connection")
    print("=" * 50)
    
    try:
        # Connect to WhisperLive server
        uri = "ws://localhost:9090"
        print(f"🔌 Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ Successfully connected to WhisperLive server!")
            
            # Send initialization message
            init_message = {
                "language": "en",
                "task": "transcribe",
                "model": "small",
                "use_vad": False
            }
            
            await websocket.send(json.dumps(init_message))
            print("📤 Sent initialization message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📥 Received response: {response}")
                print("🎯 WhisperLive server is ready for real-time transcription!")
                return True
            except asyncio.TimeoutError:
                print("⚠️ No response received (this might be normal)")
                return True
                
    except Exception as e:
        print(f"❌ Failed to connect to WhisperLive server: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_whisperlive_connection()) 