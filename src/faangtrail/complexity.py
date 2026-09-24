"""Optional OpenAI-backed time and space complexity analysis."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SERVICE_NAME = "faangtrail"
KEY_NAME = "openai-api-key"
DEFAULT_MODEL = "gpt-4o-mini"
API_URL = "https://api.openai.com/v1/responses"


class ComplexityError(RuntimeError):
    """Raised when complexity analysis cannot be completed."""


@dataclass(frozen=True)
class ComplexityResult:
    time: str
    space: str


def _keyring():
    try:
        import keyring
    except ImportError:
        return None
    return keyring


def get_api_key() -> str | None:
    environment_key = os.environ.get("OPENAI_API_KEY")
    if environment_key:
        return environment_key.strip() or None
    keyring = _keyring()
    if keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, KEY_NAME)
    except Exception:
        return None


def save_api_key(api_key: str) -> None:
    normalized = api_key.strip()
    if not normalized:
        raise ValueError("Enter an OpenAI API key.")
    keyring = _keyring()
    if keyring is None:
        raise ComplexityError("Install the AI optional dependency to securely store the key: pip install -e \".[ai]\"")
    try:
        keyring.set_password(SERVICE_NAME, KEY_NAME, normalized)
    except Exception as error:
        raise ComplexityError(f"Unable to save the API key in the system credential store: {error}") from error


def delete_api_key() -> None:
    keyring = _keyring()
    if keyring is None:
        return
    try:
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
    except Exception:
        pass


def analyze_complexity(source: str, problem: str, api_key: str | None = None) -> ComplexityResult:
    key = (api_key or get_api_key() or "").strip()
    if not key:
        raise ComplexityError("Configure an OpenAI API key before analyzing complexity.")
    if not source.strip():
        raise ComplexityError("Add a solution before analyzing complexity.")

    prompt = (
        "Analyze the submitted Python solution for the stated programming problem. "
        "Return only valid JSON with exactly these two string fields: "
        "time_complexity and space_complexity. "
        "Values must contain only Big-O notation, such as O(n), O(log n), or O(n^2). "
        "Do not include markdown, explanations, confidence, caveats, or any other fields.\n\n"
        f"Problem:\n{problem}\n\nSolution:\n{source}"
    )
    payload = {
        "model": DEFAULT_MODEL,
        "input": prompt,
        "temperature": 0,
        "max_output_tokens": 40,
    }
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ComplexityError(f"OpenAI request failed ({error.code}): {detail[:240]}") from error
    except URLError as error:
        raise ComplexityError(f"Unable to reach OpenAI: {error.reason}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise ComplexityError(f"Unable to read the OpenAI response: {error}") from error

    try:
        text = body["output"][0]["content"][0]["text"]
        result = json.loads(text)
        time_complexity = result["time_complexity"]
        space_complexity = result["space_complexity"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise ComplexityError("OpenAI returned an invalid complexity result.") from error
    if not isinstance(time_complexity, str) or not isinstance(space_complexity, str):
        raise ComplexityError("OpenAI returned invalid complexity values.")
    return ComplexityResult(time=time_complexity.strip(), space=space_complexity.strip())
