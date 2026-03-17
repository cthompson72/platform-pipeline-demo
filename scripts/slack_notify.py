"""
Slack notifications for the CI/CD pipeline.
Posts pipeline results with Experience ID context.
"""

import os
import sys
import json
import urllib.request
import urllib.error


def post_slack_message(blocks):
    """Post a message to Slack via webhook."""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set — skipping notification")
        return False

    body = json.dumps({"blocks": blocks}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=body, headers={
        "Content-Type": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            print("Slack notification sent")
            return True
    except urllib.error.HTTPError as e:
        print(f"Slack error: {e.code} {e.read().decode()}")
        return False


def build_pipeline_message():
    """Build a Slack message with pipeline results."""
    ticket_id = os.environ.get("TICKET_ID", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    branch = os.environ.get("GITHUB_HEAD_REF", os.environ.get("GITHUB_REF_NAME", "unknown"))
    event = os.environ.get("GITHUB_EVENT_NAME", "push")
    jira_base = os.environ.get("JIRA_BASE_URL", "")

    # Collect stage results
    stages = {}
    all_passed = True
    for key, value in sorted(os.environ.items()):
        if key.startswith("STAGE_"):
            name = key.replace("STAGE_", "").replace("_", " ").title()
            stages[name] = value
            if value not in ("success", "skipped"):
                all_passed = False

    # Header
    if all_passed:
        header = ":white_check_mark: Pipeline Passed"
        color_emoji = ":large_green_circle:"
    else:
        header = ":x: Pipeline Failed"
        color_emoji = ":red_circle:"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header}
        }
    ]

    # Experience ID and branch info
    context_parts = [f"*Branch:* `{branch}`"]
    snow_instance = os.environ.get("SERVICENOW_INSTANCE", "")
    if ticket_id and snow_instance:
        context_parts.insert(0, f"*Experience ID:* {ticket_id} (ServiceNow)")
    if event == "pull_request":
        context_parts.append(f"*Trigger:* Pull Request")
    else:
        context_parts.append(f"*Trigger:* Push to {branch}")

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "  |  ".join(context_parts)}
    })

    # Stage results
    stage_lines = []
    for name, result in stages.items():
        if result == "success":
            icon = ":white_check_mark:"
        elif result == "skipped":
            icon = ":fast_forward:"
        else:
            icon = ":x:"
        stage_lines.append(f"{icon}  {name}")

    blocks.append({
        "type": "section",
        "text": {"type": "mrkdwn", "text": "\n".join(stage_lines)}
    })

    # Link to run
    if repo and run_id:
        blocks.append({
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"<https://github.com/{repo}/actions/runs/{run_id}|View full pipeline run>"
            }]
        })

    return blocks


if __name__ == "__main__":
    blocks = build_pipeline_message()
    post_slack_message(blocks)