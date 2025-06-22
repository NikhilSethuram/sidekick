from typing import List, Dict

class MockIntentParser:
    """Parses transcript chunks into actionable intents using Claude API"""
    
    def __init__(self, api_key: str = "your-anthropic-api-key"):
        self.api_key = api_key
        # For demo purposes, we'll mock the API response
        self.mock_mode = True
        
    def parse(self, text_chunks: List[str]) -> Dict:
        """Parse transcript chunks into structured intent"""
        combined_text = " ".join(text_chunks)
        
        if self.mock_mode:
            return self._mock_parse(combined_text)
        
    def _mock_parse(self, text: str) -> Dict:
        """Mock parser for demo purposes"""
        text_lower = text.lower()
        
        if "schedule" in text_lower and "meeting" in text_lower:
            return {
                "action": "schedule_meeting",
                "entities": {
                    "person": self._extract_person(text),
                    "time": self._extract_time(text)
                },
                "confidence": 0.9,
                "ready": True,
                "description": f"Schedule meeting with {self._extract_person(text)} at {self._extract_time(text)}"
            }
        elif "add" in text_lower and "reviewer" in text_lower:
            return {
                "action": "add_reviewer", 
                "entities": {
                    "person": self._extract_person(text),
                    "repo": self._extract_repo(text)
                },
                "confidence": 0.85,
                "ready": True,
                "description": f"Add {self._extract_person(text)} as reviewer to {self._extract_repo(text)}"
            }
        elif "send" in text_lower and ("slack" in text_lower or "message" in text_lower or "channel" in text_lower):
            return {
                "action": "send_message",
                "entities": {
                    "person": self._extract_person(text),
                    "channel": self._extract_channel(text),
                    "content": "meeting notes"
                },
                "confidence": 0.8,  
                "ready": True,
                "description": f"Send message to {self._extract_person(text)} in {self._extract_channel(text)}"
            }
        elif "create" in text_lower and ("ticket" in text_lower or "task" in text_lower):
            return {
                "action": "create_task",
                "entities": {
                    "task_title": self._extract_task_title(text),
                    "assignee": self._extract_person(text)
                },
                "confidence": 0.9,
                "ready": True, 
                "description": f"Create task: {self._extract_task_title(text)}"
            }
        else:
            return {
                "action": "none",
                "entities": {},
                "confidence": 0.1,
                "ready": False,
                "description": "No clear action detected"
            }
    
    def _extract_person(self, text: str) -> str:
        """Extract person name from text (simple mock)"""
        names = ["john", "sarah", "mike", "jane", "alex"]
        for name in names:
            if name in text.lower():
                return name.title()
        return "Unknown Person"
    
    def _extract_time(self, text: str) -> str:
        """Extract time from text (simple mock)"""
        if "tuesday" in text.lower():
            return "Tuesday 2pm"
        elif "tomorrow" in text.lower():
            return "Tomorrow 10am"
        elif "2pm" in text.lower():
            return "2pm"
        return "Next available time"
    
    def _extract_repo(self, text: str) -> str:
        """Extract repository from text (simple mock)"""
        if "auth" in text.lower():
            return "company/auth-service"
        elif "main" in text.lower():
            return "company/main-repo"
        return "company/default-repo"
    
    def _extract_channel(self, text: str) -> str:
        """Extract Slack channel from text (simple mock)"""
        if "engineering" in text.lower():
            return "#engineering"
        elif "general" in text.lower():
            return "#general"
        return "#general"
    
    def _extract_task_title(self, text: str) -> str:
        """Extract task title from text (simple mock)"""
        if "login bug" in text.lower():
            return "Fix login authentication bug"
        elif "ui" in text.lower():
            return "Update UI components"
        return "General task from meeting"

class MockGitHubExecutor:
    """Handles GitHub API actions"""
    
    def __init__(self, token: str = "mock-token"):
        self.token = token
        
    def add_reviewer(self, intent: Dict) -> Dict:
        """Add reviewer to GitHub PR"""
        person = intent["entities"].get("person", "Unknown")
        repo = intent["entities"].get("repo", "unknown-repo")
        
        return {
            "status": "success",
            "action": f"Added {person} as reviewer to {repo}",
            "details": f"GitHub API call would be made to add {person}"
        }

class MockCalendarExecutor:
    """Handles Google Calendar API actions"""
    
    def __init__(self, credentials=None):
        self.credentials = credentials
        
    def schedule_meeting(self, intent: Dict) -> Dict:
        """Schedule a meeting via Google Calendar"""
        person = intent["entities"].get("person", "Unknown")
        time = intent["entities"].get("time", "TBD")
        
        return {
            "status": "success", 
            "action": f"Scheduled meeting with {person} at {time}",
            "details": f"Calendar invite would be sent to {person}"
        }

class MockSlackExecutor:
    """Handles Slack API actions"""
    
    def __init__(self, token: str = "mock-token"):
        self.token = token
        
    def send_message(self, intent: Dict) -> Dict:
        """Send message via Slack"""
        person = intent["entities"].get("person", "Unknown")
        channel = intent["entities"].get("channel", "#general")
        content = intent["entities"].get("content", "meeting notes")
        
        return {
            "status": "success",
            "action": f"Sent {content} to {person} in {channel}",
            "details": f"Slack message would be posted"
        }

class MockTaskExecutor:
    """Handles task creation (Linear, Jira, etc.)"""
    
    def __init__(self, api_key: str = "mock-key"):
        self.api_key = api_key
        
    def create_task(self, intent: Dict) -> Dict:
        """Create a task/ticket"""
        title = intent["entities"].get("task_title", "Meeting Task")
        assignee = intent["entities"].get("assignee", "Unassigned")
        
        return {
            "status": "success",
            "action": f"Created task: {title}",
            "details": f"Task assigned to {assignee}"
        } 