"""Execute submitted Python locally with a bounded subprocess."""

import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def run_python(source: str, timeout_seconds: int = 5) -> RunResult:
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", source],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        return RunResult(
            returncode=124,
            stdout=error.stdout or "",
            stderr="Execution timed out.\n",
            timed_out=True,
        )
    return RunResult(completed.returncode, completed.stdout, completed.stderr)