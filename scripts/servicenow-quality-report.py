import argparse
import json
import os
import requests


def post_quality_report(experience_id, gate_result):
    instance = os.environ.get("SERVICENOW_INSTANCE", "")
    user = os.environ.get("SERVICENOW_USER", "")
    password = os.environ.get("SERVICENOW_PASSWORD", "")

    if not all([instance, user, password, experience_id]):
        print("Missing ServiceNow credentials or experience ID. Skipping.")
        return

    # Load quality report
    report_path = f"quality-reports/{experience_id}-quality-report.json"
    try:
        with open(report_path) as f:
            report = json.load(f)
    except FileNotFoundError:
        print(f"Quality report not found at {report_path}")
        return

    # Format work note
    gates = report.get("gates", {})
    lines = [
        f"=== QA Pipeline Quality Gate: {gate_result} ===",
        f"Experience ID: {experience_id}",
        "",
    ]

    e2e = gates.get("e2e", {})
    if e2e.get("status") != "SKIPPED":
        lines.append(f"E2E Tests: {e2e.get('status')} ({e2e.get('passed', 0)}/{e2e.get('total', 0)} passed)")
    else:
        lines.append(f"E2E Tests: SKIPPED")

    perf = gates.get("performance", {})
    if perf.get("status") != "SKIPPED":
        lines.append(f"Performance: {perf.get('status')} (p95={perf.get('p95_ms', 'N/A')}ms, errors={perf.get('error_rate', 'N/A')}%)")
    else:
        lines.append(f"Performance: SKIPPED")

    ai = gates.get("ai_test_gen", {})
    if ai.get("status") != "SKIPPED":
        lines.append(f"AI Test Suggestions: {ai.get('suggestions', 0)} ({ai.get('high_priority', 0)} high priority)")

    lines.append(f"\nOverall: {gate_result}")

    work_note = "\n".join(lines)

    # Find the change request by number
    url = f"https://{instance}.service-now.com/api/now/table/change_request"
    params = {"sysparm_query": f"short_descriptionLIKE{experience_id}", "sysparm_limit": 1}
    resp = requests.get(url, auth=(user, password), params=params,
                        headers={"Accept": "application/json"})

    if resp.status_code != 200 or not resp.json().get("result"):
        print(f"Could not find ServiceNow CR {experience_id}: {resp.status_code}")
        return

    sys_id = resp.json()["result"][0]["sys_id"]

    # Post work note
    update_url = f"https://{instance}.service-now.com/api/now/table/change_request/{sys_id}"
    update_data = {"work_notes": work_note}
    resp = requests.patch(update_url, auth=(user, password), json=update_data,
                          headers={"Content-Type": "application/json", "Accept": "application/json"})

    if resp.status_code == 200:
        print(f"Posted QA quality report to {experience_id}")
    else:
        print(f"Failed to post to ServiceNow: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experience-id", required=True)
    parser.add_argument("--gate-result", required=True)
    args = parser.parse_args()
    post_quality_report(args.experience_id, args.gate_result)
