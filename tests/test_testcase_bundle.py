import hashlib
import json
import tarfile
from pathlib import Path

from faangtrail import roadmap, testcase_bundle


def _write_release(root: Path) -> Path:
    problem_dir = root / "two-sum"
    problem_dir.mkdir()
    (problem_dir / "testcases.json").write_text(
        json.dumps(
            {
                "problem_id": "two-sum",
                "pattern": "function",
                "function": "solve",
                "cases": [{"input": [[2, 7], 9], "expected": [0, 1]}],
            }
        ),
        encoding="utf-8",
    )
    archive = root / "cases.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(problem_dir / "testcases.json", arcname="two-sum/testcases.json")
    manifest = {
        "manifest_version": 1,
        "bundle_format_version": 1,
        "min_app_version": "0.1.0",
        "filename": archive.name,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "problem_count": 1,
        "problems": ["two-sum"],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


def test_bundle_download_installs_and_converts_function_cases(tmp_path, monkeypatch) -> None:
    manifest_path = _write_release(tmp_path)
    bundle_dir = tmp_path / "installed"
    monkeypatch.setattr(testcase_bundle, "BUNDLE_DIR", bundle_dir)
    monkeypatch.setattr(testcase_bundle, "BUNDLE_META", bundle_dir / ".bundle.json")

    metadata = testcase_bundle.fetch_testcase_bundle(manifest_path.as_uri())

    assert metadata["problem_count"] == 1
    assert (bundle_dir / "two-sum" / "testcases.json").exists()
    tests = roadmap._load_downloaded_tests("two-sum")
    assert "assert solve([2, 7], 9) == [0, 1]" in tests


def test_bundle_rejects_unlisted_archive_member(tmp_path) -> None:
    manifest_path = _write_release(tmp_path)
    rogue = tmp_path / "rogue"
    rogue.mkdir()
    (rogue / "testcases.json").write_text("{}", encoding="utf-8")
    archive = tmp_path / "cases.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        bundle.add(tmp_path / "two-sum" / "testcases.json", arcname="two-sum/testcases.json")
        bundle.add(rogue / "testcases.json", arcname="rogue/testcases.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["filename"] = archive.name
    manifest["sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    try:
        testcase_bundle.fetch_testcase_bundle(manifest_path.as_uri())
    except ValueError as error:
        assert "Unexpected testcase archive member" in str(error)
    else:
        raise AssertionError("unsafe archive was accepted")
