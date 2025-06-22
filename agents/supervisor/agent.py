import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import PromptTemplate

load_dotenv()

model = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

# The descriptions are what the supervisor will see.
# The `name` must match the node name in the main graph.
available_agents_descriptions = """
- outlook_agent: An agent that can manage your Outlook calendar. Use it to schedule meetings, find free time, and send invites.
- github_agent: An agent that can interact with GitHub. Use it to manage pull requests, assign reviewers, and create issues.
"""

prompt_template = f"""
You are a supervisor agent responsible for managing a team of specialized worker agents.
Your primary role is to analyze incoming user requests and the conversation history to route them to the most appropriate agent.
You can also route to 'FINISH' if you think the user's request has been fully addressed.

**Instructions:**
1.  Thoroughly analyze the user's request and the full conversation history to understand what has already been done.
2.  Review the list of available agents below.
3.  Based on the history, choose the single best agent to handle the *next step* of the request.
4.  If no agent is suitable or the task is complete, respond with 'FINISH'.
5.  Respond ONLY with the name of the selected agent (e.g., `github_agent`) or 'FINISH'. Do not add any other text.

**Available Agents:**
{available_agents_descriptions}

**Conversation History:**
{{chat_history}}

**User Request:**
{{input}}

**Your Response:**
"""

prompt = PromptTemplate.from_template(prompt_template)
llm_chain = prompt | model


def workflow(state: dict):
    """
    This function is the supervisor's main logic. It decides which agent to call next.
    """
    messages = state["messages"]

    # The input to the supervisor is the initial user request.
    # We find the first human message in the history.
    input_text = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            input_text = msg.content
            break
    
    # The chat history for the prompt is a formatted string of all messages.
    # This gives the supervisor full context of what has been tried and what the results were.
    chat_history_str = "\n".join([f"  - {msg.type}: {msg.content}" for msg in messages])

    # Invoke the LLM chain with the formatted history and initial input.
    response = llm_chain.invoke(
        {
            "chat_history": chat_history_str,
            "input": input_text,
        }
    )

    # The result from the LLM is the name of the next agent or "FINISH".
    agent_name = response.content.strip()

    # We return this decision as an AIMessage, which the graph will use for routing.
    return {"messages": [AIMessage(content=agent_name, name="supervisor")]}


