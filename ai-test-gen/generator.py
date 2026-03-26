import os
import json
import time
import anthropic
from models import TestGenerationResult, GeneratedTest, TestType
from prompts import SYSTEM_PROMPT, build_test_gen_prompt


def generate_tests(diff_text: str, changed_files: list, experience_id: str, pr_number: int) -> TestGenerationResult:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Truncate large diffs to stay within rate limits
    MAX_DIFF_CHARS = 8000
    if len(diff_text) > MAX_DIFF_CHARS:
        print(f"Diff is {len(diff_text)} chars — truncating to {MAX_DIFF_CHARS}")
        diff_text = diff_text[:MAX_DIFF_CHARS] + "\n... (diff truncated for API limits)"

    prompt = build_test_gen_prompt(diff_text, changed_files, experience_id)

    # Retry with backoff for rate limits
    response = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            break
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"Rate limited (attempt {attempt + 1}/3). Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

    if response is None:
        raise RuntimeError("Failed to get response from Claude API after 3 attempts")

    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    tests_data = json.loads(raw_text)

    result = TestGenerationResult(
        experience_id=experience_id,
        pr_number=pr_number,
        changed_files=changed_files,
    )

    for t in tests_data:
        result.suggested_tests.append(GeneratedTest(
            test_type=TestType(t["test_type"]),
            name=t["name"],
            description=t["description"],
            code=t["code"],
            priority=t["priority"],
            rationale=t["rationale"],
            sast_detectable=t.get("sast_detectable", False),
        ))

    high = sum(1 for t in result.suggested_tests if t.priority == "high")
    med = sum(1 for t in result.suggested_tests if t.priority == "medium")
    low = sum(1 for t in result.suggested_tests if t.priority == "low")
    result.summary = f"Generated {len(result.suggested_tests)} test suggestions ({high} high, {med} medium, {low} low priority)"

    return result