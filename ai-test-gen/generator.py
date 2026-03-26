import os
import json
import anthropic
from models import TestGenerationResult, GeneratedTest, TestType
from prompts import SYSTEM_PROMPT, build_test_gen_prompt


def generate_tests(diff_text: str, changed_files: list, experience_id: str, pr_number: int) -> TestGenerationResult:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt = build_test_gen_prompt(diff_text, changed_files, experience_id)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )

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
