import os
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.runnables import Runnable, RunnableLambda, RunnableConfig
from typing import Any, Dict, List

# Import the tools from your tools.py file
from .tools import send_email, schedule_meeting

def create_outlook_calendar_agent(llm: ChatAnthropic):
    """Creates the agent that can use the Outlook calendar tools."""
    
    # 1. Define the tools this agent has access to
    tools = [send_email, schedule_meeting]
    
    # 2. Create the prompt
    # The prompt tells the agent its purpose and how to behave.
    # It now includes agent_scratchpad for tool usage history.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are a helpful assistant that is an expert at using Microsoft Outlook tools for email and calendar management.

You have access to the following user information:
- Yash: 'ysgupta@wisc.edu'
- Nikhil: 'nst@wisc.edu'

When a user asks to schedule a meeting with these users, you MUST use the corresponding email from the list above.

You capabilities include:
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
- Tool: schedule_meeting

When sending emails:
- Ensure all email addresses are valid format
- Provide clear, professional subject lines
- Write appropriate email content
- Tool: send_email

Be helpful, professional, and efficient in your responses."""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 3. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return agent, tools

# This helper function converts the message history from the supervisor
# into the "intermediate_steps" format that the agent expects.
def _convert_messages_to_intermediate_steps(messages: list) -> list:
    """
    Converts a list of messages into a list of (AgentAction, observation) tuples.
    This is used to create the "agent_scratchpad".
    """
    intermediate_steps = []
    # We are looking for pairs of AI and Tool messages.
    for i in range(len(messages) - 1):
        if isinstance(messages[i], AIMessage) and messages[i].tool_calls:
            if isinstance(messages[i+1], ToolMessage):
                ai_msg = messages[i]
                tool_msg = messages[i+1]
                # Reconstruct the actions and observations
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

# This adapter is the key to making the supervisor and the worker compatible.
# It takes the state from the supervisor and transforms it into the format
# that the create_tool_calling_agent expects.
def _agent_adapter(state: dict) -> dict:
    """
    Adapts the supervisor's state to the agent's expected input format.
    
    The supervisor passes the entire message history. We need to parse this
    to find the most recent human message as the input, and all preceding
    messages as the chat history. Tool calls since the last human message
    are formatted as intermediate steps for the agent's scratchpad.
    """
    messages = state["messages"]
    
    # Find the index of the last HumanMessage
    last_human_message_idx = -1
    for i, msg in enumerate(reversed(messages)):
        if isinstance(msg, HumanMessage):
            last_human_message_idx = len(messages) - 1 - i
            break
            
    # The input to the agent is the content of the last HumanMessage
    input_content = messages[last_human_message_idx].content
    
    # The chat history is everything before the last HumanMessage
    chat_history = messages[:last_human_message_idx]
    
    # The intermediate steps are the tool calls after the last HumanMessage
    intermediate_steps_messages = messages[last_human_message_idx + 1 :]
    intermediate_steps = _convert_messages_to_intermediate_steps(
        intermediate_steps_messages
    )
    
    return {
        "input": input_content,
        "chat_history": chat_history,
        "intermediate_steps": intermediate_steps,
    }

# This custom runnable class wraps the base agent and the adapter logic.
# This is necessary so we can attach the .name and .tools attributes
# that the supervisor expects.
class AgentRunnable(Runnable):
    def __init__(self, agent: Runnable, tools: list, name: str):
        self.agent = agent
        self.tools = tools
        self.name = name

    def _convert_output_to_message(self, output: Any) -> Dict[str, List[BaseMessage]]:
        """Converts the agent's output (AgentAction) to a message dictionary."""
        if isinstance(output, AgentFinish):
            # The agent has finished, return its final response.
            return {"messages": [AIMessage(content=output.return_values["output"])]}

        # The output is a list of actions
        tool_calls = []
        for action in output:
            if isinstance(action, AgentAction) and action.tool_call_id:
                tool_calls.append(
                    {
                        "name": action.tool,
                        "args": action.tool_input,
                        "id": action.tool_call_id,
                        "type": "tool_call",
                    }
                )
        message = AIMessage(content="", tool_calls=tool_calls)
        return {"messages": [message]}

    def invoke(self, state: Dict[str, Any], config: RunnableConfig | None = None) -> Any:
        # Adapt the state from the supervisor to the agent's expected format
        adapted_input = _agent_adapter(state)
        # Invoke the underlying agent
        output = self.agent.invoke(adapted_input, config)
        return self._convert_output_to_message(output)

    # We need to implement ainvoke for async operations
    async def ainvoke(
        self, state: Dict[str, Any], config: RunnableConfig | None = None, **kwargs: Any
    ) -> Any:
        adapted_input = _agent_adapter(state)
        output = await self.agent.ainvoke(adapted_input, config, **kwargs)
        return self._convert_output_to_message(output)

load_dotenv()

# Instantiate the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Create the base agent and tools
base_agent, outlook_tools = create_outlook_calendar_agent(llm)

# Create an instance of our custom runnable
outlook_agent = AgentRunnable(
    agent=base_agent, 
    tools=outlook_tools, 
    name="outlook_agent"
)
