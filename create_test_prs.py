import os
import time
from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
# Get repository details and token from environment variables.
# Make sure to set these in your shell before running the script.
# export GITHUB_TOKEN="your_personal_access_token"
# export GITHUB_REPOSITORY="yashg4509/calhacks2025"
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

# A list of realistic pull request titles for testing.
PR_TITLES = [
    "feat: Implement user login with OAuth 2.0",
    "fix: Resolve critical session timeout bug",
    "docs: Add comprehensive contribution guidelines",
    "refactor: Streamline database query logic for performance",
    "feat: Integrate Slack for team notifications",
    "style: Update UI components to align with new brand design",
    "test: Add end-to-end tests for the payment processing flow",
    "chore: Upgrade project dependencies to resolve security vulnerabilities",
    "fix: Correct persistent typo in the public API documentation",
]

def create_test_pull_requests():
    """
    Connects to GitHub and creates a series of test pull requests.
    """
    if not TOKEN or not REPO_NAME:
        print("Error: Please set GITHUB_TOKEN and GITHUB_REPOSITORY environment variables.")
        print("Example: export GITHUB_REPOSITORY='yashg4509/calhacks2025'")
        return

    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        main_branch = repo.get_branch("main")
        main_sha = main_branch.commit.sha
    except GithubException as e:
        print(f"Error connecting to GitHub or finding the repository: {e}")
        print("Please ensure your token has 'repo' permissions and the repository exists.")
        return

    print(f"Successfully connected to repository: {REPO_NAME}")

    for title in PR_TITLES:
        try:
            # Create a clean, unique branch name from the PR title
            branch_name = "test/" + title.lower().replace(" ", "-").replace(":", "").replace("'", "")[:50]
            file_path = f"test_files/{branch_name.replace('/', '_')}.txt"
            commit_message = f"Commit for: {title}"
            
            print(f"\nProcessing PR: '{title}'")
            print(f"  - Creating branch: {branch_name}")

            # 1. Create a new branch from main
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_sha)

            # 2. Create a new dummy file to commit
            content = f"This is a test file for the PR titled '{title}'."
            repo.create_file(
                path=file_path,
                message=commit_message,
                content=content,
                branch=branch_name,
            )
            print(f"  - Created and committed file: {file_path}")

            # 3. Create the pull request
            pr_body = f"This PR is for testing purposes.\nIt addresses the task: **{title}**."
            pr = repo.create_pull(
                title=title,
                body=pr_body,
                head=branch_name,
                base="main",
            )
            print(f"  - Successfully created Pull Request #{pr.number}: {pr.html_url}")
            
            # Pause to avoid hitting API rate limits
            time.sleep(2)

        except GithubException as e:
            # This can happen if a branch already exists or another API error occurs.
            if e.status == 422: # Unprocessable Entity
                 print(f"  - Warning: Branch '{branch_name}' might already exist. Skipping.")
            else:
                print(f"  - Error creating PR for '{title}': {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    print("\nScript finished.")

if __name__ == "__main__":
    create_test_pull_requests() 