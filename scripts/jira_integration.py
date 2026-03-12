"""
Jira Integration for Experience ID Pipeline.
Extracts ticket ID from branch name, fetches Jira context,
and posts pipeline results back to the ticket.
"""

import os
import sys
import json
import re
import base64
import urllib.request
import urllib.error


def get_jira_auth():
    """Build basic auth header for Jira API."""
    email = os.environ.get("JIRA_EMAIL")
    token = os.environ.get("JIRA_TOKEN")
    if not email or not token:
        print("JIRA_EMAIL or JIRA_TOKEN not set")
        return None
    credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {credentials}"


def extract_ticket_id(branch_name):
    """Extract Jira ticket ID from branch name."""
    match = re.search(r"([A-Z]+-\d+)", branch_name)
    if match:
        return match.group(1)
    return None


def get_jira_ticket(ticket_id):
    """Fetch ticket details from Jira API."""
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    auth = get_jira_auth()
    if not base_url or not auth:
        return None

    url = f"{base_url}/rest/api/3/issue/{ticket_id}"
    req = urllib.request.Request(url, headers={
        "Authorization": auth,
        "Accept": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {
                "key": data["key"],
                "summary": data["fields"]["summary"],
                "status": data["fields"]["status"]["name"],
                "type": data["fields"]["issuetype"]["name"],
                "priority": data["fields"].get("priority", {}).get("name", "None"),
                "description": extract_description(data["fields"].get("description")),
                "created": data["fields"]["created"],
                "url": f"{base_url}/browse/{ticket_id}"
            }
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch Jira ticket {ticket_id}: {e.code}")
        return None


def extract_description(desc):
    """Extract plain text from Jira's Atlassian Document Format."""
    if not desc:
        return "No description provided"
    if isinstance(desc, str):
        return desc
    texts = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(desc)
    return " ".join(texts) if texts else "No description provided"


def post_jira_comment(ticket_id, comment_text):
    """Post a comment to a Jira ticket."""
    base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
    auth = get_jira_auth()
    if not base_url or not auth:
        print("Cannot post to Jira — missing credentials")
        return False

    url = f"{base_url}/rest/api/3/issue/{ticket_id}/comment"
    body = json.dumps({
        "body": {
            "version": 1,
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": comment_text}]
            }]
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": auth,
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Comment posted to {ticket_id}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Failed to post comment to {ticket_id}: {e.code} {error_body}")
        return False


def do_extract():
    """Extract ticket ID from branch and write to GitHub outputs."""
    branch = os.environ.get("GITHUB_HEAD_REF", os.environ.get("GITHUB_REF_NAME", ""))
    print(f"Branch: {branch}")
    ticket_id = extract_ticket_id(branch)

    output_file = os.environ.get("GITHUB_OUTPUT")

    if not ticket_id:
        print("No ticket ID found in branch name")
        if output_file:
            with open(output_file, "a") as f:
                f.write("ticket_id=\n")
        return

    print(f"Extracted ticket: {ticket_id}")
    ticket = get_jira_ticket(ticket_id)

    if output_file and ticket:
        with open(output_file, "a") as f:
            f.write(f"ticket_id={ticket_id}\n")
            f.write(f"ticket_summary={ticket['summary']}\n")
            f.write(f"ticket_status={ticket['status']}\n")
            f.write(f"ticket_type={ticket['type']}\n")
            f.write(f"ticket_url={ticket['url']}\n")
            f.write(f"ticket_description={ticket['description']}\n")
        print(f"Ticket details written to GITHUB_OUTPUT")
    elif ticket:
        print(f"Summary: {ticket['summary']}")
        print(f"Status: {ticket['status']}")


def do_post_results():
    """Post pipeline results back to Jira ticket."""
    ticket_id = os.environ.get("TICKET_ID")
    if not ticket_id:
        print("No TICKET_ID set — skipping Jira update")
        return

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    branch = os.environ.get("GITHUB_HEAD_REF", os.environ.get("GITHUB_REF_NAME", "unknown"))

    lines = [
        f"Pipeline Results for {ticket_id}",
        f"Branch: {branch}",
        f"Run: {run_id}",
        "",
        "Stage Results:",
    ]

    for key, value in sorted(os.environ.items()):
        if key.startswith("STAGE_"):
            name = key.replace("STAGE_", "").replace("_", " ").title()
            icon = "PASS" if value == "success" else "SKIP" if value == "skipped" else "FAIL"
            lines.append(f"  [{icon}] {name}")

    if repo and run_id:
        lines.append("")
        lines.append(f"Details: https://github.com/{repo}/actions/runs/{run_id}")

    comment = "\n".join(lines)
    print(comment)
    post_jira_comment(ticket_id, comment)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "extract"
    if action == "extract":
        do_extract()
    elif action == "post-results":
        do_post_results()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)