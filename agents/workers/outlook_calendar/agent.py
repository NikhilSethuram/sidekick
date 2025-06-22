from langchain.agents import create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Import the tools from your tools.py file
from .tools import send_email, schedule_meeting

def create_outlook_calendar_agent(llm: ChatAnthropic):
    """Creates the agent that can use the Outlook calendar tools."""
    
    # 1. Define the tools this agent has access to
    tools = [send_email, schedule_meeting]
    
    # 2. Create the prompt
    # The prompt tells the agent its purpose and how to behave.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are a helpful assistant that is an expert at using Microsoft Outlook tools for email and calendar management.

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

When sending emails:
- Ensure all email addresses are valid format
- Provide clear, professional subject lines
- Write appropriate email content

Be helpful, professional, and efficient in your responses."""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 3. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return agent, tools
