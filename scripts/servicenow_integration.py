"""
ServiceNow Integration for Experience ID Pipeline.
Extracts change request number from branch name, fetches context,
and posts pipeline results back as work notes.
Aligns with IT4IT Requirement to Deploy value stream.
"""

import os
import sys
import json
import re
import base64
import urllib.request
import urllib.error


def get_snow_auth():
    """Build basic auth header for ServiceNow API."""
    user = os.environ.get("SERVICENOW_USER")
    password = os.environ.get("SERVICENOW_PASSWORD")
    if not user or not password:
        print("SERVICENOW_USER or SERVICENOW_PASSWORD not set")
        return None
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
    return f"Basic {credentials}"


def get_base_url():
    """Build ServiceNow base URL from instance name."""
    instance = os.environ.get("SERVICENOW_INSTANCE", "")
    if not instance:
        print("SERVICENOW_INSTANCE not set")
        return None
    return f"https://{instance}.service-now.com"


def extract_ticket_id(branch_name):
    """Extract ServiceNow change request number from branch name."""
    # Match CHG followed by digits
    match = re.search(r"(CHG\d+)", branch_name, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def get_change_request(cr_number):
    """Fetch change request details from ServiceNow Table API."""
    base_url = get_base_url()
    auth = get_snow_auth()
    if not base_url or not auth:
        return None

    url = (
        f"{base_url}/api/now/table/change_request"
        f"?sysparm_query=number={cr_number}"
        f"&sysparm_fields=number,short_description,state,priority,sys_id,sys_created_on,assigned_to"
        f"&sysparm_limit=1"
    )

    req = urllib.request.Request(url, headers={
        "Authorization": auth,
        "Accept": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            if not data.get("result"):
                print(f"No change request found for {cr_number}")
                return None
            cr = data["result"][0]

            state_map = {
                "-5": "New",
                "-4": "Assess",
                "-3": "Authorize",
                "-2": "Scheduled",
                "-1": "Implement",
                "0": "Review",
                "3": "Closed",
                "4": "Cancelled"
            }

            return {
                "number": cr["number"],
                "summary": cr["short_description"],
                "state": state_map.get(str(cr.get("state", "")), str(cr.get("state", "Unknown"))),
                "priority": cr.get("priority", "Unknown"),
                "sys_id": cr["sys_id"],
                "created": cr.get("sys_created_on", ""),
                "url": f"{base_url}/nav_to.do?uri=change_request.do?sys_id={cr['sys_id']}"
            }
    except urllib.error.HTTPError as e:
        print(f"Failed to fetch change request {cr_number}: {e.code}")
        return None


def post_work_note(cr_number, sys_id, note_text):
    """Post a work note to a ServiceNow change request."""
    base_url = get_base_url()
    auth = get_snow_auth()
    if not base_url or not auth:
        print("Cannot post to ServiceNow — missing credentials")
        return False

    url = f"{base_url}/api/now/table/change_request/{sys_id}"
    body = json.dumps({
        "work_notes": note_text
    }).encode("utf-8")

    req = urllib.request.Request(url, data=body, method="PATCH", headers={
        "Authorization": auth,
        "Content-Type": "application/json",
        "Accept": "application/json"
    })

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Work note posted to {cr_number}")
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Failed to post work note to {cr_number}: {e.code} {error_body}")
        return False


def do_extract():
    """Extract change request number from branch, commit message, or PR title."""
    branch = os.environ.get("GITHUB_HEAD_REF", os.environ.get("GITHUB_REF_NAME", ""))
    print(f"Branch: {branch}")
    ticket_id = extract_ticket_id(branch)

    # If not found in branch (e.g., merge to main), check the commit message
    if not ticket_id:
        import subprocess
        try:
            commit_msg = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                capture_output=True, text=True
            ).stdout.strip()
            print(f"Commit message: {commit_msg}")
            ticket_id = extract_ticket_id(commit_msg)
        except Exception as e:
            print(f"Could not read commit message: {e}")

    output_file = os.environ.get("GITHUB_OUTPUT")

    if not ticket_id:
        print("No change request number found in branch name")
        if output_file:
            with open(output_file, "a") as f:
                f.write("ticket_id=\n")
        return

    print(f"Extracted change request: {ticket_id}")
    cr = get_change_request(ticket_id)

    if output_file and cr:
        with open(output_file, "a") as f:
            f.write(f"ticket_id={ticket_id}\n")
            f.write(f"ticket_summary={cr['summary']}\n")
            f.write(f"ticket_status={cr['state']}\n")
            f.write(f"ticket_url={cr['url']}\n")
            f.write(f"ticket_sys_id={cr['sys_id']}\n")
            f.write(f"ticket_description={cr['summary']}\n")
        print("Change request details written to GITHUB_OUTPUT")
    elif cr:
        print(f"Summary: {cr['summary']}")
        print(f"State: {cr['state']}")


def do_post_results():
    """Post pipeline results back to ServiceNow change request."""
    ticket_id = os.environ.get("TICKET_ID")
    sys_id = os.environ.get("TICKET_SYS_ID")
    if not ticket_id:
        print("No TICKET_ID set — skipping ServiceNow update")
        return

    # If we don't have sys_id, fetch it
    if not sys_id:
        cr = get_change_request(ticket_id)
        if cr:
            sys_id = cr["sys_id"]
        else:
            print(f"Could not find {ticket_id} in ServiceNow")
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

    note = "\n".join(lines)
    print(note)
    post_work_note(ticket_id, sys_id, note)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "extract"
    if action == "extract":
        do_extract()
    elif action == "post-results":
        do_post_results()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)