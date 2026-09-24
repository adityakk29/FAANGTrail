"""Roadmap metadata loading and lookup."""

import json
import re
from dataclasses import dataclass
from importlib.resources import files

from .testcase_bundle import testcase_path


_IDENTIFIER_PATTERN = r"[A-Za-z_]\w*"
_PASS_MESSAGE = "\nprint('All tests passed.')"


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
    challenges = []
    for item in json.loads(payload):
        downloaded_tests = _load_downloaded_tests(item["id"])
        challenges.append(Challenge(**{**item, "tests": downloaded_tests or item["tests"]}))
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
            downloaded_tests = _load_downloaded_tests(
                challenge_id,
                _python_symbol_name(problem.get("python_template", "")),
            )
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


def _load_downloaded_tests(problem_id: str, python_symbol: str | None = None) -> str | None:
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
    if not isinstance(payload, dict):
        return None
    if payload.get("pattern") == "design":
        return _build_design_tests(payload)
    if payload.get("pattern") == "inplace":
        return _build_inplace_tests(payload, python_symbol)
    if payload.get("pattern") == "in_place_linked_list":
        return _build_linked_list_tests(payload)
    if payload.get("pattern") in {"alien_to_string", "tickets_to_strings", "ladder_to_int"}:
        return _build_custom_function_tests(payload)
    if payload.get("pattern") != "function":
        return None
    function_name = payload.get("function")
    cases = payload.get("cases")
    if not isinstance(function_name, str) or not re.fullmatch(_IDENTIFIER_PATTERN, function_name) or not isinstance(cases, list):
        return None
    assertions = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), list) or "expected" not in case:
            return None
        arguments = ", ".join(repr(value) for value in case["input"])
        assertions.append(f"assert {function_name}({arguments}) == {case['expected']!r}")
    return "\n".join(assertions) + _PASS_MESSAGE if assertions else None


def _build_design_tests(payload: dict) -> str | None:
    class_name = payload.get("function")
    cases = payload.get("cases")
    if not isinstance(class_name, str) or not re.fullmatch(_IDENTIFIER_PATTERN, class_name) or not isinstance(cases, list):
        return None

    assertions = []
    for case in cases:
        if not isinstance(case, dict):
            return None
        operations = case.get("operations")
        operation_inputs = case.get("op_inputs")
        expected = case.get("expected")
        constructor_args = case.get("input")
        if (
            not isinstance(operations, list)
            or not isinstance(operation_inputs, list)
            or not isinstance(expected, list)
            or len(operations) != len(operation_inputs)
            or len(operations) != len(expected)
            or not isinstance(constructor_args, list)
        ):
            return None
        lines = [f"__faangtrail_object = {class_name}(*{constructor_args!r})", "__faangtrail_results = []"]
        for operation, arguments in zip(operations, operation_inputs):
            if not isinstance(operation, str) or not isinstance(arguments, list):
                return None
            if operation == class_name:
                lines.append("__faangtrail_results.append(None)")
            else:
                lines.append(
                    f"__faangtrail_results.append(getattr(__faangtrail_object, {operation!r})(*{arguments!r}))"
                )
        lines.append(f"assert __faangtrail_results == {expected!r}")
        assertions.append("\n".join(lines))
    return "\n".join(assertions) + _PASS_MESSAGE if assertions else None


def _build_inplace_tests(payload: dict, python_symbol: str | None) -> str | None:
    cases = payload.get("cases")
    if not python_symbol or not isinstance(cases, list):
        return None

    assertions = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), list) or "expected" not in case:
            return None
        arguments = case["input"]
        lines = [f"__faangtrail_args = {arguments!r}"]
        lines.append(f"__faangtrail_result = {python_symbol}(*__faangtrail_args)")
        lines.append(
            f"assert (__faangtrail_result if __faangtrail_result is not None else __faangtrail_args[0]) == {case['expected']!r}"
        )
        assertions.append("\n".join(lines))
    return "\n".join(assertions) + _PASS_MESSAGE if assertions else None


def _build_custom_function_tests(payload: dict) -> str | None:
    function_name = payload.get("function")
    cases = payload.get("cases")
    if not isinstance(function_name, str) or not re.fullmatch(_IDENTIFIER_PATTERN, function_name) or not isinstance(cases, list):
        return None
    assertions = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), list) or "expected" not in case:
            return None
        assertions.append(f"assert {function_name}(*{case['input']!r}) == {case['expected']!r}")
    return "\n".join(assertions) + _PASS_MESSAGE if assertions else None


def _build_linked_list_tests(payload: dict) -> str | None:
    function_name = payload.get("function") or "reorderList"
    cases = payload.get("cases")
    if not isinstance(function_name, str) or not re.fullmatch(_IDENTIFIER_PATTERN, function_name) or not isinstance(cases, list):
        return None
    assertions = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("input"), list) or "expected" not in case:
            return None
        values = case["input"][0] if len(case["input"]) == 1 else None
        expected = case["expected"]
        if not isinstance(values, list) or not isinstance(expected, list):
            return None
        lines = ["__faangtrail_head = None"]
        for value in reversed(values):
            lines.append(f"__faangtrail_head = ListNode({value!r}, __faangtrail_head)")
        lines.append(f"{function_name}(__faangtrail_head)")
        lines.append("__faangtrail_values = []")
        lines.append("__faangtrail_node = __faangtrail_head")
        lines.append(f"for _ in range({len(expected)}):")
        lines.append("    __faangtrail_values.append(__faangtrail_node.val)")
        lines.append("    __faangtrail_node = __faangtrail_node.next")
        lines.append("assert __faangtrail_node is None")
        lines.append(f"assert __faangtrail_values == {expected!r}")
        assertions.append("\n".join(lines))
    return "\n".join(assertions) + _PASS_MESSAGE if assertions else None


def _python_symbol_name(template: str) -> str | None:
    match = re.search(r"^def\s+([A-Za-z_]\w*)\s*\(", template, flags=re.MULTILINE)
    return match.group(1) if match else None


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