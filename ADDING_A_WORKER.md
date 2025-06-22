# A Guide to Adding a New Worker Agent

The core principle of this architecture is **modularity**. Each worker is a self-contained unit that we can "plug into" the main graph. Adding a new one involves three main steps:

1.  **Create the Agent's Files**: Set up the directory and Python files for the new worker.
2.  **Define the Agent's Logic**: Write the code for the agent's tools and create the agent itself.
3.  **Integrate into the Main Graph**: Tell the supervisor about the new agent and add it to the graph's workflow.

---

## Step 1: Create the Agent's Files

First, create a new directory for your worker inside `agents/workers/`. Then, create the necessary Python files within it. As an example, let's add a **Slack** worker.

```bash
# Create the directory for the new Slack worker
mkdir agents/workers/slack

# Create the __init__.py, agent.py, and tools.py files
touch agents/workers/slack/__init__.py agents/workers/slack/agent.py agents/workers/slack/tools.py
```

Your file structure will now look like this:

```
agents/
└── workers/
    ├── github/
    ├── google_calendar/
    └── slack/
        ├── __init__.py
        ├── agent.py
        └── tools.py
```

---

## Step 2: Define the Agent's Logic and Tools

This is where you'll write the code that actually interacts with the external service (e.g., the Slack API).

### A. Define the Tools (`agents/workers/slack/tools.py`)

In this file, you create the functions that perform the actions. Each function should be decorated with `@tool` to make it available to the agent.

```python
# In agents/workers/slack/tools.py

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# It's good practice to define the schema for your tool's inputs
class PostMessageSchema(BaseModel):
    channel: str = Field(description="The channel to post the message in (e.g., #general).")
    message: str = Field(description="The content of the message to post.")

@tool(args_schema=PostMessageSchema)
def post_message(channel: str, message: str) -> str:
    """Posts a message to a specified Slack channel."""
    
    # This is where you would add your code to call the Slack API
    # For example: slack_client.chat_postMessage(channel=channel, text=message)
    print(f"--- TOOL: Posting message to {channel}: '{message}' ---")
    
    return f"Successfully posted message to {channel}."

# You can define as many tools as you need in this file
# @tool
# def ...
```

### B. Create the Agent (`agents/workers/slack/agent.py`)

This file is responsible for taking the tools you just defined and "binding" them to an LLM. This creates the agent that can intelligently decide *which* tool to use based on the user's request.

```python
# In agents/workers/slack/agent.py

from langchain.agents import create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Import the tools from your tools.py file
from .tools import post_message

def create_slack_agent(llm: ChatAnthropic):
    """Creates the agent that can use the Slack tools."""
    
    # 1. Define the tools this agent has access to
    tools = [post_message]
    
    # 2. Create the prompt
    # The prompt tells the agent its purpose and how to behave.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant that is an expert at using Slack tools."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 3. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return agent, tools
```

---

## Step 3: Integrate into the Main Graph

Finally, you need to tell your main graph in `core/main_graph.py` that this new worker exists.

1.  **Import the new agent**:
    ```python
    # In core/main_graph.py
    
    # ... other imports
    from agents.workers.slack.agent import create_slack_agent
    ```

2.  **Instantiate the agent and add it as a node**:
    ```python
    # In core/main_graph.py

    # ... where you define your model ...
    llm = ChatAnthropic(model="claude-3-opus-20240229") # Or your chosen model
    
    # Create the agent and add it to a dictionary of agents
    slack_agent, slack_tools = create_slack_agent(llm)
    
    # It's helpful to have a function that creates the final agent node
    def agent_node_func(state, agent, name):
        result = agent.invoke(state)
        return {"messages": [result]}

    # ... inside your graph definition ...
    graph_builder = StateGraph(AgentState)
    
    # ... other nodes ...
    graph_builder.add_node("slack_agent", lambda state: agent_node_func(state, slack_agent, "slack_agent"))
    ```

3.  **Tell the supervisor about the new worker**:
    This is the most important part. The supervisor needs to know that "slack_agent" is now an option. You'll do this by updating its prompt or logic.
    ```python
    # In agents/supervisor/agent.py (when you build it)
    
    # The supervisor's prompt will list the available workers:
    system_prompt = """
    You are a supervisor tasked with managing a conversation...
    The workers you have access to are: 'google_calendar_agent', 'github_agent', 'slack_agent'.
    Given the conversation history, determine which worker should act next...
    """
    ```

4.  **Add the edge to the graph**:
    Connect your new agent node to the `after_agent_router` so it follows the same logic as the other workers.
    ```python
    # In core/main_graph.py

    # ... other edges ...
    graph_builder.add_conditional_edges("slack_agent", after_agent_router)
    ```

And that's it! By following this pattern, you can add as many specialized workers as you need, keeping your codebase organized and easy to maintain. 