import argparse
import json
import os
import sys
from github import Github
from generator import generate_tests
from formatter import format_pr_comment


def main():
    parser = argparse.ArgumentParser(description="AI-augmented test generation")
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--experience-id", type=str, required=True)
    parser.add_argument("--repo", type=str, default="cthompson72/platform-pipeline-demo")
    args = parser.parse_args()

    gh = Github(os.environ["GITHUB_TOKEN"])
    repo = gh.get_repo(args.repo)
    pr = repo.get_pull(args.pr_number)

    files = pr.get_files()
    changed_files = [f.filename for f in files]
    diff_text = "\n".join(f.patch or "" for f in files if f.patch)

    if not diff_text.strip():
        print("No code changes to analyze. Skipping test generation.")
        sys.exit(0)

    result = generate_tests(diff_text, changed_files, args.experience_id, args.pr_number)

    comment_body = format_pr_comment(result)
    pr.create_issue_comment(comment_body)

    print(f"Posted {len(result.suggested_tests)} test suggestions to PR #{args.pr_number}")

    os.makedirs("ai-test-gen/results", exist_ok=True)
    with open("ai-test-gen/results/test-gen-results.json", "w") as f:
        json.dump({
            "experience_id": result.experience_id,
            "pr_number": result.pr_number,
            "total_suggestions": len(result.suggested_tests),
            "high_priority": sum(1 for t in result.suggested_tests if t.priority == "high"),
            "medium_priority": sum(1 for t in result.suggested_tests if t.priority == "medium"),
            "low_priority": sum(1 for t in result.suggested_tests if t.priority == "low"),
        }, f, indent=2)


if __name__ == "__main__":
    main()
