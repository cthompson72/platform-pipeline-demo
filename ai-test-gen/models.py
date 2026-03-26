from dataclasses import dataclass, field
from typing import List
from enum import Enum


class TestType(Enum):
    E2E_API = "e2e_api"
    E2E_UI = "e2e_ui"
    PERFORMANCE = "performance"
    EDGE_CASE = "edge_case"


@dataclass
class GeneratedTest:
    test_type: TestType
    name: str
    description: str
    code: str
    priority: str
    rationale: str
    sast_detectable: bool


@dataclass
class TestGenerationResult:
    experience_id: str
    pr_number: int
    changed_files: List[str]
    suggested_tests: List[GeneratedTest] = field(default_factory=list)
    summary: str = ""
    generation_model: str = "claude-sonnet-4-20250514"
