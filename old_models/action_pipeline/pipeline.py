# action_pipeline/pipeline.py
"""
Main action processing pipeline that integrates with audio transcription
"""

import json
import time
from typing import List, Dict, Optional, Callable
from .intent_parser import IntentParser
from .executors import ActionExecutors
from .approval_ui import ApprovalInterface

class ActionPipeline:
    """
    Main pipeline that processes transcript chunks and executes actions
    This is the interface your partner's audio code will call
    """
    
    def __init__(self, config: Dict = None):
        """Initialize the action pipeline"""
        self.config = config or {}
        
        # Core components
        self.parser = IntentParser(
            api_key=self.config.get('anthropic_api_key')
        )
        self.executors = ActionExecutors(self.config)
        self.approval_interface = ApprovalInterface()
        
        # Transcript buffering
        self.transcript_buffer = []
        self.buffer_max_age = 30  # seconds
        self.last_action_time = 0
        self.min_action_interval = 5  # minimum seconds between actions
        
        # Statistics
        self.stats = {
            'chunks_processed': 0,
            'actions_detected': 0,
            'actions_executed': 0,
            'actions_denied': 0
        }
    
    def process_transcript_chunk(self, text: str, timestamp: float = None) -> Optional[Dict]:
        """
        Main method called by audio pipeline for each transcript chunk
        
        Args:
            text: Transcript text chunk from Whisper
            timestamp: Optional timestamp of when this was spoken
            
        Returns:
            Dict with action result if action was taken, None otherwise
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Add to buffer
        self.transcript_buffer.append({
            'text': text,
            'timestamp': timestamp
        })
        
        # Clean old chunks
        self._clean_buffer(timestamp)
        
        # Update stats
        self.stats['chunks_processed'] += 1
        
        # Check if we should process for actions
        if self._should_process_actions(timestamp):
            return self._process_for_actions()
        
        return None
    
    def _clean_buffer(self, current_time: float):
        """Remove chunks older than buffer_max_age"""
        cutoff_time = current_time - self.buffer_max_age
        self.transcript_buffer = [
            chunk for chunk in self.transcript_buffer 
            if chunk['timestamp'] > cutoff_time
        ]
    
    def _should_process_actions(self, current_time: float) -> bool:
        """Determine if we should look for actions now"""
        # Don't process too frequently
        if current_time - self.last_action_time < self.min_action_interval:
            return False
        
        # Need at least some text to work with
        if len(self.transcript_buffer) < 2:
            return False
        
        # Check if recent chunks suggest a complete thought
        recent_text = ' '.join([
            chunk['text'] for chunk in self.transcript_buffer[-3:]
        ])
        
        # Simple heuristic: look for action keywords
        action_keywords = ['schedule', 'add', 'send', 'create', 'assign', 'invite']
        return any(keyword in recent_text.lower() for keyword in action_keywords)
    
    def _process_for_actions(self) -> Optional[Dict]:
        """Process current buffer for actionable intents"""
        # Get recent transcript text
        recent_chunks = self.transcript_buffer[-5:]  # Last 5 chunks
        text_chunks = [chunk['text'] for chunk in recent_chunks]
        
        # Parse for intent
        intent = self.parser.parse(text_chunks)
        
        if not intent.get('ready') or intent.get('confidence', 0) < 0.7:
            return None
        
        self.stats['actions_detected'] += 1
        self.last_action_time = time.time()
        
        # Get user approval (this could be async in real implementation)
        approval = self.approval_interface.show_approval_popup(
            intent['description'], intent
        )
        
        if approval == 'approved':
            # Execute the action
            result = self.executors.execute_action(intent)
            if result.get('status') == 'success':
                self.stats['actions_executed'] += 1
            return result
        elif approval == 'denied':
            self.stats['actions_denied'] += 1
            return {'status': 'denied', 'action': intent['description']}
        
        return None
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'chunks_processed': 0,
            'actions_detected': 0, 
            'actions_executed': 0,
            'actions_denied': 0
        }

# Integration example for your partner's code
class TranscriptProcessor:
    """
    Example of how your partner would integrate this
    This would go in their main.py or audio processing file
    """
    
    def __init__(self):
        # Initialize action pipeline
        config = {
            'anthropic_api_key': 'your-key-here',
            'github_token': 'your-github-token',
            'google_credentials': 'path-to-creds.json',
            'slack_token': 'your-slack-token'
        }
        
        self.action_pipeline = ActionPipeline(config)
    
    def on_transcript_chunk(self, text: str, timestamp: float):
        """
        Called by Whisper/audio processing when new transcript arrives
        Your partner would call this method
        """
        print(f"[TRANSCRIPT] {text}")
        
        # Process through action pipeline
        result = self.action_pipeline.process_transcript_chunk(text, timestamp)
        
        if result:
            print(f"[ACTION] {result}")
    
    def simulate_whisper_integration(self):
        """
        Simulate how this would work with real Whisper output
        Your partner's code would replace this with real WebSocket handling
        """
        # This simulates real-time transcript chunks from Whisper
        mock_transcript_stream = [
            ("Let's schedule a meeting", 1.0),
            ("with John from engineering", 3.5),
            ("for next Tuesday at 2pm", 6.0),
            ("Can we also add Sarah", 10.0),
            ("as a reviewer on the auth PR", 12.5),
            ("Send the meeting notes", 18.0),
            ("to the engineering channel", 20.0)
        ]
        
        start_time = time.time()
        
        for text, delay in mock_transcript_stream:
            current_time = start_time + delay
            
            # Simulate real-time arrival
            time.sleep(0.5)  # Brief pause between chunks
            
            # Process transcript chunk
            self.on_transcript_chunk(text, current_time)

# Example usage that your partner would implement
def main():
    """
    This is what your partner's main.py would look like
    """
    processor = TranscriptProcessor()
    
    print("🎤 Starting meeting transcription with action detection...")
    print("=" * 60)
    
    # In real implementation, this would be:
    # - WebSocket connection to Whisper API
    # - Real-time audio processing
    # - Actual transcript chunks
    
    processor.simulate_whisper_integration()
    
    # Show final stats
    stats = processor.action_pipeline.get_stats()
    print(f"\n📊 Final Statistics:")
    print(f"Chunks processed: {stats['chunks_processed']}")
    print(f"Actions detected: {stats['actions_detected']}")
    print(f"Actions executed: {stats['actions_executed']}")

if __name__ == "__main__":
    main()