"""Roadmap metadata loading and lookup."""

import json
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class Challenge:
    id: str
    title: str
    topic: str
    difficulty: str
    prompt: str
    starter: str
    tests: str


def load_challenges() -> list[Challenge]:
    payload = files("faangtrail").joinpath("data/roadmap.json").read_text()
    return [Challenge(**item) for item in json.loads(payload)]


def find_challenge(challenge_id: str) -> Challenge:
    for challenge in load_challenges():
        if challenge.id == challenge_id:
            return challenge
    raise LookupError(f"Unknown challenge: {challenge_id}")