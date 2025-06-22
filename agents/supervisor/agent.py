import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic  
from langchain_core.messages import HumanMessage
from langgraph_supervisor import create_supervisor
from agents.workers.outlook_calendar.agent import outlook_agent, outlook_tools

load_dotenv()
model = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

supervisor_graph = create_supervisor(
    [outlook_agent],
    model=model,
    prompt="""You are a supervisor agent responsible for managing a team of specialized worker agents.

Your primary role is to understand the user's request, break it down into actionable steps, and delegate each step to the most appropriate worker agent.

You have access to the following worker agents:
{members}

Each worker agent has a specific set of tools and capabilities. Your job is to determine which worker is best suited to handle the current task based on the user's input.

Here is your workflow:
1.  **Analyze the request:** Carefully read the latest user request to understand their goal.
2.  **Select the best agent:** Based on the request, choose the most appropriate worker agent from the available list to address the user's request. You are provided with a list of agents and their descriptions.
3.  **Specify the next agent:** Your response must be only the name of the selected agent. For example, if the user wants to schedule a meeting, and you have an 'outlook_agent' available, you should respond with "outlook_agent". Do not add any other text to your response.

You must route the tasks to the agents. You should not try to answer the user's request directly.
"""
)

workflow = supervisor_graph.compile()


