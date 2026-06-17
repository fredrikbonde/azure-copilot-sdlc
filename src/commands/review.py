"""Review command implementation"""

from datetime import datetime
import typer
from services import (
    AgentDiscoveryService,
    CopilotAgentService,
    GitService
)
from utilities import (
    console_helper,
    validators
)
from utilities.config import get_env_variable


def build_review_prompt(work_item_id: int, project: str, branch_name: str) -> str:
    """Build comprehensive prompt for code review execution"""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return f"""You are a senior code reviewer. Your task is to review the implementation for work item #{work_item_id} on branch {branch_name}.

Review Focus Areas:
1. Security vulnerabilities - Check for injection attacks, authentication/authorization issues, data exposure
2. Correctness and logic - Verify implementation matches requirements and handles edge cases
3. Test coverage - Ensure adequate unit tests, integration tests, and critical path coverage
4. Performance - Identify potential bottlenecks, inefficient algorithms, memory leaks
5. Code quality - Check for maintainability, readability, adherence to project conventions
6. Design patterns - Verify proper use of design patterns and architectural principles

Instructions:
1. Retrieve work item #{work_item_id} in project: "{project}" from Azure DevOps to understand requirements
2. Review the COPILOT PLAN to understand the technical implementation strategy
3. Analyze all code changes on branch {branch_name}
4. Review all test cases for coverage and quality
5. Identify specific issues with actionable feedback
6. Prioritize issues by severity: Critical, High, Medium, Low

Output Format:
For each issue found, provide:
- Severity level
- File and line number(s)
- Description of the issue
- Suggested fix or improvement
- Example code if applicable

Summary:
- Overall assessment (Approved, Approved with minor comments, Request changes)
- List of critical issues requiring fixes
- List of recommendations for improvement
- Test coverage assessment

Publish the review to the pull request:
1. Locate the active pull request whose source branch is "refs/heads/{branch_name}"
   in project "{project}" using the Azure DevOps MCP tool
   `repo_list_pull_requests_by_repo_or_project` (pass project="{project}",
   sourceRefName="refs/heads/{branch_name}", status="Active").
2. From the returned pull request, read its `pullRequestId` and `repositoryId`.
3. Post the COMPLETE review (the full Markdown report above, not a summary) as a new
   comment thread on that pull request using `repo_create_pull_request_thread` with:
   - repositoryId = the pull request's repositoryId
   - pullRequestId = the pull request's pullRequestId
   - project = "{project}"
   - content = the full review in valid Markdown
   - status = "Active"
4. Prefix the comment with "# COPILOT REVIEW" and add "Generated on {timestamp} UTC".
5. Confirm the comment was created; if posting fails, report the error clearly.

Be thorough and provide constructive feedback. Focus on high-impact issues.
Generated on {timestamp} UTC
"""


def review(
    work_item_id: int = typer.Argument(..., help="Azure DevOps work item ID"),
    directory: str = typer.Option(".", "-d", "--directory", help="Working directory"),
    model: str = typer.Option(None, "-m", "--model", help="LLM model to use (e.g., gpt-5-mini, gpt-4)")
):
    """
    Review code changes for a work item.
    
    Workflow:
    1. Find feature branch
    2. Retrieve work item and plan
    3. Execute reviewer agent
    4. Post the review as a comment on the pull request

    Note: this command is advisory. It does not modify code, merge the PR, or
    change the work item state.
    """
    try:
        # Validate inputs
        work_dir = validators.validate_git_repo(directory)
        item_id = validators.validate_work_item_id(str(work_item_id))
        
        console_helper.show_info(f"Reviewing work item #{item_id}...")
        
        # Find branch
        git = GitService(work_dir)
        branch_name = f"feature/{item_id}"
        
        if not git.branch_exists(branch_name):
            console_helper.show_error(f"Branch {branch_name} not found")
            raise typer.Exit(code=1)
        
        # Switch to branch
        if not git.switch_branch(branch_name):
            raise ValueError(f"Could not switch to branch {branch_name}")
        
        # Discover agent
        discovery = AgentDiscoveryService(work_dir)
        agent = discovery.discover_agent("review")
        
         # Get Azure DevOps project name
        project = get_env_variable(
            "AZURE_DEVOPS_PROJECT",
            prompt_text="Enter Azure DevOps project name:",
            password=False
        )

        # Execute agent with comprehensive prompt
        copilot = CopilotAgentService(work_dir, model=model)
        prompt = build_review_prompt(item_id, project, branch_name)
        
        success, output = copilot.execute_agent(
            agent=agent,
            prompt=prompt,
            timeout=300
        )
        
        if not success:
            raise ValueError(f"Review failed: {output}")
        
        console_helper.show_panel("Review Results", output[:500] + "..." if len(output) > 500 else output)
        
    except Exception as e:
        console_helper.show_error(str(e))
        raise typer.Exit(code=1)
