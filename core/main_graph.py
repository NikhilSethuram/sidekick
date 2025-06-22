import os
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

# We will implement these later, for now, they are placeholders
# from agents.supervisor.agent import Supervisor
# from agents.workers.google_calendar.agent import (
#     create_google_calendar_agent,
#     google_calendar_tools,
# )

# Import the Outlook calendar agent
from agents.workers.outlook_calendar.agent import create_outlook_calendar_agent
from core.state import AgentState

# Initialize the LLM
llm = ChatAnthropic(model="claude-3-opus-20240229")

# Create the Outlook calendar agent
outlook_agent, outlook_tools = create_outlook_calendar_agent(llm)

# This is a placeholder for the real supervisor agent
def supervisor_node(state: AgentState):
    print("---SUPERVISOR---")
    # In the real implementation, this would involve a call to an LLM
    # to decide the next step based on state['transcript']
    
    print(state)
    # For the skeleton, we'll just check if there are any messages yet.
    # If not, we'll route to a worker. Otherwise, we'll end.
    if len(state["messages"]) < 2:
        # Check transcript for keywords to route to appropriate agent
        transcript_text = " ".join(state.get("transcript", [])).lower()
        
        # Route to Outlook calendar agent for email/meeting related requests
        if any(keyword in transcript_text for keyword in ["email", "send", "meeting", "schedule", "calendar", "outlook"]):
            next_agent = "outlook_calendar_agent"
        else:
            next_agent = "google_calendar_agent"  # default fallback
            
        print(f"Routing to {next_agent}")
        return {"next": next_agent}
    else:
        # After a worker has acted and the loop is complete
        print("Ending conversation")
        return {"next": "end"}


# This is a placeholder for a real worker agent
def agent_node(state: AgentState):
    print(f"---AGENT: {state['next']}---")
    # This will be replaced by the actual agent's logic.
    # A real agent would return an AIMessage with tool_calls or final content.
    # This placeholder simulates a final response from the agent.
    print(state)
    message = AIMessage(
        content=f"This is a placeholder response from the {state['next']} agent.",
        name=state["next"],
    )
    return {"messages": [message]}

# Function to create the final agent node for Outlook calendar
def outlook_agent_node(state: AgentState):
    print(f"---OUTLOOK CALENDAR AGENT---")
    print(state)
    # Get the last human message as input
    last_human_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_human_message = msg.content
            break
    
    if not last_human_message:
        # If no human message, use transcript
        last_human_message = " ".join(state.get("transcript", []))
    
    # Invoke the Outlook agent
    result = outlook_agent.invoke({
        "input": last_human_message,
        "chat_history": state["messages"]
    })
    
    return {"messages": [result]}


# The final graph is created here
graph_builder = StateGraph(AgentState)

# 1. Define the nodes
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("google_calendar_agent", agent_node)
graph_builder.add_node("github_agent", agent_node)
graph_builder.add_node("outlook_calendar_agent", outlook_agent_node)

# The ToolNode is a pre-built node that executes tools.
# Initialize it with the Outlook tools
tool_node = ToolNode(outlook_tools)
graph_builder.add_node("tools", tool_node)


# 2. Define the edges
graph_builder.add_edge(START, "supervisor")

# The supervisor routes to a worker or ends the conversation
def supervisor_router(state: AgentState):
    if state["next"] == "end":
        return END
    return state["next"]

graph_builder.add_conditional_edges("supervisor", supervisor_router)

# This router checks if the worker's response contains tool calls.
# If so, it routes to the 'tools' node. Otherwise, it routes back to the supervisor.
def after_agent_router(state: AgentState):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    else:
        return "supervisor"

# Edges from the workers go to our new router
graph_builder.add_conditional_edges("google_calendar_agent", after_agent_router)
graph_builder.add_conditional_edges("github_agent", after_agent_router)
graph_builder.add_conditional_edges("outlook_calendar_agent", after_agent_router)

# The tool node always routes back to the supervisor
graph_builder.add_edge("tools", "supervisor")


# 3. Compile the graph
graph = graph_builder.compile()

# You can visualize the graph with this line (requires a few extra installs)
# from IPython.display import Image, display
# display(Image(graph.get_graph().draw_png()))


# This is how you would run the graph
if __name__ == "__main__":
    # The initial state can be populated with the initial transcript
    initial_state = {
        "transcript": ["Hello, I need to schedule a meeting."],
        "messages": [],
    }
    # The stream() method allows us to see the state at each step
    for step in graph.stream(initial_state):
        print(f"Step: {list(step.keys())[0]}")
        print(step)
        print("---")


