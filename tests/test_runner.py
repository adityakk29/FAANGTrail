from faangtrail.runner import run_python


def test_run_python_captures_output() -> None:
    result = run_python("print(2 + 2)")

    assert result.returncode == 0
    assert result.stdout == "4\n"
    assert result.stderr == ""


def test_run_python_reports_timeout() -> None:
    result = run_python("while True: pass", timeout_seconds=1)

    assert result.timed_out is True
    assert result.returncode == 124


def test_run_python_executes_local_tests() -> None:
    result = run_python("def solve(value):\n    return value * 2", test_source="assert solve(3) == 6")

    assert result.returncode == 0
    assert "All 1 tests passed." in result.stdout


def test_run_python_stops_on_first_failed_assertion() -> None:
    result = run_python("def solve(value):\n    return value + 1", test_source="assert solve(1) == 2\nassert solve(2) == 5")

    assert result.returncode != 0
    assert "Test 2 failed" in result.stdout