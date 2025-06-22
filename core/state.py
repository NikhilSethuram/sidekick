from typing import Annotated, List

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, ToolMessage
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.agents import AgentFinish, AgentAction
import json


class AgentState(TypedDict):
    """
    The state of the conversation. It is passed between all nodes in the graph.

    Attributes:
        messages: A list of messages that is accumulated over time.
                  This provides the chat history to the LLMs.
        transcript: A list of strings accumulating the real-time spoken text.
                    This is the "context" the supervisor will analyze.
        next: The name of the next agent to be invoked.
              This is used for routing decisions.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    transcript: List[str]
    next: str


def _convert_messages_to_intermediate_steps(messages: list) -> list:
    """
    Converts a list of messages into a list of (AgentAction, observation) tuples.
    This is used to create the "agent_scratchpad".
    """
    intermediate_steps = []
    for i in range(len(messages) - 1):
        if isinstance(messages[i], AIMessage) and messages[i].tool_calls:
            if isinstance(messages[i+1], ToolMessage):
                ai_msg = messages[i]
                tool_msg = messages[i+1]
                for tool_call in ai_msg.tool_calls:
                    if tool_call["id"] == tool_msg.tool_call_id:
                        action = AgentAction(
                            tool=tool_call["name"],
                            tool_input=tool_call["args"],
                            log=f"Invoking tool {tool_call['name']} for {tool_call['id']}",
                            tool_call_id=tool_call["id"],
                        )
                        intermediate_steps.append((action, tool_msg.content))
    return intermediate_steps


class AgentRunnable(Runnable):
    """A runnable that wraps an agent and its tools."""
    def __init__(self, agent, tools, name, description):
        self.agent = agent
        self.tools = {tool.name: tool for tool in tools}
        self.name = name
        self.description = description

    def invoke(self, state: AgentState, config: RunnableConfig = None):
        # The agent returns a list of actions or a final response.
        messages = state["messages"]
        last_human_message_idx = -1
        for i, msg in enumerate(reversed(messages)):
            if isinstance(msg, HumanMessage):
                last_human_message_idx = len(messages) - 1 - i
                break
        
        input_content = messages[last_human_message_idx].content
        chat_history = messages[:last_human_message_idx]
        intermediate_steps = _convert_messages_to_intermediate_steps(messages[last_human_message_idx + 1:])
        
        agent_input = {
            "input": input_content,
            "chat_history": chat_history,
            "intermediate_steps": intermediate_steps,
        }

        output = self.agent.invoke(agent_input)
        # We convert the output to a message and return it.
        return self._convert_output_to_message(output)
    
    def _convert_output_to_message(self, output):
        if isinstance(output, AgentFinish):
            return {"messages": [AIMessage(content=output.return_values["output"], name=self.name)]}
        
        tool_calls = []
        for action in output:
            tool_calls.append({
                "name": action.tool,
                "args": action.tool_input,
                "id": action.tool
            })
            
        message = AIMessage(content="", tool_calls=tool_calls, name=self.name)
        return {"messages": [message]}