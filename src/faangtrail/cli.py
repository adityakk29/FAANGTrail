"""Command-line interface for the first FAANGTrail milestone."""

import argparse
from pathlib import Path

from .roadmap import find_challenge, load_challenges
from .runner import run_python
from .testcase_bundle import fetch_testcase_bundle, installed_metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="faangtrail")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List available roadmap challenges")
    commands.add_parser("fetch-testcases", help="Download the latest local testcase bundle")

    run_parser = commands.add_parser("run", help="Run Python code for a challenge")
    run_parser.add_argument("challenge_id")
    source = run_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--code", help="Python source code to execute")
    source.add_argument("--file", type=Path, help="Path to a Python solution file")
    run_parser.add_argument("--timeout", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "fetch-testcases":
        try:
            metadata = fetch_testcase_bundle()
        except (OSError, ValueError) as error:
            print(f"Unable to download testcases: {error}")
            return 2
        print(f"Installed {metadata['problem_count']} testcase sets.")
        return 0
    if args.command == "list":
        for challenge in load_challenges():
            print(f"{challenge.id:22} {challenge.difficulty:8} {challenge.topic}")
        return 0

    try:
        challenge = find_challenge(args.challenge_id)
    except LookupError as error:
        print(error)
        return 2

    source = args.code if args.code is not None else args.file.read_text()
    print(f"{challenge.title}: {challenge.prompt}")
    result = run_python(source, args.timeout, test_source=challenge.tests)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())