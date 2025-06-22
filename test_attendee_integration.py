import os
from attendee_whisperlive_integration import AttendeeWhisperLiveIntegration

def test_attendee_setup():
    """Test the Attendee integration setup"""
    print("🧪 Testing Attendee + WhisperLive Integration")
    print("=" * 50)
    
    # Test configuration
    api_key = os.getenv("ATTENDEE_API_KEY", "test_key")
    test_meeting_url = "https://zoom.us/j/123456789?pwd=test"
    
    # Create integration
    integration = AttendeeWhisperLiveIntegration(api_key)
    
    # Test WhisperLive connection
    print("1. Testing WhisperLive connection...")
    integration.setup_whisper_client()
    
    # Test meeting join (this will fail without proper credentials, but tests the structure)
    print("\n2. Testing meeting join API call...")
    try:
        result = integration.join_meeting(test_meeting_url, "TestBot")
        if result:
            print("✅ Meeting join API call successful")
        else:
            print("⚠️ Meeting join failed (expected without proper credentials)")
    except Exception as e:
        print(f"⚠️ Expected error (no credentials): {e}")
    
    print("\n3. Integration test complete!")
    print("\n📋 Next steps:")
    print("   - Set up Attendee with proper credentials")
    print("   - Get API key from Attendee UI")
    print("   - Configure Zoom OAuth credentials")
    print("   - Test with real meeting URL")

if __name__ == "__main__":
    test_attendee_setup() 