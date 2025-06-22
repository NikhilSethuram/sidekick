import streamlit as st
import json
import time
import os
import re
from datetime import datetime
import sys
sys.path.append('/Users/yashgupta/Desktop/Programming/calhacks2025')
from agents.workers.github.tools import add_reviewer_to_pr, create_github_issue
from agents.workers.outlook_calendar.tools import schedule_meeting, send_email

# --- Tool Mapping ---
TOOL_MAP = {
    "add_reviewer_to_pr": add_reviewer_to_pr,
    "schedule_meeting": schedule_meeting,
    "create_github_issue": create_github_issue,
    "send_email": send_email
}

# --- Human-like Interface Functions ---
def get_action_avatar(tool_name):
    """Get appropriate avatar for each action type."""
    avatars = {
        "add_reviewer_to_pr": "👨‍💻",
        "create_github_issue": "👨‍💻", 
        "schedule_meeting": "📅",
        "send_email": "✉️"
    }
    return avatars.get(tool_name, "🤖")

def get_action_avatar_and_type(tool_name):
    """Get avatar and type based on tool name"""
    if tool_name in ['add_reviewer_to_pr', 'create_github_issue']:
        return "👨‍💻", "GitHub", "github-avatar"
    elif tool_name in ['schedule_meeting', 'send_email']:
        return "📅", "Outlook", "calendar-avatar"
    else:
        return "🔧", "Tool", "github-avatar"

def get_human_description(task):
    """Format task description in a more human way"""
    tool_name = task.get('tool_name', '')
    args = task.get('arguments', {})
    
    if tool_name == 'add_reviewer_to_pr':
        reviewer = args.get('reviewer_username', args.get('reviewer', 'someone'))
        pr_name = args.get('pr_name', 'a PR')
        return f"I'd like to add <strong>{reviewer}</strong> as a reviewer on the <strong>{pr_name}</strong> pull request"
        
    elif tool_name == 'create_github_issue':
        title = args.get('title', 'New Issue')
        assignee = args.get('assignee')
        desc = f"I want to create a new GitHub issue: <strong>\"{title}\"</strong>"
        if assignee:
            desc += f" and assign it to <strong>{assignee}</strong>"
        return desc
        
    elif tool_name == 'schedule_meeting':
        subject = args.get('subject', 'Meeting')
        attendees = args.get('attendees', [])
        start_time = args.get('start_time', '')
        duration = args.get('duration_minutes', 60)
        desc = f"I'd like to schedule <strong>\"{subject}\"</strong>"
        if attendees:
            desc += f" with {', '.join(attendees)}"
        if start_time:
            desc += f" starting {start_time}"
        if duration:
            desc += f" ({duration} minutes)"
        return desc
        
    elif tool_name == 'send_email':
        recipients = args.get('recipients', [])
        subject = args.get('subject', 'Email')
        desc = f"I'd like to send an email about <strong>\"{subject}\"</strong>"
        if recipients:
            desc += f" to {', '.join(recipients)}"
        return desc
        
    else:
        return f"Execute {tool_name} with the provided parameters"

def get_impact_description(task):
    """Get impact explanation for the task"""
    tool_name = task.get('tool_name', '')
    
    if tool_name == 'add_reviewer_to_pr':
        return "💡 This will notify the reviewer and add them to the PR review process"
    elif tool_name == 'create_github_issue':
        return "💡 This will create a new issue that the team can track and work on"
    elif tool_name == 'schedule_meeting':
        return "💡 This will send calendar invites to all attendees"
    elif tool_name == 'send_email':
        return "💡 This will send an email to the specified recipients"
    else:
        return "💡 This action will be executed immediately"

def display_conversation_style_action(task, index):
    """Display action in a conversation/chat style."""
    avatar = get_action_avatar(task.get("name"))
    human_desc = get_human_description(task)
    impact_desc = get_impact_description(task)
    command = task.get("command", "Unknown command")
    created_at = task.get("created_at", "")
    
    # Create a chat-like message bubble
    with st.container():
        col1, col2 = st.columns([1, 10])
        
        with col1:
            st.markdown(f"<div style='font-size: 2em; text-align: center;'>{avatar}</div>", unsafe_allow_html=True)
        
        with col2:
            # Assistant message bubble
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 20px 20px 20px 5px;
                margin: 10px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ">
                <div style="font-size: 0.9em; opacity: 0.8; margin-bottom: 8px;">
                    🎤 From your meeting: "<em>{command}</em>"
                </div>
                <div style="font-size: 1.1em; line-height: 1.4;">
                    {human_desc}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Impact preview
            with st.expander("🔍 What will this do?", expanded=False):
                st.markdown("**Here's what will happen:**")
                st.markdown(impact_desc)
                
                # Technical details (much less prominent)
                with st.expander("⚙️ Technical details (for debugging)", expanded=False):
                    st.code(json.dumps(task.get("args", {}), indent=2), language="json")
    
    return col2  # Return column for placing buttons

