import json
import time
import argparse
from typing import List, Tuple, Dict, Optional

# --- Configuration ---
# Set to True to use mock components, False to use real APIs
USE_MOCK = True 
# ---------------------

# Real components
from action_pipeline.intent_parser import IntentParser
from action_pipeline.executors import (
    CalendarExecutor, GitHubExecutor, SlackExecutor, TaskExecutor
)

# Mock components for demo purposes
from demo.mock_components import (
    MockCalendarExecutor, MockGitHubExecutor, MockSlackExecutor, 
    MockTaskExecutor, MockIntentParser
)


# Mock transcript scenarios for testing
DEMO_SCENARIOS = [
    {
        "name": "Schedule Meeting",
        "chunks": [
            ("Let's schedule a meeting", 0),
            ("with John next Tuesday", 2),
            ("at 2pm", 4)
        ],
        "expected_action": "schedule_meeting"
    },
    {
        "name": "Add Reviewer",
        "chunks": [
            ("Can we add Sarah", 0),
            ("as a reviewer on the auth PR", 3),
            ("in the main repo", 5)
        ],
        "expected_action": "add_reviewer"
    },
    {
        "name": "Send Slack Message", 
        "chunks": [
            ("Send John the meeting notes", 0),
            ("in the engineering channel", 2)
        ],
        "expected_action": "send_message"
    },
    {
        "name": "Create Task",
        "chunks": [
            ("Create a ticket for the login bug", 0),
            ("we discussed earlier", 2),
            ("assign it to Mike", 4)
        ],
        "expected_action": "create_task"
    }
]

class ApprovalInterface:
    """Handles user approval for actions"""
    
    def show_approval_popup(self, action_description: str, intent: Dict) -> str:
        """Show approval interface and get user choice"""
        print(f"\n{'='*60}")
        print(f"🤖 AI DETECTED ACTION")
        print(f"{'='*60}")
        print(f"Action: {action_description}")
        print(f"Confidence: {intent.get('confidence', 0)*100:.1f}%")
        print(f"Details: {intent.get('entities', {})}")
        print(f"{'='*60}")
        print("Options:")
        print("  (a) Approve - Execute this action now")
        print("  (d) Deny - Skip this action")  
        print("  (r) Remind - Ask me later")
        print("  (m) Modify - Change the action details")
        
        while True:
            choice = input("\nYour choice [a/d/r/m]: ").lower().strip()
            
            if choice in ['a', 'approve']:
                return "approved"
            elif choice in ['d', 'deny']:
                return "denied"
            elif choice in ['r', 'remind']:
                return "remind_later"
            elif choice in ['m', 'modify']:
                return "modify"
            else:
                print("Please enter 'a', 'd', 'r', or 'm'")

