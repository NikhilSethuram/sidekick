import os
import json
from typing import List
from datetime import datetime

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

# The supervisor has been repurposed to be a command extractor.
from agents.supervisor.agent import workflow as command_extractor_workflow
from agents.workers.outlook_calendar.agent import outlook_agent, outlook_tools
from core.state import AgentState
from agents.workers.github.agent import github_agent, github_tools
# Skip Jira for now
# from agents.workers.jira.agent import jira_agent, jira_tools

# Initialize the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME", "claude-3-5-sonnet-20241022"))


# --- Routing Supervisor Logic ---
# This supervisor is for routing a single command to the correct worker agent.
available_agents_descriptions = """
- outlook_agent: An agent that can manage your Outlook calendar. Use it to schedule meetings, find free time, and send invites.
- github_agent: An agent that can interact with GitHub. Use it to manage pull requests, assign reviewers, and create issues.
- slack_agent: An agent that can send messages to Slack channels.
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
# Skip Jira for now
# graph_builder.add_node("jira_agent", jira_agent_node)
# Placeholder nodes for other agents. They need to be implemented.
# graph_builder.add_node("slack_agent", slack_agent_node)
# graph_builder.add_node("notion_agent", notion_agent_node)


tool_node = ToolNode(outlook_tools + github_tools) # Removed jira_tools
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "supervisor")

def supervisor_router(state: AgentState):
    """Routes from the supervisor to the correct agent or ends."""
    print(f"---ROUTING---")
    last_message = state["messages"][-1]
    next_agent = last_message.content
    print(f"Next step is: {next_agent}")
    if next_agent == "FINISH" or next_agent not in ["outlook_agent", "github_agent"]: # Removed jira_agent
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
# Skip Jira for now
# graph_builder.add_conditional_edges("jira_agent", after_agent_router)
# Add edges for other agents
# graph_builder.add_conditional_edges("slack_agent", after_agent_router)
# graph_builder.add_conditional_edges("notion_agent", after_agent_router)

graph_builder.add_edge("tools", "supervisor")

agent_execution_graph = graph_builder.compile()

# --- MAIN EXECUTION LOGIC ---
if __name__ == "__main__":
    # 1. Load existing proposed actions (but don't track processed commands)
    proposed_actions = []
    output_file = "output.json"

    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            try:
                existing_actions = json.load(f)
                # Keep existing actions that haven't been approved/rejected yet
                proposed_actions = [action for action in existing_actions if action.get("status") == "pending_approval"]
            except json.JSONDecodeError:
                pass # File is empty or corrupt, start fresh

    # 2. Define a sample meeting transcript (in a real scenario, this would be fetched live)
    sample_transcript = [
        "This is a test attempt.",
        "this is a test attempt recording in progress checking if whisper works thank you",
        "this is a test attempt recording in progress checking if whisper works thank Thank you."
    ]

    initial_state = {"transcript": sample_transcript, "messages": []}

    # 3. Extract all commands from the current transcript.
    extracted_commands = command_extractor_node(initial_state)["messages"]
    
    print("\n--- Extracted Commands ---")
    if not extracted_commands:
        print("No commands were extracted.")
    else:
        for cmd in extracted_commands:
            print(f"- {cmd.content}")
    print("--------------------------\n")

    # 4. Process ALL commands (no filtering for already processed)
    if not extracted_commands:
        print("No commands to process.")
    else:
        # 5. Loop through ALL commands and PROPOSE actions (don't execute)
        for i, command in enumerate(extracted_commands):
            print(f"\n--- ANALYZING COMMAND {i+1}/{len(extracted_commands)}: '{command.content}' ---")
            
            command_state = {"messages": [command]}
            current_tool_calls = []
            
            # Run the agent workflow but STOP before tool execution
            for step in agent_execution_graph.stream(command_state, {"recursion_limit": 10}):
                step_name = list(step.keys())[0]
                step_state = step[step_name]
                
                print(f"  Step: {step_name}")
                
                # IMPORTANT: Stop at tool calls - don't execute them
                if step_name == "tools":
                    print("    - Skipping tool execution (waiting for user approval)")
                    break
                
                if "messages" in step_state and step_state["messages"]:
                    last_message = step_state["messages"][-1]
                    
                    # Capture tool calls as PROPOSALS
                    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls") and last_message.tool_calls:
                        print(f"    - Found tool call proposals: {[tc['name'] for tc in last_message.tool_calls]}")
                        current_tool_calls.extend(last_message.tool_calls)
            
            # Convert tool calls to proposed actions (no execution)
            for tool_call in current_tool_calls:
                proposed_action = {
                    "tool_name": tool_call["name"],
                    "arguments": tool_call["args"],
                    "id": tool_call["id"],
                    "type": "tool_call",
                    "command": command.content,
                    "status": "pending_approval",  # Key difference - waiting for approval
                    "created_at": datetime.now().isoformat()
                }
                proposed_actions.append(proposed_action)
                print(f"    - Created proposal: {tool_call['name']} with args {tool_call['args']}")

    # 6. Save the proposed actions (no execution results yet)
    print("\n--- All Proposed Actions (Awaiting Approval) ---")
    print(json.dumps(proposed_actions, indent=2))

    with open(output_file, "w") as f:
        json.dump(proposed_actions, f, indent=2)

    print(f"\nSaved {len(proposed_actions)} proposed actions to {output_file}")
    print("\n🔒 No actions were executed. Use the Streamlit interface to approve and execute actions.")