def display_human_response_buttons(task, col):
    """Display human-like response buttons."""
    task_id = task.get("id")
    tool_name = task.get("name")
    
    # Check service readiness
    env_status = check_environment()
    service_ready = True
    warning_msg = ""
    
    if tool_name == "add_reviewer_to_pr" and not env_status["github_ready"]:
        service_ready = False
        warning_msg = "GitHub not configured"
    elif tool_name == "schedule_meeting" and not env_status["outlook_ready"]:
        service_ready = False  
        warning_msg = "Outlook not configured"
    
    with col:
        if not service_ready:
            st.warning(f"⚠️ {warning_msg} - Please check your settings")
        
        # Human-like response options
        st.markdown("**How should I respond?**")
        
        col_yes, col_no, col_maybe = st.columns([2, 2, 1])
        
        with col_yes:
            if st.button(
                "✅ **Yes, do it!**", 
                key=f"approve_{task_id}", 
                disabled=not service_ready,
                help="I approve this action - go ahead and execute it",
                type="primary"
            ):
                st.session_state.task_states[task_id] = "approved"
                st.rerun()
        
        with col_no:
            if st.button(
                "❌ **No, skip this**", 
                key=f"reject_{task_id}",
                help="I don't want this action to be executed"
            ):
                st.session_state.task_states[task_id] = "rejected"
                task["status"] = "rejected"
                task["result"] = "Declined by user"
                st.rerun()
        
        with col_maybe:
            if st.button("🤔", key=f"info_{task_id}", help="Tell me more about this"):
                st.info(f"""
                **More details about this action:**
                
                • **Action type:** {tool_name.replace('_', ' ').title()}
                • **Triggered by:** "{task.get('command', 'Unknown')}"
                • **Proposed at:** {task.get('created_at', 'Unknown time')[:19]}
                
                This action is waiting for your approval. It won't execute until you click "Yes, do it!"
                """)

# --- Error Analysis Functions ---
def analyze_error(tool_name, error_message, args):
    """Analyze errors and provide categorization and suggestions."""
    error_info = {
        "category": "unknown",
        "severity": "error",
        "icon": "❌",
        "suggestion": "Please check the error details and try again.",
        "actionable": False
    }
    
    error_lower = error_message.lower()
    
    # GitHub-specific errors
    if tool_name == "add_reviewer_to_pr":
        if "review cannot be requested from pull request author" in error_lower:
            error_info.update({
                "category": "Can't review own PR",
                "severity": "warning",
                "icon": "⚠️",
                "suggestion": f"Oops! {args.get('reviewer', 'This person')} created this PR, so they can't review their own work. Let's try adding someone else instead.",
                "actionable": True,
                "fix_action": "Choose different reviewer"
            })
        elif "not found" in error_lower and "pr" in error_lower:
            error_info.update({
                "category": "PR not found",
                "severity": "error",
                "icon": "🔍",
                "suggestion": f"I couldn't find a PR matching '{args.get('pr_name', 'that name')}'. Maybe it was already merged, closed, or the name is slightly different?",
                "actionable": True,
                "fix_action": "Check PR name"
            })
        elif "token" in error_lower or "authentication" in error_lower:
            error_info.update({
                "category": "GitHub login issue",
                "severity": "critical",
                "icon": "🔐",
                "suggestion": "I can't access GitHub right now. Your access token might be missing or expired.",
                "actionable": True,
                "fix_action": "Fix GitHub access"
            })
    
    # Outlook-specific errors  
    elif tool_name == "schedule_meeting":
        if "time" in error_lower and ("invalid" in error_lower or "format" in error_lower):
            error_info.update({
                "category": "Time format issue",
                "severity": "warning",
                "icon": "⏰",
                "suggestion": f"I'm having trouble understanding the time '{args.get('start_time', 'unknown')}'. Could you try a format like 'in 2 hours' or '2024-01-15T10:00:00'?",
                "actionable": True,
                "fix_action": "Fix time format"
            })
    
    return error_info

