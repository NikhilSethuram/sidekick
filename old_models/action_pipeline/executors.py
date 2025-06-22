from typing import Dict

class GitHubExecutor:
    """Handles GitHub API actions"""
    
    def __init__(self, token: str = "your-github-token"):
        self.token = token
        
    def add_reviewer(self, intent: Dict) -> Dict:
        """Add reviewer to GitHub PR - STUB"""
        person = intent["entities"].get("person", "Unknown")
        repo = intent["entities"].get("repo", "unknown-repo")
        print(f"--- FAKE GITHUB ACTION ---")
        print(f"Would add {person} as a reviewer to {repo}")
        print(f"--------------------------")
        return {
            "status": "success",
            "action": f"Added {person} as reviewer to {repo}",
            "details": f"This is a stub. No real API call was made."
        }

class CalendarExecutor:
    """Handles Google Calendar API actions"""
    
    def __init__(self, credentials=None):
        self.credentials = credentials
        
    def schedule_meeting(self, intent: Dict) -> Dict:
        """Schedule a meeting via Google Calendar - STUB"""
        person = intent["entities"].get("person", "Unknown")
        time = intent["entities"].get("time", "TBD")
        print(f"--- FAKE CALENDAR ACTION ---")
        print(f"Would schedule meeting with {person} at {time}")
        print(f"----------------------------")
        return {
            "status": "success", 
            "action": f"Scheduled meeting with {person} at {time}",
            "details": f"This is a stub. No real API call was made."
        }

class SlackExecutor:
    """Handles Slack API actions"""
    
    def __init__(self, token: str = "your-slack-token"):
        self.token = token
        
    def send_message(self, intent: Dict) -> Dict:
        """Send message via Slack - STUB"""
        person = intent["entities"].get("person", "Unknown")
        channel = intent["entities"].get("channel", "#general")
        content = intent["entities"].get("content", "meeting notes")
        print(f"--- FAKE SLACK ACTION ---")
        print(f"Would send '{content}' to {person} in {channel}")
        print(f"-------------------------")
        return {
            "status": "success",
            "action": f"Sent {content} to {person} in {channel}",
            "details": f"This is a stub. No real API call was made."
        }

class TaskExecutor:
    """Handles task creation (Linear, Jira, etc.) - STUB"""
    
    def __init__(self, api_key: str = "your-task-manager-api-key"):
        self.api_key = api_key
        
    def create_task(self, intent: Dict) -> Dict:
        """Create a task/ticket"""
        title = intent["entities"].get("task_title", "Meeting Task")
        assignee = intent["entities"].get("assignee", "Unassigned")
        print(f"--- FAKE TASK ACTION ---")
        print(f"Would create task '{title}' assigned to {assignee}")
        print(f"------------------------")
        return {
            "status": "success",
            "action": f"Created task: {title}",
            "details": f"Task assigned to {assignee}. This is a stub."
        }

class ActionExecutors:
    """A manager for all the different action executors."""

    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.github = GitHubExecutor(token=self.config.get('github_token'))
        self.calendar = CalendarExecutor(credentials=self.config.get('google_credentials'))
        self.slack = SlackExecutor(token=self.config.get('slack_token'))
        self.task = TaskExecutor(api_key=self.config.get('task_manager_api_key'))

        self.executor_map = {
            "add_reviewer": self.github.add_reviewer,
            "schedule_meeting": self.calendar.schedule_meeting,
            "send_message": self.slack.send_message,
            "create_task": self.task.create_task,
        }

    def execute_action(self, intent: Dict) -> Dict:
        """Execute an action based on the intent."""
        action = intent.get("action")
        if action in self.executor_map:
            return self.executor_map[action](intent)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
