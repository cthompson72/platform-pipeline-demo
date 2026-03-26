import argparse
import json
import os
import sys


def evaluate_gate(e2e_path, perf_path, ai_gen_path, experience_id):
    report = {
        "experience_id": experience_id,
        "gates": {},
        "overall": "PASSED"
    }

    # E2E Results
    try:
        with open(e2e_path) as f:
            e2e = json.load(f)
        total = e2e.get("stats", {}).get("expected", 0)
        failed = e2e.get("stats", {}).get("unexpected", 0)
        report["gates"]["e2e"] = {
            "status": "PASSED" if failed == 0 else "FAILED",
            "total": total,
            "passed": total - failed,
            "failed": failed,
        }
    except FileNotFoundError:
        report["gates"]["e2e"] = {"status": "SKIPPED", "reason": "No E2E results found"}

    # Performance Results
    try:
        with open(perf_path) as f:
            perf = json.load(f)
        metrics = perf.get("metrics", {})
        p95 = metrics.get("http_req_duration", {}).get("values", {}).get("p(95)", 0)
        error_rate = metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0)

        perf_passed = p95 < 500 and error_rate < 0.05
        report["gates"]["performance"] = {
            "status": "PASSED" if perf_passed else "FAILED",
            "p95_ms": round(p95, 2),
            "error_rate": round(error_rate * 100, 2),
            "threshold_p95": 500,
            "threshold_error_rate": 5,
        }
    except FileNotFoundError:
        report["gates"]["performance"] = {"status": "SKIPPED", "reason": "No perf results found"}

    # AI Test Gen Results (informational, does not block)
    try:
        with open(ai_gen_path) as f:
            ai_gen = json.load(f)
        report["gates"]["ai_test_gen"] = {
            "status": "INFO",
            "suggestions": ai_gen.get("total_suggestions", 0),
            "high_priority": ai_gen.get("high_priority", 0),
        }
    except FileNotFoundError:
        report["gates"]["ai_test_gen"] = {"status": "SKIPPED", "reason": "No AI gen results found"}

    # Overall decision
    blocking_gates = ["e2e", "performance"]
    for gate_name in blocking_gates:
        if report["gates"].get(gate_name, {}).get("status") == "FAILED":
            report["overall"] = "FAILED"
            break

    # Write report
    os.makedirs("quality-reports", exist_ok=True)
    with open(f"quality-reports/{experience_id}-quality-report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Set output for GitHub Actions
    with open(os.environ.get("GITHUB_OUTPUT", "/dev/null"), "a") as f:
        f.write(f"gate_status={report['overall']}\n")

    print(json.dumps(report, indent=2))
    return report["overall"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experience-id", required=True)
    parser.add_argument("--e2e-results", required=True)
    parser.add_argument("--perf-results", required=True)
    parser.add_argument("--ai-gen-results", required=True)
    args = parser.parse_args()

    status = evaluate_gate(args.e2e_results, args.perf_results, args.ai_gen_results, args.experience_id)
    if status == "FAILED":
        sys.exit(1)