def display_human_error_card(task, error_info):
    """Display error in a human, conversational way."""
    with st.container():
        col1, col2 = st.columns([1, 10])
        
        with col1:
            st.markdown(f"<div style='font-size: 2em; text-align: center;'>😅</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
                color: white;
                padding: 20px;
                border-radius: 20px 20px 20px 5px;
                margin: 10px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            ">
                <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 8px;">
                    {error_info['icon']} Oops! {error_info['category']}
                </div>
                <div style="font-size: 1em; line-height: 1.4; opacity: 0.95;">
                    {error_info['suggestion']}
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- Helper Functions ---
def load_tasks(filepath="output.json"):
    """Loads tasks from the JSON file."""
    try:
        with open(filepath, 'r') as f:
            tasks = json.load(f)
            # Ensure tasks is a list
            if not isinstance(tasks, list):
                return []
            return tasks
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_tasks(tasks, filepath="output.json"):
    """Saves tasks back to the JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(tasks, f, indent=2)
    except IOError as e:
        st.error(f"Error saving tasks: {e}")

def check_environment():
    """Check if required environment variables are set."""
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPOSITORY") 
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    return {
        "github_ready": bool(github_token and github_repo),
        "outlook_ready": True,  # Assume outlook is configured
        "anthropic_ready": bool(anthropic_key),
        "github_token": github_token,
        "github_repo": github_repo
    }

def execute_tool(task):
    """Execute the tool for a given task"""
    try:
        tool_name = task.get('tool_name', '')
        args = task.get('arguments', {})
        
        if tool_name == 'add_reviewer_to_pr':
            result = add_reviewer_to_pr(
                pr_name=args.get('pr_name', args.get('pr_title', 'PR')),
                reviewer=args.get('reviewer_username', args.get('reviewer'))
            )
            return True, f"Successfully added reviewer: {result}"
            
        elif tool_name == 'create_github_issue':
            result = create_github_issue(
                title=args.get('title'),
                body=args.get('body', ''),
                assignee=args.get('assignee')
            )
            return True, f"Successfully created GitHub issue: {result}"
            
        elif tool_name == 'schedule_meeting':
            result = schedule_meeting(
                subject=args.get('subject'),
                start_time=args.get('start_time'),
                end_time=args.get('end_time'),
                attendees=args.get('attendees', []),
                body=args.get('body', '')
            )
            return True, f"Successfully scheduled meeting: {args.get('subject')}"
            
        elif tool_name == 'send_email':
            result = send_email(
                recipients=args.get('recipients', []),
                subject=args.get('subject', 'Email'),
                body=args.get('body', '')
            )
            return True, f"Successfully sent email: {args.get('subject')}"
            
        else:
            return False, f"Unknown tool: {tool_name}"
            
    except Exception as e:
        error_msg = str(e)
        
        # Provide human-friendly error explanations
        if "Review cannot be requested from pull request author" in error_msg:
            return False, "Can't add the PR author as a reviewer (they're already the author!)"
        elif "Not Found" in error_msg:
            return False, "Couldn't find the repository or PR. Please check if it exists."
        elif "Validation Failed" in error_msg:
            return False, "Invalid request - please check the details and try again."
        elif "rate limit" in error_msg.lower():
            return False, "API rate limit exceeded. Please try again in a few minutes."
        else:
            return False, f"Something went wrong: {error_msg}"

# --- Streamlit App ---
st.set_page_config(
    page_title="Sidekick - Your Meeting Assistant", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main > div {
        padding-top: 2rem;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    .main-subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 1.1rem;
        font-weight: 400;
    }
    
    .action-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
    }
    
    .action-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .action-avatar {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        margin-right: 1rem;
        font-weight: 600;
    }
    
    .github-avatar {
        background: linear-gradient(135deg, #24292e, #586069);
        color: white;
    }
    
    .calendar-avatar {
        background: linear-gradient(135deg, #4285f4, #34a853);
        color: white;
    }
    
    .jira-avatar {
        background: linear-gradient(135deg, #0052cc, #2684ff);
        color: white;
    }
    
    .action-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
    }
    
    .action-type {
        font-size: 0.85rem;
        color: #6b7280;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .action-description {
        color: #374151;
        font-size: 1rem;
        line-height: 1.6;
        margin: 1rem 0;
    }
    
    .action-impact {
        background: #f0f9ff;
        border: 1px solid #e0f2fe;
        border-radius: 8px;
        padding: 0.75rem;
        margin: 1rem 0;
        font-size: 0.9rem;
        color: #0369a1;
    }
    
    .button-container {
        display: flex;
        gap: 0.75rem;
        margin-top: 1.5rem;
    }
    
    .approve-btn {
        background: linear-gradient(135deg, #10b981, #059669) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3) !important;
    }
    
    .approve-btn:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4) !important;
    }
    
    .reject-btn {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3) !important;
    }
    
    .reject-btn:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4) !important;
    }
    
    .success-alert {
        background: linear-gradient(135deg, #d1fae5, #a7f3d0);
        border: 1px solid #10b981;
        color: #065f46;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .error-alert {
        background: linear-gradient(135deg, #fee2e2, #fecaca);
        border: 1px solid #ef4444;
        color: #991b1b;
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .status-pending {
        background: #fef3c7;
        color: #92400e;
    }
    
    .status-success {
        background: #d1fae5;
        color: #065f46;
    }
    
    .status-error {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .status-rejected {
        background: #f3f4f6;
        color: #374151;
    }
    
    .no-actions {
        text-align: center;
        padding: 3rem;
        color: #6b7280;
    }
    
    .no-actions-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        opacity: 0.5;
    }
    
    .stats-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .stat-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    
    .stat-label {
        color: #6b7280;
        font-size: 0.9rem;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1 class="main-title">🤖 Sidekick</h1>
    <p class="main-subtitle">Your AI meeting companion is ready to help</p>
</div>
""", unsafe_allow_html=True)

