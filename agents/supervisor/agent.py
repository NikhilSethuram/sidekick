import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic  
from langchain_core.messages import HumanMessage
from langgraph_supervisor import create_supervisor
from agents.workers.outlook_calendar.agent import outlook_agent, outlook_tools
from agents.workers.github.agent import github_agent, github_tools

load_dotenv()
model = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

supervisor_graph = create_supervisor(
    [outlook_agent, github_agent],
    model=model,
    prompt="""You are a supervisor agent responsible for managing a team of specialized worker agents. Your primary role is to analyze incoming user requests and route them to the most appropriate agent based on their specific capabilities and tools.

**Instructions:**
1.  Thoroughly analyze the user's request to understand the core task.
2.  Review the list of available agents and their documented tools.
3.  Choose the single agent that is best equipped to handle the request. The agent's tools MUST be suitable for the task.
4.  Respond ONLY with the name of the selected agent (e.g., `github_agent`). Do not add any other text.

**Available Agents and Tools:**
{members}

**Example:**
User Request: "Can you add a reviewer to my pull request?"
Your Response:
github_agent
"""
)

workflow = supervisor_graph.compile()


