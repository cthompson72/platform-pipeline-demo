"""
AI-Powered Code Review using Claude API.
Enriched with Jira ticket context when an experience ID is available.
"""

import os
import sys
import json
import re
import urllib.request
import urllib.error


def get_pr_diff():
    """Fetch the PR diff, prioritizing application code."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    token = os.environ.get("GITHUB_TOKEN")

    if not all([repo, pr_number, token]):
        print("Missing required environment variables")
        sys.exit(1)

    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
        "X-GitHub-Api-Version": "2022-11-28"
    })

    try:
        with urllib.request.urlopen(req) as response:
            full_diff = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch PR diff: {e.code} {e.reason}")
        sys.exit(1)

    # Split into per-file sections and prioritize app code
    file_diffs = re.split(r'(?=^diff --git)', full_diff, flags=re.MULTILINE)
    app_code = []
    infra_code = []

    for section in file_diffs:
        if not section.strip():
            continue
        header = section[:200]
        if any(p in header for p in ['scripts/', '.github/', '.gitleaks']):
            infra_code.append(section)
        elif any(ext in header for ext in ['.java', '.py', '.js', '.ts']):
            app_code.append(section)
        else:
            infra_code.append(section)

    prioritized = "\n".join(app_code + infra_code)
    max_length = 30000
    if len(prioritized) > max_length:
        prioritized = prioritized[:max_length] + "\n\n... [diff truncated]"

    print(f"Diff: {len(app_code)} app files, {len(infra_code)} infra files, {len(prioritized)} chars")
    return prioritized


def call_claude(diff):
    """Send the diff to Claude for review."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    jira_context = ""
    ticket_id = os.environ.get("TICKET_ID", "")
    ticket_summary = os.environ.get("TICKET_SUMMARY", "")
    ticket_description = os.environ.get("TICKET_DESCRIPTION", "")
    if ticket_id:
        jira_context = f"""
Jira Ticket Context:
- Ticket: {ticket_id}
- Summary: {ticket_summary}
- Description: {ticket_description}
Use this context to evaluate whether the code changes actually address what the ticket describes.
If the code doesn't match the ticket intent, flag it as a CRITICAL finding.
"""

    prompt = f"""You are a senior software engineer performing a code review on a pull request.
{jira_context}
Analyze the following diff and provide a review focusing on issues that static analysis tools
like Semgrep and SonarQube would NOT catch. Specifically look for:

1. **Ticket Alignment**: Do the code changes actually address what the Jira ticket describes?
2. **Logic Errors**: Does the code actually do what the PR title/comments suggest?
3. **Security Context**: Is sensitive data handled appropriately?
4. **API Compatibility**: Would these changes break existing API consumers?
5. **Error Handling**: Are edge cases covered?
6. **Business Logic**: Does the change make sense in the broader application context?
7. **Documentation Drift**: Do comments still match what the code does?

Format your response as a structured review:
- Start with a one-line summary
- If a Jira ticket is linked, assess whether the changes match the ticket intent
- List findings with severity (CRITICAL / WARNING / SUGGESTION)
- For each finding, explain WHY it matters
- End with what the PR does WELL

If the code looks clean, say so. Don't manufacture findings.

Here is the diff:
````diff
{diff}
```"""

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Claude API error: {e.code} {error_body}")
        sys.exit(1)


def post_pr_comment(review_text):
    """Post the review as a PR comment."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    token = os.environ.get("GITHUB_TOKEN")

    ticket_id = os.environ.get("TICKET_ID", "")
    jira_base = os.environ.get("JIRA_BASE_URL", "")
    jira_link = ""
    if ticket_id and jira_base:
        jira_link = f"\n**Experience ID**: [{ticket_id}]({jira_base}/browse/{ticket_id})\n"

    comment_body = f"""## AI Code Review (Powered by Claude)
{jira_link}
{review_text}

---
*Automated review focusing on contextual issues that static analysis tools may miss.*
"""

    body = json.dumps({"body": comment_body}).encode("utf-8")
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    })

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"Comment posted: {result['html_url']}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Failed to post comment: {e.code} {error_body}")
        sys.exit(1)


def main():
    print("Fetching PR diff...")
    diff = get_pr_diff()

    ticket_id = os.environ.get("TICKET_ID", "")
    if ticket_id:
        print(f"Experience ID: {ticket_id}")
    else:
        print("No Experience ID — reviewing without Jira context")

    print("Sending to Claude for review...")
    review = call_claude(diff)
    print("Review received:")
    print(review)

    print("\nPosting review comment to PR...")
    post_pr_comment(review)
    print("Done!")


if __name__ == "__main__":
    main()