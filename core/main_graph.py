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

# Import the supervisor workflow
from agents.supervisor.agent import workflow as supervisor_workflow
# Import the Outlook calendar agent and tools directly
from agents.workers.outlook_calendar.agent import outlook_agent, outlook_tools
from core.state import AgentState

# Initialize the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME"))

# The supervisor node now simply invokes our compiled supervisor workflow
def supervisor_node(state: AgentState):
    """Invokes the supervisor to decide the next step."""
    print("---SUPERVISOR---")
    # The supervisor returns a dict with a "messages" key.
    result = supervisor_workflow.invoke(state)
    print(f"Supervisor result: {result}")
    # The last message in the list is the supervisor's decision.
    last_message = result["messages"][-1]
    
    # The content of the last message is the name of the next agent to call.
    # It can also be "FINISH" to end the graph.
    next_agent = last_message.content
    
    return {"next": next_agent}


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
    """Invokes the outlook agent and returns its result."""
    print("---OUTLOOK AGENT---")
    result = outlook_agent.invoke(state)
    # The agent's response is already in the correct format.
    return result


# The final graph is created here
graph_builder = StateGraph(AgentState)

# 1. Define the nodes
graph_builder.add_node("supervisor", supervisor_node)
graph_builder.add_node("outlook_agent", outlook_agent_node)

# The ToolNode is a pre-built node that executes tools.
# Initialize it with the Outlook tools
tool_node = ToolNode(outlook_tools)
graph_builder.add_node("tools", tool_node)


# 2. Define the edges
graph_builder.add_edge(START, "supervisor")

# The supervisor routes to a worker or ends the conversation
def supervisor_router(state: AgentState):
    print(f"---ROUTING---")
    print(f"Next step is: {state['next']}")
    if state["next"] == "FINISH":
        return END
    return state["next"]

graph_builder.add_conditional_edges("supervisor", supervisor_router)

# This router checks if the worker's response contains tool calls.
# If so, it routes to the 'tools' node. Otherwise, it routes back to the supervisor.
def after_agent_router(state: AgentState):
    print("---AGENT ROUTER---")
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        print("Routing to tools")
        return "tools"
    else:
        print("Routing back to supervisor")
        return "supervisor"

# Edges from the workers go to our new router
graph_builder.add_conditional_edges("outlook_agent", after_agent_router)

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
    # initial_state = {
    #     "messages": [HumanMessage(content="Please send an email to ysgupta@wisc.edu. The subject should be 'Hello from the agent' and the body should be 'This is a test message from the multi-agent system.'")],
    # }
    # # The stream() method allows us to see the state at each step
    # for step in graph.stream(initial_state, {"recursion_limit": 10}):
    #     print(f"Step: {list(step.keys())[0]}")
    #     print(step)
    #     print("---")

    # Import the transcription client
    from tools.audio.whisper_groq import run_transcription_client
    import sys
    # Add the whisperlive directory to the path
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'whisperlive_env', 'WhisperLive'))

    class TranscriptionHandler:
        def __init__(self, graph):
            self.graph = graph
            self.transcript_buffer = ""
            self.is_agent_working = False

        def handle_transcription(self, transcript: str):
            """
            This function is called when a new transcription is available.
            It accumulates the transcript, checks for a command, and then
            feeds the transcript into the graph and prints the final result.
            """
            if self.is_agent_working:
                print("Agent is busy. Ignoring new transcript...")
                return

            print(f"\n--- TRANSCRIPTION RECEIVED ---\n{transcript}\n------------------------------")
            
            self.transcript_buffer = transcript

            trigger_words = [
                "schedule", "book", "find", "add", "create", "send", "post", "merge", 
                "assign", "remind", "update", "delete", "get", "pull", "push",
                "run", "execute", "what", "who", "where", "when", "why", "how"
            ]
            if not any(word in self.transcript_buffer.lower() for word in trigger_words):
                print("No trigger word detected. Waiting for a command...")
                return

            self.is_agent_working = True
            
            print("--- TRIGGER WORD DETECTED ---")
            print("--- INVOKING AGENT ---")

            initial_state = {
                "messages": [HumanMessage(content=self.transcript_buffer)],
            }
            
            final_state = None
            try:
                for step in self.graph.stream(initial_state, {"recursion_limit": 15}):
                    print(f"Step: {list(step.keys())[0]}")
                    final_state = step

                if final_state:
                    print("--- AGENT WORK COMPLETE ---")
                    final_message = final_state[list(final_state.keys())[0]]['messages'][-1]
                    print(f"Final Response: {final_message.content}")
            
            except Exception as e:
                print(f"--- AGENT ERROR ---")
                print(f"An error occurred: {e}")

            finally:
                print("--- CLEARING TRANSCRIPT BUFFER ---")
                self.transcript_buffer = ""
                self.is_agent_working = False
                print("\n🎤 Listening for next command...")

    handler = TranscriptionHandler(graph)

    print("Starting audio transcription client...")
    print("Speak into your microphone. The agent will respond when it has a complete thought.")
    run_transcription_client(handler.handle_transcription)