class MeetingAssistant:
    """Main orchestrator for the meeting assistant"""
    
    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        if self.use_mock:
            print("--- Running in MOCK mode ---")
            self.parser = MockIntentParser()
            self.executors = {
                'schedule_meeting': MockCalendarExecutor(),
                'add_reviewer': MockGitHubExecutor(),
                'send_message': MockSlackExecutor(),
                'create_task': MockTaskExecutor()
            }
        else:
            print("--- Running in LIVE mode ---")
            self.parser = IntentParser()
            self.executors = {
                'schedule_meeting': CalendarExecutor(),
                'add_reviewer': GitHubExecutor(),
                'send_message': SlackExecutor(),
                'create_task': TaskExecutor()
            }
            
        self.approval_interface = ApprovalInterface()
        
        self.stats = {
            'actions_detected': 0,
            'actions_executed': 0,
            'actions_denied': 0
        }
    
    def simulate_transcript_stream(self, scenario: Dict):
        """Simulate receiving transcript chunks over time"""
        print(f"\n🎤 Starting scenario: {scenario['name']}")
        print("Listening to meeting...")
        
        chunks = []
        for chunk_text, delay in scenario["chunks"]:
            if delay > 0:
                print(f"   ... {delay}s pause ...")
                time.sleep(delay)
            
            chunks.append(chunk_text)
            print(f"📝 Heard: '{chunk_text}'")
            
            # Check if we should process this chunk
            if len(chunks) >= 2:  # Wait for at least 2 chunks before processing
                yield chunks.copy()
        
        # Final processing with all chunks
        yield chunks
    
    def process_scenario(self, scenario: Dict):
        """Process a complete scenario"""
        print(f"\n{'🚀 PROCESSING SCENARIO: ' + scenario['name']}")
        
        for chunks in self.simulate_transcript_stream(scenario):
            # Parse intent from current chunks
            intent = self.parser.parse(chunks)
            
            if not intent or intent.get("action") == "none":
                continue

            # Only process if we have a confident, ready action
            if intent.get("ready", False) and intent.get("confidence", 0) > 0.7:
                self.stats['actions_detected'] += 1
                
                # Get user approval
                approval = self.approval_interface.show_approval_popup(
                    intent["description"], intent
                )
                
                if approval == "approved":
                    # Execute the action
                    result = self.execute_action(intent)
                    if result.get("status") == "success":
                        self.stats['actions_executed'] += 1
                        print(f"\n✅ SUCCESS: {result['action']}")
                        print(f"   Details: {result.get('details', 'N/A')}")
                    else:
                        print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
                        
                elif approval == "denied":
                    self.stats['actions_denied'] += 1
                    print(f"\n🚫 DENIED: Action skipped by user")
                    
                elif approval == "remind_later":
                    print(f"\n⏰ REMIND LATER: Action saved for later")
                    
                elif approval == "modify":
                    print(f"\n✏️ MODIFY: Action modification not implemented yet")
                
                break  # Process only one action per scenario for demo
    
    def execute_action(self, intent: Dict) -> Dict:
        """Execute an action based on the intent"""
        action_type = intent["action"]
        
        if action_type in self.executors:
            executor = self.executors[action_type]
            
            # Call the appropriate method
            if action_type == "schedule_meeting":
                return executor.schedule_meeting(intent)
            elif action_type == "add_reviewer":
                return executor.add_reviewer(intent)
            elif action_type == "send_message":
                return executor.send_message(intent)
            elif action_type == "create_task":
                return executor.create_task(intent)
        
        return {"status": "error", "error": f"No executor found for {action_type}"}
    
    def show_stats(self):
        """Display session statistics"""
        print(f"\n{'📊 SESSION STATISTICS'}")
        print(f"{'='*50}")
        print(f"Actions Detected: {self.stats['actions_detected']}")
        print(f"Actions Executed: {self.stats['actions_executed']}")
        print(f"Actions Denied: {self.stats['actions_denied']}")
        success_rate = (self.stats['actions_executed'] / max(self.stats['actions_detected'], 1)) * 100
        print(f"Success Rate: {success_rate:.1f}%")

def main():
    """Main demo function"""
    parser = argparse.ArgumentParser(description="Run the Meeting Assistant Demo.")
    parser.add_argument(
        '--live', 
        action='store_true',
        help='Run with real API calls instead of mock components.'
    )
    args = parser.parse_args()

    use_mock_mode = not args.live
    
    print("🤖 Meeting Assistant - Live Demo")
    print("="*50)
    print("This demo simulates real-time meeting transcription")
    print("and shows how AI can detect and execute actions.")
    if not use_mock_mode:
        print("\n⚠️  WARNING: Running in LIVE mode. This will make real API calls. ⚠️")
        print("Make sure your ANTHROPIC_API_KEY is set in a .env file or environment variable.")
    print("="*50)
    
    try:
        assistant = MeetingAssistant(use_mock=use_mock_mode)
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        return

    # Run through all demo scenarios
    for scenario in DEMO_SCENARIOS:
        try:
            assistant.process_scenario(scenario)
            print(f"\n{'-'*60}")
            
            # Brief pause between scenarios
            input("Press Enter to continue to next scenario...")
            
        except KeyboardInterrupt:
            print(f"\n\n🛑 Demo interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error in scenario: {e}")
            continue
    
    # Show final statistics
    assistant.show_stats()
    print(f"\n🎉 Demo completed!")

if __name__ == "__main__":
    main()