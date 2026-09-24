"""Execute submitted Python locally with a bounded subprocess."""

import ast
import subprocess
import sys
import threading
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


PROGRESS_PREFIX = "__FAANGTRAIL_PROGRESS__"


def _instrument_assertions(test_source: str, emit_progress: bool = False) -> str:
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return test_source

    total_assertions = sum(isinstance(node, ast.Assert) for node in ast.walk(tree))

    class AssertionTransformer(ast.NodeTransformer):
        def visit_Assert(self, node: ast.Assert):
            self.assertion_number += 1
            return ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="__faangtrail_check__", ctx=ast.Load()),
                    args=[
                        node.test,
                        ast.Constant(value=self.assertion_number),
                        node.msg if node.msg is not None else ast.Constant(value=None),
                    ],
                    keywords=[],
                )
            )

        def __init__(self) -> None:
            super().__init__()
            self.assertion_number = 0

        def generic_visit(self, node):
            if isinstance(node, ast.Assert):
                self.assertion_number += 1
            return super().generic_visit(node)

    instrumented = ast.fix_missing_locations(AssertionTransformer().visit(tree))
    progress_interval = max(1, total_assertions // 100)
    progress_line = (
        f"    if number == 1 or number % {progress_interval} == 0 or number == {total_assertions}:\n"
        f"        print('{PROGRESS_PREFIX} ' + str(number) + ' ' + str({total_assertions}), flush=True)\n"
        if emit_progress
        else ""
    )
    return (
        "__faangtrail_passed = 0\n"
        "__faangtrail_total = 0\n"
        f"def __faangtrail_check__(condition, number, message=None):\n"
        "    global __faangtrail_passed, __faangtrail_total\n"
        + progress_line
        + "    __faangtrail_total += 1\n"
        "    if not condition:\n"
        "        print(f'Test {__faangtrail_total} failed')\n"
        "        raise AssertionError(message or 'assertion failed')\n"
        "    __faangtrail_passed += 1\n"
        + ast.unparse(instrumented)
        + "\n"
        + "if __faangtrail_total:\n"
        "    print(f'All {__faangtrail_passed} tests passed.')\n"
    )


def run_python(
    source: str,
    timeout_seconds: int = 5,
    test_source: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> RunResult:
    program = source if test_source is None else f"{source}\n\n{_instrument_assertions(test_source, emit_progress=progress_callback is not None)}"
    process = subprocess.Popen(
        [sys.executable, "-I", "-"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def read_stdout() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            if line.startswith(PROGRESS_PREFIX + " "):
                try:
                    _, current, total = line.strip().split()
                    if progress_callback is not None:
                        progress_callback(int(current), int(total))
                except ValueError:
                    stdout_lines.append(line)
            else:
                stdout_lines.append(line)

    def read_stderr() -> None:
        assert process.stderr is not None
        stderr_lines.extend(process.stderr)

    stdout_thread = threading.Thread(target=read_stdout)
    stderr_thread = threading.Thread(target=read_stderr)
    stdout_thread.start()
    stderr_thread.start()
    try:
        assert process.stdin is not None
        process.stdin.write(program)
        process.stdin.close()
        process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
        return RunResult(
            returncode=124,
            stdout="".join(stdout_lines),
            stderr="Execution timed out.\n",
            timed_out=True,
        )
    stdout_thread.join()
    stderr_thread.join()
    return RunResult(process.returncode, "".join(stdout_lines), "".join(stderr_lines))