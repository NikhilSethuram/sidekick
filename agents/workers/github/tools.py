import os
from github import Github
from thefuzz import process

# The GITHUB_REPOSITORY is now fetched once when the module is loaded.
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

def add_reviewer_to_pr(pr_name: str, reviewer: str) -> str:
    """
    Finds a pull request by its name and adds a reviewer to it.
    The repository is determined by the GITHUB_REPOSITORY environment variable.

    Args:
        pr_name (str): The title or part of the title of the pull request to find.
        reviewer (str): The GitHub username of the person to add as a reviewer.

    Returns:
        str: A message indicating success or failure.
    """
    try:
        if not REPO_NAME:
            return "Error: GITHUB_REPOSITORY environment variable not set."
            
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            return "Error: GITHUB_TOKEN environment variable not set."

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
        pr_to_update.create_review_request(reviewers=[reviewer])

        return f"Successfully added '{reviewer}' as a reviewer to PR: '{best_match_title}'."

    except Exception as e:
        return f"An error occurred: {e}"
