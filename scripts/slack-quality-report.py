import argparse
import json
import os
import requests


def post_slack_report(experience_id, gate_result):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("No SLACK_WEBHOOK_URL set. Skipping.")
        return

    # Load quality report
    report_path = f"quality-reports/{experience_id}-quality-report.json"
    try:
        with open(report_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"Quality report not found at {report_path}")
        return

    gates = report.get("gates", {})
    color = "#36a64f" if gate_result == "PASSED" else "#dc3545"
    status_icon = "PASSED" if gate_result == "PASSED" else "FAILED"

    fields = []

    e2e = gates.get("e2e", {})
    if e2e.get("status") != "SKIPPED":
        fields.append({
            "title": "E2E Tests",
            "value": f"{e2e.get('status')} ({e2e.get('passed', 0)}/{e2e.get('total', 0)} passed)",
            "short": True
        })

    perf = gates.get("performance", {})
    if perf.get("status") != "SKIPPED":
        fields.append({
            "title": "Performance",
            "value": f"{perf.get('status')} (p95={perf.get('p95_ms', 'N/A')}ms)",
            "short": True
        })

    ai = gates.get("ai_test_gen", {})
    if ai.get("status") != "SKIPPED":
        fields.append({
            "title": "AI Test Suggestions",
            "value": f"{ai.get('suggestions', 0)} suggestions ({ai.get('high_priority', 0)} high)",
            "short": True
        })

    github_run_url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"

    payload = {
        "attachments": [{
            "color": color,
            "title": f"QA Quality Gate: {status_icon}",
            "text": f"Experience ID: `{experience_id}`",
            "fields": fields,
            "actions": [{
                "type": "button",
                "text": "View Pipeline Run",
                "url": github_run_url
            }],
            "footer": "Platform QA Pipeline"
        }]
    }

    resp = requests.post(webhook_url, json=payload)
    if resp.status_code == 200:
        print(f"Posted QA quality report to Slack for {experience_id}")
    else:
        print(f"Failed to post to Slack: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experience-id", required=True)
    parser.add_argument("--gate-result", required=True)
    args = parser.parse_args()
    post_slack_report(args.experience_id, args.gate_result)
