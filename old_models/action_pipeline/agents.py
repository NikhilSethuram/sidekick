from mcp_agent.core.fastagent import FastAgent
from typing import Dict

# Create the application
fast = FastAgent("ZoomMateAgent")

@fast.agent(
  name="add_reviewer",
  instruction="Add a reviewer to a GitHub pull request."
)
async def add_reviewer(intent: Dict) -> Dict:
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

@fast.agent(
  name="schedule_meeting",
  instruction="Schedule a meeting with someone."
)
async def schedule_meeting(intent: Dict) -> Dict:
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

@fast.agent(
  name="send_message",
  instruction="Send a message to a person or channel in Slack."
)
async def send_message(intent: Dict) -> Dict:
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

@fast.agent(
  name="create_task",
  instruction="Create a new task in a task management system."
)
async def create_task(intent: Dict) -> Dict:
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