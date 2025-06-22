import os
from dotenv import load_dotenv
from langchain.agents import create_tool_calling_agent
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

from agents.workers.github.tools import add_reviewer_to_pr, create_github_issue
from core.state import AgentRunnable

class AddReviewerSchema(BaseModel):
    """The schema for the add_reviewer_to_pr tool."""
    pr_name: str = Field(..., description="The title or part of the title of the pull request to find.")
    reviewer: str = Field(..., description="The GitHub username of the person to add as a reviewer.")

class CreateIssueSchema(BaseModel):
    """The schema for the create_github_issue tool."""
    title: str = Field(..., description="The title of the GitHub issue to create.")
    body: str = Field(default="", description="The description/body content of the issue (optional).")
    assignee: str = Field(default=None, description="The username to assign the issue to (optional).")
    labels: list = Field(default=[], description="List of label names to add to the issue (optional).")

def create_github_agent(llm: ChatAnthropic):
    """Creates an agent that can use the GitHub tools."""
    
    # 1. Define the tools this agent has access to
    tools = [
        StructuredTool(
            name="add_reviewer_to_pr",
            description="Adds a reviewer to a specific pull request in a GitHub repository. Use this when a user asks to assign someone for a code review.",
            func=add_reviewer_to_pr,
            args_schema=AddReviewerSchema,
        ),
        StructuredTool(
            name="create_github_issue",
            description="Creates a new GitHub issue in the repository. Use this when someone asks to create a bug report, feature request, or task.",
            func=create_github_issue,
            args_schema=CreateIssueSchema,
        )
    ]
    
    # 2. Create the prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", """You are a helpful assistant that is an expert at using GitHub tools. Your primary role is to determine which tool to use based on the user's request and provide the necessary arguments.

You have access to the following user information:
- Yash: 'yashg4509'
- Nikhil: 'NikhilSethuram'

When a user asks to add these users as reviewers to a PR or assign issues to them, you MUST use the corresponding GitHub username from the list above.

Your capabilities include:
- Adding reviewers to pull requests: Use add_reviewer_to_pr
- Creating GitHub issues: Use create_github_issue

When creating issues:
- Always provide a clear, descriptive title
- Include relevant details in the body when possible
- Assign to the appropriate person if mentioned
- Use common labels like 'bug', 'feature', 'task' when appropriate"""),
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
    description="A GitHub specialist for managing pull requests and issues, such as adding reviewers and creating issues."
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
        
        # Test create issue
        issue_result = create_github_issue(
            title="Test Issue from Agent",
            body="This is a test issue created by the GitHub agent.",
            assignee="yash"
        )
        print(issue_result)
    else:
        print("Please set the GITHUB_REPOSITORY environment variable.")
