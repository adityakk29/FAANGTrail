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