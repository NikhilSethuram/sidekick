from typing import List, Optional
from pydantic import BaseModel, Field

class LinearCreateIssue(BaseModel):
    """Create a new Linear issue."""
    title: str = Field(description="Issue title")
    teamId: str = Field(description="Team ID to create issue in")
    description: Optional[str] = Field(None, description="Issue description (markdown supported)")
    priority: Optional[int] = Field(None, description="Priority level (1=urgent, 4=low)", ge=0, le=4)
    status: Optional[str] = Field(None, description="Initial status name")

class LinearUpdateIssue(BaseModel):
    """Update an existing Linear issue."""
    id: str = Field(description="Issue ID to update")
    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    priority: Optional[int] = Field(None, description="New priority", ge=0, le=4)
    status: Optional[str] = Field(None, description="New status name")

class LinearSearchIssues(BaseModel):
    """Search Linear issues with flexible filtering."""
    query: Optional[str] = Field(None, description="Text to search in title/description")
    teamId: Optional[str] = Field(None, description="Filter by team")
    status: Optional[str] = Field(None, description="Filter by status")
    assigneeId: Optional[str] = Field(None, description="Filter by assignee")
    labels: Optional[List[str]] = Field(None, description="Filter by labels")
    priority: Optional[int] = Field(None, description="Filter by priority")
    limit: Optional[int] = Field(10, description="Max results")

class LinearGetUserIssues(BaseModel):
    """Get issues assigned to a user."""
    userId: Optional[str] = Field(None, description="User ID (omit for authenticated user)")
    includeArchived: Optional[bool] = Field(False, description="Include archived issues")
    limit: Optional[int] = Field(50, description="Max results")

class LinearAddComment(BaseModel):
    """Add a comment to a Linear issue."""
    issueId: str = Field(description="Issue ID to comment on")
    body: str = Field(description="Comment text (markdown supported)")
    createAsUser: Optional[str] = Field(None, description="Custom username")
    displayIconUrl: Optional[str] = Field(None, description="Custom avatar URL")

# Tool implementations
def create_issue(args: LinearCreateIssue):
    """Create a new Linear issue."""
    # TODO: Implement actual Linear API call
    return {"status": "success", "message": f"Created issue: {args.title}"}

def update_issue(args: LinearUpdateIssue):
    """Update an existing Linear issue."""
    # TODO: Implement actual Linear API call
    return {"status": "success", "message": f"Updated issue: {args.id}"}

def search_issues(args: LinearSearchIssues):
    """Search Linear issues."""
    # TODO: Implement actual Linear API call
    return {"status": "success", "message": "Found matching issues"}

def get_user_issues(args: LinearGetUserIssues):
    """Get issues assigned to a user."""
    # TODO: Implement actual Linear API call
    return {"status": "success", "message": "Retrieved user issues"}

def add_comment(args: LinearAddComment):
    """Add a comment to an issue."""
    # TODO: Implement actual Linear API call
    return {"status": "success", "message": f"Added comment to issue: {args.issueId}"}

# Export tools
linear_tools = [
    create_issue,
    update_issue,
    search_issues,
    get_user_issues,
    add_comment
] 