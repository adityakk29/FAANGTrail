"""Execute submitted Python locally with a bounded subprocess."""

import ast
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


def _instrument_assertions(test_source: str) -> str:
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return test_source

    class AssertionTransformer(ast.NodeTransformer):
        def visit_Assert(self, node: ast.Assert):
            return ast.Expr(
                value=ast.Call(
                    func=ast.Name(id="__faangtrail_check__", ctx=ast.Load()),
                    args=[node.test, node.msg if node.msg is not None else ast.Constant(value=None)],
                    keywords=[],
                )
            )

    instrumented = ast.fix_missing_locations(AssertionTransformer().visit(tree))
    return (
        "__faangtrail_passed = 0\n"
        "__faangtrail_total = 0\n"
        "def __faangtrail_check__(condition, message=None):\n"
        "    global __faangtrail_passed, __faangtrail_total\n"
        "    __faangtrail_total += 1\n"
        "    if not condition:\n"
        "        print(f'Test {__faangtrail_total} failed')\n"
        "        raise AssertionError(message or 'assertion failed')\n"
        "    __faangtrail_passed += 1\n"
        + ast.unparse(instrumented)
        + "\n"
        + "if __faangtrail_total:\n"
        "    print(f'All {__faangtrail_passed} tests passed.')\n"
    )


def run_python(source: str, timeout_seconds: int = 5, test_source: str | None = None) -> RunResult:
    program = source if test_source is None else f"{source}\n\n{_instrument_assertions(test_source)}"
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", program],
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