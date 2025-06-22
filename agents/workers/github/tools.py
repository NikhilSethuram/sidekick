import os
from github import Github
from thefuzz import process

# The GITHUB_REPOSITORY is now fetched once when the module is loaded.
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

# Hardcoded GitHub username mapping
GITHUB_USER_MAP = {
    "yash": "yashg4509",
    "nikhil": "NikhilSethuram",
}

def _resolve_github_username(name: str) -> str:
    """Resolves a name to a GitHub username using the hardcoded map."""
    return GITHUB_USER_MAP.get(name.lower(), name)

def add_reviewer_to_pr(pr_name: str, reviewer: str) -> str:
    """
    Finds a pull request by its name and adds a reviewer to it.
    The repository is determined by the GITHUB_REPOSITORY environment variable.
    It can resolve 'yash' and 'nikhil' to their GitHub usernames.

    Args:
        pr_name (str): The title or part of the title of the pull request to find.
        reviewer (str): The name or GitHub username of the person to add as a reviewer.

    Returns:
        str: A message indicating success or failure.
    """
    try:
        if not REPO_NAME:
            return "Error: GITHUB_REPOSITORY environment variable not set."
            
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "Error: GITHUB_TOKEN environment variable not set."

        # Resolve the reviewer's username
        reviewer_username = _resolve_github_username(reviewer)

        g = Github(github_token)
        repo = g.get_repo(REPO_NAME)

        open_prs = repo.get_pulls(state='open')
        pr_titles = {pr.title: pr for pr in open_prs}

        if not pr_titles:
            return "No open pull requests found."

        best_match_title, score = process.extractOne(pr_name, pr_titles.keys())

        if score < 80:
            return f"Could not find a close match for PR titled '{pr_name}'. Best match was '{best_match_title}' with a score of {score}."

        pr_to_update = pr_titles[best_match_title]
        pr_to_update.create_review_request(reviewers=[reviewer_username])

        return f"Successfully added '{reviewer_username}' (resolved from '{reviewer}') as a reviewer to PR: '{best_match_title}'."

    except Exception as e:
        return f"An error occurred: {e}"

def create_github_issue(title: str, body: str = "", assignee: str = None, labels: list = None) -> str:
    """
    Creates a new GitHub issue in the repository.
    
    Args:
        title (str): The title of the issue.
        body (str): The description/body of the issue.
        assignee (str): The name or GitHub username to assign the issue to (optional).
        labels (list): List of label names to add to the issue (optional).
    
    Returns:
        str: A message indicating success or failure with the issue URL.
    """
    try:
        if not REPO_NAME:
            return "Error: GITHUB_REPOSITORY environment variable not set."
            
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "Error: GITHUB_TOKEN environment variable not set."

        g = Github(github_token)
        repo = g.get_repo(REPO_NAME)

        # Resolve assignee username if provided
        assignee_username = None
        if assignee:
            assignee_username = _resolve_github_username(assignee)

        # Create the issue
        issue = repo.create_issue(
            title=title,
            body=body or "Issue created from meeting discussion.",
            assignee=assignee_username,
            labels=labels or []
        )

        assignee_msg = f" and assigned to {assignee_username}" if assignee_username else ""
        return f"Successfully created issue #{issue.number}: '{title}'{assignee_msg}. View at: {issue.html_url}"

    except Exception as e:
        return f"An error occurred while creating the issue: {e}"
