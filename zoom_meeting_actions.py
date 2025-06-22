#!/usr/bin/env python3
"""
Integrated Zoom Meeting Actions System
Combines Attendee bot (for joining Zoom) + WhisperLive (for transcription) + Agent System (for actions)

The bot joins the meeting and "pretends" to listen while WhisperLive actually processes audio
and executes real-time actions through the agent system.
"""

import requests
import time
import json
import threading
import subprocess
import sys
import os
import hashlib
from datetime import datetime
from collections import deque
from typing import Set, List

# Add WhisperLive to path
sys.path.append('whisperlive_env/WhisperLive')

from whisper_live.client import TranscriptionClient
from core.main_graph import command_extractor_node, agent_execution_graph
from core.state import AgentState

# Configuration - Update with your meeting URL
ATTENDEE_API_KEY = "81d137awvcp1aK5tSxxyrNoEX6dhjQXg"
ATTENDEE_BASE_URL = "http://localhost:8000/api/v1"
ZOOM_MEETING_URL = "https://us04web.zoom.us/j/71455358172?pwd=4lJCKKiaExPDnYTsvFaMOvdvsEvoxP.1"

class ZoomMeetingActions:
    def __init__(self, buffer_window_seconds=30, cooldown_seconds=3):
        """
        Integrated Zoom + WhisperLive + Agent system
        
        Args:
            buffer_window_seconds: Rolling transcript window size
            cooldown_seconds: Minimum time between processing same command
        """
        self.buffer_window_seconds = buffer_window_seconds
        self.cooldown_seconds = cooldown_seconds
        
        # Zoom bot management
        self.bot_id = None
        self.bot_joined = False
        self.is_running = False
        
        # Real-time transcript processing (from our realtime_meeting_actions.py)
        self.transcript_buffer = deque()
        self.executed_actions: Set[str] = set()
        self.processing_actions: Set[str] = set()
        self.last_processing_time = {}
        
        # WhisperLive client
        self.whisper_client = None
        self.processing_thread = None
        self.process_lock = threading.Lock()
        
        # Logging
        self.transcript_file = f"zoom_meeting_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.actions_file = f"zoom_meeting_actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.executed_actions_log = []
        
        print("🚀 Zoom Meeting Actions System Initialized")
        print(f"📋 Meeting: {ZOOM_MEETING_URL}")
        print(f"📊 Buffer: {buffer_window_seconds}s, Cooldown: {cooldown_seconds}s")

    # =================== ZOOM BOT MANAGEMENT ===================
    
    def create_zoom_bot(self):
        """Create a bot to join the Zoom meeting"""
        url = f"{ATTENDEE_BASE_URL}/bots"
        headers = {
            "Authorization": f"Token {ATTENDEE_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "meeting_url": ZOOM_MEETING_URL,
            "bot_name": "CalHacks AI Meeting Assistant",
            "metadata": {
                "purpose": "AI-powered meeting actions",
                "created_by": "realtime_meeting_actions_system"
            }
        }
        
        print("🤖 Creating Zoom bot...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            bot_data = response.json()
            self.bot_id = bot_data['id']
            print(f"✅ Bot created successfully: {self.bot_id}")
            return True
        else:
            print(f"❌ Failed to create bot: {response.status_code} - {response.text}")
            return False

    def get_bot_status(self):
        """Get current bot status"""
        if not self.bot_id:
            return None
            
        url = f"{ATTENDEE_BASE_URL}/bots/{self.bot_id}"
        headers = {"Authorization": f"Token {ATTENDEE_API_KEY}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Failed to get bot status: {response.status_code}")
            return None

    def monitor_bot_status(self):
        """Monitor bot status and trigger transcription when bot joins"""
        print("👀 Monitoring bot status...")
        
        while self.is_running:
            try:
                status = self.get_bot_status()
                if status:
                    bot_state = status.get('state', 'unknown')
                    
                    if not self.bot_joined:
                        if bot_state in ['joining', 'ready']:
                            print(f"🤖 Bot Status: {bot_state}")
                        elif bot_state in ['joined', 'recording', 'joined_recording', 'joined_not_recording']:
                            print(f"✅ Bot joined meeting! Status: {bot_state}")
                            self.bot_joined = True
                            # Start the real-time processing
                            self._start_realtime_processing()
                        elif bot_state in ['failed', 'fatal_error']:
                            print(f"❌ Bot failed to join: {bot_state}")
                            self.is_running = False
                            break
                    else:
                        # Bot already joined, check if meeting ended
                        if bot_state in ['left', 'ended', 'post_processing']:
                            print(f"🏁 Meeting ended - Bot status: {bot_state}")
                            self.is_running = False
                            break
                        
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"❌ Error monitoring bot: {e}")
                time.sleep(5)

    def launch_zoom_app(self):
        """Launch Zoom app for user to see the meeting"""
        try:
            # Extract meeting details from URL
            meeting_id = ZOOM_MEETING_URL.split("/j/")[1].split("?")[0]
            password = ZOOM_MEETING_URL.split("pwd=")[1]
            
            zoom_url = f"zoommtg://zoom.us/join?confno={meeting_id}&pwd={password}"
            subprocess.run(["open", zoom_url], check=True)
            print("📱 Zoom app launched for you to join manually")
        except Exception as e:
            print(f"⚠️  Could not launch Zoom app: {e}")

    # =================== REAL-TIME PROCESSING (from realtime_meeting_actions.py) ===================
    
    def _create_action_signature(self, command_text: str) -> str:
        """Create unique signature for command deduplication"""
        normalized = command_text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def _cleanup_old_entries(self):
        """Remove old transcript entries and expired actions"""
        current_time = time.time()
        cutoff_time = current_time - self.buffer_window_seconds
        
        # Clean transcript buffer
        while self.transcript_buffer and self.transcript_buffer[0][1] < cutoff_time:
            self.transcript_buffer.popleft()
        
        # Clean expired action signatures (older than 5 minutes)
        expired_cutoff = current_time - 300
        expired_actions = {
            action for action, timestamp in self.last_processing_time.items() 
            if timestamp < expired_cutoff
        }
        
        for action in expired_actions:
            self.executed_actions.discard(action)
            self.processing_actions.discard(action)
            del self.last_processing_time[action]

    def _get_current_transcript(self) -> List[str]:
        """Get current transcript buffer as list of strings"""
        self._cleanup_old_entries()
        return [text for text, _ in self.transcript_buffer]

    def _should_process_command(self, command_text: str) -> bool:
        """Check if command should be processed (not duplicate/recent)"""
        signature = self._create_action_signature(command_text)
        current_time = time.time()
        
        if signature in self.executed_actions or signature in self.processing_actions:
            return False
        
        if signature in self.last_processing_time:
            if current_time - self.last_processing_time[signature] < self.cooldown_seconds:
                return False
        
        return True

    def _mark_action_processing(self, command_text: str):
        """Mark action as currently being processed"""
        signature = self._create_action_signature(command_text)
        self.processing_actions.add(signature)
        self.last_processing_time[signature] = time.time()

    def _mark_action_completed(self, command_text: str, success: bool = True, tool_calls=None):
        """Mark action as completed and log it"""
        signature = self._create_action_signature(command_text)
        self.processing_actions.discard(signature)
        
        if success:
            self.executed_actions.add(signature)
            
            # Log the action
            action_log = {
                "timestamp": datetime.now().isoformat(),
                "command": command_text,
                "success": True,
                "tool_calls": tool_calls or [],
                "signature": signature
            }
            self.executed_actions_log.append(action_log)
            
            print(f"✅ MEETING ACTION COMPLETED: {command_text}")
            if tool_calls:
                for tc in tool_calls:
                    print(f"    🔧 Executed: {tc.get('name', 'unknown')} - {tc.get('args', {})}")
        else:
            print(f"❌ MEETING ACTION FAILED: {command_text}")

    def _process_transcript_for_commands(self):
        """Process current transcript for actionable commands"""
        with self.process_lock:
            try:
                current_transcript = self._get_current_transcript()
                
                if len(current_transcript) < 2:
                    return
                
                print(f"🔄 Processing meeting transcript ({len(current_transcript)} lines)")
                
                # Extract commands using our main graph system
                initial_state = {"transcript": current_transcript, "messages": []}
                result = command_extractor_node(initial_state)
                extracted_commands = result.get("messages", [])
                
                if not extracted_commands:
                    return
                
                print(f"🎯 Found {len(extracted_commands)} potential meeting actions")
                
                # Process each command through the agent system
                for command_msg in extracted_commands:
                    command_text = command_msg.content
                    
                    if not self._should_process_command(command_text):
                        print(f"⏭️  Skipping duplicate/recent: {command_text}")
                        continue
                    
                    self._mark_action_processing(command_text)
                    
                    print(f"\n🚀 EXECUTING MEETING ACTION: {command_text}")
                    
                    try:
                        # Execute through agent graph
                        command_state = {"messages": [command_msg]}
                        tool_calls_found = []
                        
                        for step in agent_execution_graph.stream(command_state, {"recursion_limit": 10}):
                            step_name = list(step.keys())[0]
                            step_state = step[step_name]
                            
                            print(f"    📍 {step_name}")
                            
                            if "messages" in step_state and step_state["messages"]:
                                last_message = step_state["messages"][-1]
                                if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                                    for tc in last_message.tool_calls:
                                        print(f"      🔧 Tool: {tc['name']}")
                                        tool_calls_found.extend(last_message.tool_calls)
                        
                        # Mark as completed
                        success = len(tool_calls_found) > 0
                        self._mark_action_completed(command_text, success, tool_calls_found)
                        
                    except Exception as e:
                        print(f"    ❌ Error executing meeting action: {e}")
                        self._mark_action_completed(command_text, False)
                
            except Exception as e:
                print(f"❌ Error in meeting transcript processing: {e}")

    def _on_transcription_received(self, text: str, segments=None):
        """Handle new transcription from WhisperLive"""
        if not text or not text.strip():
            return
        
        current_time = time.time()
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Add to rolling buffer
        self.transcript_buffer.append((text.strip(), current_time))
        
        # Show live transcription with meeting context
        print(f"🎤 [{timestamp}] MEETING: {text}")
        
        # Save to transcript file
        try:
            with open(self.transcript_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {text}\n")
        except Exception as e:
            print(f"❌ Error saving transcript: {e}")
        
        # Trigger command processing periodically
        if len(self.transcript_buffer) % 3 == 0:  # Every 3 new transcriptions
            if self.processing_thread is None or not self.processing_thread.is_alive():
                self.processing_thread = threading.Thread(
                    target=self._process_transcript_for_commands,
                    daemon=True
                )
                self.processing_thread.start()

    def _start_realtime_processing(self):
        """Start WhisperLive transcription after bot joins"""
        print("🎤 Starting real-time meeting transcription and action processing...")
        
        def transcription_worker():
            try:
                self.whisper_client = TranscriptionClient(
                    "localhost",
                    9090,
                    lang="en",
                    translate=False,
                    model="small",
                    use_vad=True,
                    no_speech_thresh=0.2,
                    transcription_callback=self._on_transcription_received
                )
                
                print("✅ Connected to WhisperLive server")
                print("🎤 Listening for meeting commands...")
                print("💡 Speak naturally - actions will be executed automatically!")
                
                # Start transcription (this blocks)
                self.whisper_client()
                
            except Exception as e:
                print(f"❌ WhisperLive error: {e}")
                self.is_running = False
        
        # Start transcription in separate thread
        transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
        transcription_thread.start()

    # =================== MAIN EXECUTION ===================
    
    def save_final_logs(self):
        """Save final action logs"""
        try:
            with open(self.actions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "meeting_url": ZOOM_MEETING_URL,
                    "start_time": datetime.now().isoformat(),
                    "total_actions": len(self.executed_actions_log),
                    "actions": self.executed_actions_log
                }, f, indent=2)
            print(f"📊 Action log saved: {self.actions_file}")
        except Exception as e:
            print(f"❌ Error saving action log: {e}")

    def get_stats(self):
        """Get current system statistics"""
        return {
            "bot_joined": self.bot_joined,
            "transcript_lines": len(self.transcript_buffer),
            "executed_actions": len(self.executed_actions),
            "processing_actions": len(self.processing_actions),
            "total_logged_actions": len(self.executed_actions_log)
        }

    def run(self):
        """Main execution - process transcripts once and exit"""
        print("🚀 Starting Single-Pass Zoom Meeting Actions System")
        print("=" * 60)
        print(f"📋 Meeting: {ZOOM_MEETING_URL}")
        print(f"📄 Transcript: {self.transcript_file}")
        print(f"📊 Actions Log: {self.actions_file}")
        print("=" * 60)
        
        # Initialize files
        with open(self.transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Zoom Meeting Transcript - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Meeting: {ZOOM_MEETING_URL}\n")
            f.write("=" * 50 + "\n\n")
        
        # Create and join Zoom meeting
        if not self.create_zoom_bot():
            print("❌ FAILED: Could not create Zoom bot")
            return self._exit_with_summary(success=False, reason="Bot creation failed")
        
        # Launch Zoom app for user
        self.launch_zoom_app()
        
        print("\n" + "=" * 60)
        print("🎯 SYSTEM STATUS:")
        print("🤖 Zoom Bot: CREATED & JOINING")
        print("⏳ Waiting for bot to join meeting...")
        print("=" * 60)
        
        # Wait for bot to join (with timeout)
        max_wait_time = 120  # 2 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                bot_data = self.get_bot_status()
                bot_state = bot_data.get('state', 'unknown') if isinstance(bot_data, dict) else bot_data
                print(f"🔄 Bot status: {bot_state}")
                
                if bot_state in ['in_meeting', 'joined_recording', 'joined']:
                    print(f"✅ Bot joined meeting! Starting transcript processing...")
                    self.bot_joined = True
                    break
                elif bot_state in ['failed', 'fatal_error']:
                    return self._exit_with_summary(success=False, reason=f"Bot failed to join: {bot_state}")
                    
                time.sleep(5)
                
            except Exception as e:
                return self._exit_with_summary(success=False, reason=f"Error monitoring bot: {e}")
        
        if not self.bot_joined:
            return self._exit_with_summary(success=False, reason="Bot failed to join meeting within timeout")
        
        # Start transcription and collect for processing period
        print("🎤 Starting transcript collection...")
        processing_duration = 60  # Collect transcripts for 1 minute
        
        try:
            success = self._collect_and_process_transcripts(processing_duration)
            return self._exit_with_summary(success=success)
        except Exception as e:
            return self._exit_with_summary(success=False, reason=f"Processing error: {e}")

    def _collect_and_process_transcripts(self, duration_seconds: int) -> bool:
        """Collect transcripts for specified duration, then process once"""
        
        def transcription_worker():
            try:
                self.whisper_client = TranscriptionClient(
                    "localhost",
                    9090,
                    lang="en",
                    translate=False,
                    model="small",
                    use_vad=True,
                    no_speech_thresh=0.2,
                    transcription_callback=self._on_transcription_received
                )
                
                print("✅ Connected to WhisperLive server")
                print(f"🎤 Collecting transcripts for {duration_seconds} seconds...")
                
                # Start transcription (this blocks)
                self.whisper_client()
                
            except Exception as e:
                print(f"❌ WhisperLive error: {e}")
                self.transcription_error = str(e)
        
        # Start transcription in separate thread
        self.transcription_error = None
        transcription_thread = threading.Thread(target=transcription_worker, daemon=True)
        transcription_thread.start()
        
        # Wait for specified duration
        time.sleep(duration_seconds)
        
        # Check for transcription errors
        if self.transcription_error:
            raise Exception(f"Transcription failed: {self.transcription_error}")
        
        # Stop transcription and process accumulated transcripts
        print(f"\n🔄 Finished collecting transcripts. Processing {len(self.transcript_buffer)} entries...")
        
        if len(self.transcript_buffer) == 0:
            print("⚠️  No transcripts collected")
            return True  # Not necessarily a failure
        
        # Process all collected transcripts
        self._process_transcript_for_commands()
        
        # Wait for any pending processing to complete
        if self.processing_thread and self.processing_thread.is_alive():
            print("⏳ Waiting for command processing to complete...")
            self.processing_thread.join(timeout=30)
        
        return True

    def _exit_with_summary(self, success: bool, reason: str = None):
        """Exit with summary and JSON output"""
        
        # Save final logs
        self.save_final_logs()
        
        # Get final stats
        stats = self.get_stats()
        
        # Create actions-only output
        actions_output = {
            "meeting_info": {
                "timestamp": datetime.now().isoformat(),
                "meeting_url": ZOOM_MEETING_URL,
                "success": success,
                "reason": reason if not success else None
            },
            "transcript_stats": {
                "lines_processed": stats["transcript_lines"],
                "actions_found": stats["executed_actions"]
            },
            "actions_executed": self.executed_actions_log
        }
        
        # Save actions output as JSON
        summary_file = f"meeting_actions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary = actions_output
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            print(f"❌ Error saving summary: {e}")
        
        # Print simple summary
        print("\n" + "=" * 60)
        if success:
            print("✅ MEETING ACTIONS COMPLETED")
            print(f"📝 Transcript Lines: {stats['transcript_lines']}")
            print(f"✅ Actions Executed: {stats['executed_actions']}")
            
            if self.executed_actions_log:
                print("\n🎯 ACTIONS PERFORMED:")
                for i, action in enumerate(self.executed_actions_log, 1):
                    print(f"  {i}. {action['command']}")
                    if action.get('tool_calls'):
                        for tc in action['tool_calls']:
                            print(f"     🔧 {tc.get('name', 'unknown')}: {tc.get('args', {})}")
            else:
                print("\n⚠️  No actions were executed")
                
        else:
            print("❌ FAILED")
            print(f"💀 Reason: {reason}")
        
        print(f"\n📄 Actions saved to: {summary_file}")
        print("=" * 60)
        
        return summary


def main():
    """Main function with environment checks"""
    
    # Set default model name if not provided
    if not os.environ.get("MODEL_NAME"):
        os.environ["MODEL_NAME"] = "llama-3.3-70b-versatile"
    
    # Check required environment variables
    required_env_vars = ["ANTHROPIC_API_KEY", "GROQ_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        print("💡 Set them with:")
        for var in missing_vars:
            print(f"   export {var}='your_value_here'")
        return
    
    print("🚀 All environment variables configured")
    print(f"🤖 Using model: {os.environ.get('MODEL_NAME')}")
    
    # Create and run the integrated system
    zoom_system = ZoomMeetingActions(
        buffer_window_seconds=30,
        cooldown_seconds=3
    )
    
    zoom_system.run()


if __name__ == "__main__":
    main() 