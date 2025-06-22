import os
import json
from typing import Dict, Any
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage

from .tools import (
    linear_tools,
    LinearCreateIssue,
    LinearUpdateIssue,
    LinearSearchIssues,
    LinearGetUserIssues,
    LinearAddComment
)

# Initialize the model
model = ChatAnthropic(model=os.environ.get("MODEL_NAME", "claude-3-5-sonnet-20241022"))

class LinearAgent:
    def __init__(self):
        self.tools = {
            "linear_create_issue": (linear_tools[0], LinearCreateIssue),
            "linear_update_issue": (linear_tools[1], LinearUpdateIssue),
            "linear_search_issues": (linear_tools[2], LinearSearchIssues),
            "linear_get_user_issues": (linear_tools[3], LinearGetUserIssues),
            "linear_add_comment": (linear_tools[4], LinearAddComment)
        }
        
        # Build tool descriptions for prompt
        tool_descriptions = []
        for name, (tool, model) in self.tools.items():
            tool_descriptions.append(f"- {name}: {model.__doc__}")
        self.tool_descriptions = "\n".join(tool_descriptions)
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Linear-related request."""
        # Format conversation history
        messages = []
        for msg in state["messages"]:
            if isinstance(msg, (HumanMessage, AIMessage)):
                messages.append(msg)
        
        # Get agent response
        prompt = f"""You are a Linear task management expert. Your job is to help manage tasks and issues in Linear.

Available tools:
{self.tool_descriptions}

For each request:
1. Understand the task requirements
2. Select the appropriate tool(s)
3. Format the arguments correctly
4. Return the tool call for execution

Example:
"Create a high priority task for the auth bug" -> Use linear_create_issue with:
{{
    "title": "Authentication Bug",
    "teamId": "TEAM_ID",
    "priority": 1,
    "description": "Critical authentication system bug that needs immediate attention"
}}

To use a tool, respond in this format:
<tool>tool_name</tool>
<args>
{{
    "arg1": "value1",
    "arg2": "value2"
}}
</args>

If you cannot handle the request or need more information, respond with "FINISH".

User Request: {messages[-1].content}

Your Response:"""
        
        response = model.invoke(prompt)
        
        # Parse tool call from response
        content = response.content
        if "<tool>" in content and "</tool>" in content:
            tool_start = content.find("<tool>") + 6
            tool_end = content.find("</tool>")
            tool_name = content[tool_start:tool_end].strip()
            
            args_start = content.find("<args>") + 6
            args_end = content.find("</args>")
            args_str = content[args_start:args_end].strip()
            
            try:
                args_dict = json.loads(args_str)
                tool_func, tool_model = self.tools.get(tool_name, (None, None))
                if tool_func and tool_model:
                    args = tool_model(**args_dict)
                    result = tool_func(args)
                    return {"messages": [AIMessage(content=f"Successfully executed {tool_name}: {result}")], "next": "FINISH"}
                else:
                    return {"messages": [AIMessage(content=f"Error: Tool {tool_name} not found")], "next": "FINISH"}
            except Exception as e:
                return {"messages": [AIMessage(content=f"Error executing tool: {str(e)}")], "next": "FINISH"}
        elif "FINISH" in content:
            return {"messages": [AIMessage(content="Cannot handle this request.")], "next": "FINISH"}
        
        return {"messages": [response], "next": "FINISH"}

# Export the agent instance
linear_agent = LinearAgent() 