# Check environment
env_status = check_environment()

# Initialize session state
if 'task_states' not in st.session_state:
    st.session_state.task_states = {}

# Load tasks
tasks = load_tasks()

# Separate tasks by status
pending_tasks = [task for task in tasks if task.get("status") == "pending_approval"]
error_tasks = [task for task in tasks if task.get("status") == "error"]
success_tasks = [task for task in tasks if task.get("status") == "success"]
rejected_tasks = [task for task in tasks if task.get("status") == "rejected"]

# Show status in a friendly way
if not tasks:
    st.markdown("""
    <div class="action-card">
        <div class="no-actions">
            <div class="no-actions-icon">💭</div>
            <h3>No actions detected yet</h3>
            <p>Join a meeting and I'll listen for actionable requests!</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Stats
    pending_count = len([t for t in tasks if t.get('status') == 'pending_approval'])
    completed_count = len([t for t in tasks if t.get('status') == 'success'])
    
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-card">
            <div class="stat-number">{pending_count}</div>
            <div class="stat-label">Pending Actions</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{completed_count}</div>
            <div class="stat-label">Completed Today</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(tasks)}</div>
            <div class="stat-label">Total Actions</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display tasks
    for i, task in enumerate(tasks):
        status = task.get('status', 'pending_approval')
        
        # Skip if already processed
        if status in ['success', 'error', 'rejected']:
            continue
            
        avatar, action_type, avatar_class = get_action_avatar_and_type(task.get('tool_name', ''))
        description = get_human_description(task)
        impact = get_impact_description(task)
        
        # Create a clean card using Streamlit components
        with st.container():
            # Main card with better styling
            st.markdown(f"""
            <div class="action-card">
                <div class="action-header">
                    <div class="action-avatar {avatar_class}">
                        {avatar}
                    </div>
                    <div>
                        <div class="action-type">{action_type} Action</div>
                        <div class="action-title">Ready to execute</div>
                    </div>
                </div>
                <div class="action-description">
                    {description}
                </div>
                <div class="action-impact">
                    {impact}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons - clean and compact
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            
            # Simple two-column layout for buttons
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2, 1, 1, 2])
            
            with btn_col2:
                if st.button("✅ Approve", key=f"approve_{i}", help="Execute this action", type="primary"):
                    with st.spinner("Executing..."):
                        success, message = execute_tool(task)
                        
                        if success:
                            task['status'] = 'success'
                            task['result'] = message
                            task['executed_at'] = datetime.now().isoformat()
                            st.success(f"✅ {message}")
                        else:
                            task['status'] = 'error'
                            task['error'] = message
                            task['executed_at'] = datetime.now().isoformat()
                            st.error(f"❌ {message}")
                        
                        save_tasks(tasks)
                        st.rerun()
            
            with btn_col3:
                if st.button("❌ Skip", key=f"reject_{i}", help="Skip this action"):
                    task['status'] = 'rejected'
                    task['rejected_at'] = datetime.now().isoformat()
                    save_tasks(tasks)
                    st.rerun()
            
            st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

# Auto-refresh
if st.button("🔄 Refresh", help="Check for new actions"):
    st.rerun()

# --- Recent Activity (Sidebar) ---
with st.sidebar:
    st.title("📊 Recent Activity")
    
    if success_tasks:
        st.subheader("✅ Recently completed")
        for task in success_tasks[-3:]:
            st.success(f"**{task.get('name', 'Action').replace('_', ' ').title()}**\n{task.get('result', '')[:100]}...")
    
    if error_tasks:
        st.subheader("❌ Recent issues")
        for task in error_tasks[-2:]:
            st.error(f"**{task.get('name', 'Action').replace('_', ' ').title()}**\nNeed to check this one")
    
    st.divider()
    
    if st.button("🔄 Check for new actions"):
        st.rerun()
    
    if st.button("🧹 Clear completed"):
        remaining_tasks = [task for task in tasks if task.get("status") not in ["success", "rejected"]]
        save_tasks(remaining_tasks)
        st.rerun() 