"""Roadmap metadata loading and lookup."""

import json
import re
from dataclasses import dataclass
from importlib.resources import files

from .testcase_bundle import testcase_path


@dataclass(frozen=True)
class Challenge:
    id: str
    title: str
    topic: str
    difficulty: str
    prompt: str
    description: str
    examples: str
    constraints: str
    starter: str
    tests: str


def load_challenges() -> list[Challenge]:
    package_files = files("faangtrail")
    payload = package_files.joinpath("data/roadmap.json").read_text(encoding="utf-8")
    challenges = [Challenge(**item) for item in json.loads(payload)]
    known_ids = {challenge.id for challenge in challenges}

    catalog_dir = package_files.joinpath("data", "problems")
    for category_file in sorted(catalog_dir.iterdir(), key=lambda path: path.name):
        if category_file.suffix != ".json":
            continue
        topic = category_file.stem.replace("-", " ").title()
        for problem in json.loads(category_file.read_text(encoding="utf-8")):
            challenge_id = problem["id"]
            if challenge_id in known_ids:
                continue
            title = problem["name"]
            downloaded_tests = _load_downloaded_tests(challenge_id)
            challenges.append(
                Challenge(
                    id=challenge_id,
                    title=title,
                    topic=topic,
                    difficulty=problem["difficulty"].lower(),
                    prompt=f"Solve the {title} problem.",
                    description=problem["description"],
                    examples=_format_examples(problem.get("examples", [])),
                    constraints=problem.get("constraints", ""),
                    starter=problem.get("python_template", f"# {title}\n\n"),
                    tests=downloaded_tests or (
                        "print('Tests for this imported problem are not bundled yet. "
                        "Use the examples to validate your solution.')"
                    ),
                )
            )
            known_ids.add(challenge_id)

    return challenges


def _load_downloaded_tests(problem_id: str) -> str | None:
    path = testcase_path(problem_id)
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    test_source = payload.get("test_source") if isinstance(payload, dict) else None
    if isinstance(test_source, str) and test_source.strip():
        return test_source
    if not isinstance(payload, dict) or payload.get("pattern") != "function":
        return None
    function_name = payload.get("function")
    cases = payload.get("cases")
    if not isinstance(function_name, str) or not re.fullmatch(r"[A-Za-z_]\w*", function_name) or not isinstance(cases, list):
        return None
    assertions = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), list) or "expected" not in case:
            return None
        arguments = ", ".join(repr(value) for value in case["input"])
        assertions.append(f"assert {function_name}({arguments}) == {case['expected']!r}")
    return "\n".join(assertions) + "\nprint('All tests passed.')" if assertions else None


def _format_examples(examples: list[dict]) -> str:
    formatted = []
    for index, example in enumerate(examples, start=1):
        formatted.append(
            f"Example {index}\nInput: {example.get('input', '')}\n"
            f"Output: {example.get('output', '')}"
        )
    return "\n\n".join(formatted)


def _problem_id(title: str) -> str:
    """Convert a roadmap title into the stable ID used by the app."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def find_challenge(challenge_id: str) -> Challenge:
    for challenge in load_challenges():
        if challenge.id == challenge_id:
            return challenge
    raise LookupError(f"Unknown challenge: {challenge_id}")