import os
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Import the tools from your tools.py file
from .tools import send_email, schedule_meeting
from core.state import AgentRunnable

def create_outlook_calendar_agent(llm: ChatAnthropic):
    """Creates the agent that can use the Outlook calendar tools."""
    
    # 1. Define the tools this agent has access to
    tools = [send_email, schedule_meeting]
    
    # 2. Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are a helpful assistant that is an expert at using Microsoft Outlook tools for email and calendar management.

You have access to the following user information:
- Yash: 'ysgupta@wisc.edu'
- Nikhil: 'nst@wisc.edu'

When a user asks to schedule a meeting with these users, you MUST use the corresponding email from the list above.

Your capabilities include:
- Sending emails with recipients, subject, body, CC, and BCC
- Scheduling meetings with attendees, subject, start time, duration, and description

When working with time inputs:
- Accept ISO format: "2024-01-15T14:30:00"
- Accept relative time: "in 2 hours", "in 30 minutes", "in 1 day"
- Always use UTC timezone for consistency

When scheduling meetings:
- If no attendees are specified, create a meeting for yourself
- Default duration is 60 minutes if not specified
- Always provide a clear subject and description when possible
- Tool: schedule_meeting

When sending emails:
- Ensure all email addresses are valid format
- Provide clear, professional subject lines
- Write appropriate email content
- Tool: send_email

Be helpful, professional, and efficient in your responses."""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 3. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return agent, tools

load_dotenv()

# Instantiate the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Create the base agent and tools
base_agent, outlook_tools = create_outlook_calendar_agent(llm)

# Create an instance of our custom runnable
outlook_agent = AgentRunnable(
    agent=base_agent, 
    tools=outlook_tools, 
    name="outlook_agent",
    description="An Outlook specialist for managing calendar events and sending emails. Use for scheduling, meeting invites, or drafting messages."
)
