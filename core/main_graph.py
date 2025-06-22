import os
import json
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

# The supervisor has been repurposed to be a command extractor.
from agents.supervisor.agent import workflow as command_extractor_workflow
from agents.workers.outlook_calendar.agent import outlook_agent, outlook_tools
from core.state import AgentState
from agents.workers.github.agent import github_agent, github_tools

# Initialize the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME"))


# --- Routing Supervisor Logic ---
# This supervisor is for routing a single command to the correct worker agent.
available_agents_descriptions = """
- outlook_agent: An agent that can manage your Outlook calendar. Use it to schedule meetings, find free time, and send invites.
- github_agent: An agent that can interact with GitHub. Use it to manage pull requests, assign reviewers, and create issues.
- slack_agent: An agent that can send messages to Slack channels.
- jira_agent: An agent for managing Jira tickets. Use it to create tickets.
- notion_agent: An agent for interacting with Notion.
"""

routing_supervisor_prompt_template = f"""
You are a supervisor agent responsible for managing a team of specialized worker agents.
Your primary role is to analyze an incoming user request and route it to the most appropriate agent.
Respond ONLY with the name of the selected agent (e.g., `github_agent`) or 'FINISH' if the task is complete or no agent is suitable.

Available Agents:
{available_agents_descriptions}

Conversation History:
{{chat_history}}

User Request:
{{input}}

Your Response:
"""

def command_extractor_node(state: AgentState):
    """Invokes the command extractor to find tasks in the transcript."""
    print("---COMMAND EXTRACTOR---")
    # This workflow now lives in agents/supervisor/agent.py
    result = command_extractor_workflow(state)
    return {"messages": result["messages"]}

def supervisor_node(state: AgentState):
    """Invokes the supervisor to decide the next step for a single command."""
    print("---SUPERVISOR (ROUTING)---")
    
    chat_history_str = "\n".join([f"  - {msg.type}: {msg.content}" for msg in state["messages"]])
    
    last_human_message = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break

    prompt = routing_supervisor_prompt_template.format(chat_history=chat_history_str, input=last_human_message)
    
    response = llm.invoke(prompt)
    agent_name = response.content.strip()

    return {"messages": [AIMessage(content=agent_name, name="supervisor")]}


def outlook_agent_node(state: AgentState):
    """Invokes the outlook agent and returns its result."""
    print("---OUTLOOK AGENT---")
    result = outlook_agent.invoke(state)
    return result

def github_agent_node(state: AgentState):
    """Invokes the GitHub agent and returns its result."""
    print("---GITHUB AGENT---")
    result = github_agent.invoke(state)
    return result

# --- Agent Execution Graph Definition ---
graph_builder = StateGraph(AgentState)

graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("outlook_agent", outlook_agent_node)
graph_builder.add_node("github_agent", github_agent_node)
# Placeholder nodes for other agents. They need to be implemented.
# graph_builder.add_node("jira_agent", jira_agent_node)
# graph_builder.add_node("slack_agent", slack_agent_node)
# graph_builder.add_node("notion_agent", notion_agent_node)


tool_node = ToolNode(outlook_tools + github_tools) # Add other tools here
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "supervisor")

def supervisor_router(state: AgentState):
    """Routes from the supervisor to the correct agent or ends."""
    print(f"---ROUTING---")
    last_message = state["messages"][-1]
    next_agent = last_message.content
    print(f"Next step is: {next_agent}")
    if next_agent == "FINISH" or next_agent not in ["outlook_agent", "github_agent"]: # Add other agents here
        return END
    return next_agent

graph_builder.add_conditional_edges("supervisor", supervisor_router)

def after_agent_router(state: AgentState):
    """Checks for tool calls and routes to tools or back to supervisor."""
    print("---AGENT ROUTER---")
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        print("Routing to tools")
        return "tools"
    else:
        print("Routing back to supervisor")
        return "supervisor"

graph_builder.add_conditional_edges("outlook_agent", after_agent_router)
graph_builder.add_conditional_edges("github_agent", after_agent_router)
# Add edges for other agents
# graph_builder.add_conditional_edges("jira_agent", after_agent_router)
# graph_builder.add_conditional_edges("slack_agent", after_agent_router)
# graph_builder.add_conditional_edges("notion_agent", after_agent_router)

graph_builder.add_edge("tools", "supervisor")

agent_execution_graph = graph_builder.compile()

# --- MAIN EXECUTION LOGIC ---
if __name__ == "__main__":
    sample_transcript = [
        "Cool, let's wrap up.",
        "Add Yash as a reviewer on the Dummy PR?",
        "Also, book a 30-minute meeting with Yashfor tomorrow morning to sync on the deployment plan.",
        "I think that's all for now. Great work everyone.",
    ]

    initial_state = {"transcript": sample_transcript, "messages": []}

    extracted_commands = command_extractor_node(initial_state)["messages"]
    
    print("\n--- Extracted Commands ---")
    if not extracted_commands:
        print("No commands were extracted.")
    else:
        for cmd in extracted_commands:
            print(f"- {cmd.content}")
    print("--------------------------\n")

    final_tool_calls = []

    for i, command in enumerate(extracted_commands):
        print(f"\n--- EXECUTING COMMAND {i+1}: '{command.content}' ---")
        
        command_state = {"messages": [command]}
        
        for step in agent_execution_graph.stream(command_state, {"recursion_limit": 10}):
            step_name = list(step.keys())[0]
            step_state = step[step_name]
            
            print(f"  Step: {step_name}")
            
            # Check for tool calls in the messages
            if "messages" in step_state and step_state["messages"]:
                last_message = step_state["messages"][-1]
                if isinstance(last_message, AIMessage) and last_message.tool_calls:
                    print(f"    - Found tool calls: {[tc['name'] for tc in last_message.tool_calls]}")
                    final_tool_calls.extend(last_message.tool_calls)

    print("\n--- All Proposed Actions ---")
    print(json.dumps(final_tool_calls, indent=2))

    with open("output.json", "w") as f:
        json.dump(final_tool_calls, f, indent=2)

    print("\nSaved all proposed actions to output.json")

