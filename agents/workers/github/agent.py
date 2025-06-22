import os
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from agents.workers.github.tools import add_reviewer_to_pr
from core.state import AgentRunnable

class AddReviewerSchema(BaseModel):
    """The schema for the add_reviewer_to_pr tool."""
    pr_name: str = Field(..., description="The title or part of the title of the pull request to find.")
    reviewer: str = Field(..., description="The GitHub username of the person to add as a reviewer.")

def create_github_agent(llm: ChatAnthropic):
    """Creates an agent that can use the GitHub tools."""
    
    # 1. Define the tools this agent has access to
    tools = [
        StructuredTool(
            name="add_reviewer_to_pr",
            description="Adds a reviewer to a specific pull request in a GitHub repository. Use this when a user asks to assign someone for a code review.",
            func=add_reviewer_to_pr,
            args_schema=AddReviewerSchema,
        )
    ]
    
    # 2. Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant that is an expert at using GitHub tools. Your primary role is to determine which tool to use based on the user's request and provide the necessary arguments."),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )
    
    # 3. Create the tool-calling agent
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return agent, tools

# --- Agent Definition ---
load_dotenv()

# Instantiate the LLM
llm = ChatAnthropic(model=os.environ.get("MODEL_NAME"), api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Create the base agent and tools using our new function
base_agent, github_tools = create_github_agent(llm)

# Create the final agent runnable, reusing the class from the Outlook agent
github_agent = AgentRunnable(
    agent=base_agent,
    tools=github_tools,
    name="github_agent",
    description="A GitHub specialist for managing pull requests, such as adding reviewers."
)

# --- Direct Testing Block ---
if __name__ == '__main__':
    load_dotenv()
    repo_name = os.environ.get("GITHUB_REPOSITORY")
    if repo_name:
        # This is for testing the tool function directly.
        test_result = add_reviewer_to_pr(
            pr_name="user login auth", 
            reviewer="yashg4509"
        )
        print(test_result)
    else:
        print("Please set the GITHUB_REPOSITORY environment variable.")
