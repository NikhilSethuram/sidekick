import os
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

# We will implement these later, for now, they are placeholders
# from agents.supervisor.agent import Supervisor
# from agents.workers.google_calendar.agent import (
#     create_google_calendar_agent,
#     google_calendar_tools,
# )
from .state import AgentState

# This is a placeholder for the real supervisor agent
def supervisor_node(state: AgentState):
    print("---SUPERVISOR---")
    # In the real implementation, this would involve a call to an LLM
    # to decide the next step based on state['transcript']
    print(state)
    if not state.get("messages"):
        # If there are no messages, it's the first turn
        next_agent = "google_calendar"
        print(f"Routing to {next_agent}")
        return {"next": next_agent}
    else:
        # After a worker has acted, we end the conversation for now
        print("Ending conversation")
        return {"next": "end"}


# This is a placeholder for a real worker agent
def agent_node(state: AgentState):
    print(f"---AGENT: {state['next']}---")
    # This will be replaced by the actual agent's logic,
    # which will likely call tools
    print(state)
    message = HumanMessage(content="This is a placeholder message from the agent.")
    return {"messages": [message]}


# The final graph is created here
graph_builder = StateGraph(AgentState)

# 1. Define the nodes
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("google_calendar_agent", agent_node) # Placeholder
graph_builder.add_node("github_agent", agent_node) # Placeholder
# tool_node = ToolNode([]) # Placeholder for tools
# graph_builder.add_node("tools", tool_node)

# 2. Define the edges
graph_builder.add_edge(START, "supervisor")

# This is the conditional router that reads the 'next' field in the state
def router(state: AgentState):
    if state["next"] == "end":
        return END
    return state["next"]

graph_builder.add_conditional_edges("supervisor", router)

# Workers will eventually route to the tool node, and the tool node will route
# back to the supervisor. For now, we'll just have them route back to the supervisor
# to demonstrate the loop.
graph_builder.add_edge("google_calendar_agent", "supervisor")
graph_builder.add_edge("github_agent", "supervisor")


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


