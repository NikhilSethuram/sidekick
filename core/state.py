from typing import Annotated, List

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages


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