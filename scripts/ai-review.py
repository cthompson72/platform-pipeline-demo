"""
AI-Powered Code Review using Claude API.
Reads the PR diff, sends it to Claude for contextual analysis,
and posts findings as a PR comment.
"""

import os
import sys
import json
import urllib.request
import urllib.error


def get_pr_diff():
    """Fetch the PR diff from GitHub API."""
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
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch PR diff: {e.code} {e.reason}")
        sys.exit(1)


def call_claude(diff):
    """Send the diff to Claude for review."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    # Truncate very large diffs to stay within token limits
    max_diff_length = 15000
    if len(diff) > max_diff_length:
        diff = diff[:max_diff_length] + "\n\n... [diff truncated for length]"

    prompt = f"""You are a senior software engineer performing a code review on a pull request.
Analyze the following diff and provide a review focusing on issues that static analysis tools 
like Semgrep and SonarQube would NOT catch. Specifically look for:

1. **Logic Errors**: Does the code actually do what the PR title/comments suggest?
2. **Security Context**: Is sensitive data handled appropriately? Are there authorization gaps?
3. **API Compatibility**: Would these changes break existing API consumers?
4. **Error Handling**: Are edge cases covered? Are errors handled gracefully?
5. **Race Conditions**: Any concurrency issues in shared state?
6. **Business Logic**: Does the change make sense in the broader application context?
7. **Documentation Drift**: Do comments still match what the code does?

Format your response as a structured review:
- Start with a one-line summary of the overall change
- List findings with severity (CRITICAL / WARNING / SUGGESTION)
- For each finding, explain WHY it matters, not just what you found
- End with what the PR does WELL (positive feedback matters)

If the code looks clean, say so. Don't manufacture findings.

Here is the diff:
````diff
{diff}
```"""

    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2048,
        "messages": [
            {"role": "user", "content": prompt}
        ]
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
    """Post the review as a comment on the PR."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    token = os.environ.get("GITHUB_TOKEN")

    comment_body = f"""## 🤖 AI Code Review (Powered by Claude)

{review_text}

---
*This review was generated automatically by the AI Code Review pipeline stage. 
It focuses on contextual issues that static analysis tools may miss.*
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
    print(f"Diff size: {len(diff)} characters")

    print("Sending to Claude for review...")
    review = call_claude(diff)
    print("Review received:")
    print(review)

    print("\nPosting review comment to PR...")
    post_pr_comment(review)
    print("Done!")


if __name__ == "__main__":
    main()
