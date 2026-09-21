"""Download and resolve optional local testcase bundles."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import urlopen

from . import __version__

BUNDLE_DIR = Path.home() / ".faangtrail" / "downloaded-testcases"
BUNDLE_META = BUNDLE_DIR / ".bundle.json"
MANIFEST_ENV = "FAANGTRAIL_TESTCASE_MANIFEST_URL"
DEFAULT_MANIFEST_URL = "https://github.com/grindxhq/dsa-catalog/releases/latest/download/manifest.json"
SUPPORTED_MANIFEST_VERSION = 1
SUPPORTED_BUNDLE_VERSION = 1


def _safe_id(value: object) -> bool:
    return isinstance(value, str) and bool(value) and ".." not in value and "/" not in value and "\\" not in value


def resolve_manifest_url(manifest_url: str | None = None) -> str:
    url = (manifest_url or os.environ.get(MANIFEST_ENV, "") or DEFAULT_MANIFEST_URL).strip()
    if not url:
        raise ValueError(f"No testcase manifest URL configured. Pass a URL or set {MANIFEST_ENV}.")
    return url


def testcase_path(problem_id: str) -> Path | None:
    if not _safe_id(problem_id):
        return None
    user_path = Path.home() / ".faangtrail" / "problems" / problem_id / "testcases.json"
    downloaded_path = BUNDLE_DIR / problem_id / "testcases.json"
    bundled_path = files("faangtrail").joinpath("data", "problems", problem_id, "testcases.json")
    for path in (user_path, downloaded_path, Path(str(bundled_path))):
        if path.exists():
            return path
    return None


def installed_metadata() -> dict | None:
    try:
        data = json.loads(BUNDLE_META.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version)[:3])


def _version_at_least(current: str, minimum: str) -> bool:
    current_key = _version_key(current)
    minimum_key = _version_key(minimum)
    width = max(len(current_key), len(minimum_key))
    return (current_key + (0,) * (width - len(current_key))) >= (minimum_key + (0,) * (width - len(minimum_key)))


def _download(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def _validate_manifest(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Testcase manifest must be a JSON object")
    if value.get("manifest_version") != SUPPORTED_MANIFEST_VERSION:
        raise ValueError("Unsupported testcase manifest version")
    if value.get("bundle_format_version") != SUPPORTED_BUNDLE_VERSION:
        raise ValueError("Unsupported testcase bundle version")
    minimum = value.get("min_app_version", "")
    if not isinstance(minimum, str) or not _version_at_least(__version__, minimum):
        raise ValueError(f"Installed FAANGTrail {__version__} is older than required version {minimum}")
    filename = value.get("filename")
    checksum = value.get("sha256")
    problem_ids = value.get("problems")
    if not isinstance(filename, str) or not filename.strip() or not isinstance(checksum, str) or not checksum.strip():
        raise ValueError("Manifest is missing archive filename or sha256")
    if not isinstance(problem_ids, list) or not problem_ids or any(not _safe_id(item) for item in problem_ids):
        raise ValueError("Manifest contains invalid problem IDs")
    if len(set(problem_ids)) != len(problem_ids) or value.get("problem_count") != len(problem_ids):
        raise ValueError("Manifest problem_count does not match problems")
    return value


def _safe_extract(archive: Path, destination: Path, expected: set[str]) -> None:
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or len(path.parts) != 2 or path.name != "testcases.json":
                raise ValueError(f"Unsafe testcase archive member: {member.name}")
            if path.parts[0] not in expected or not member.isfile():
                raise ValueError(f"Unexpected testcase archive member: {member.name}")
            target = destination / path
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError(f"Unable to read testcase archive member: {member.name}")
            target.write_bytes(source.read())


def fetch_testcase_bundle(manifest_url: str | None = None) -> dict:
    resolved_url = resolve_manifest_url(manifest_url)
    manifest = _validate_manifest(json.loads(_download(resolved_url).decode("utf-8")))
    archive_url = manifest.get("archive_url") or urljoin(resolved_url, manifest["filename"])
    payload = _download(archive_url)
    actual_sha = hashlib.sha256(payload).hexdigest()
    if actual_sha != manifest["sha256"]:
        raise ValueError(f"Testcase bundle checksum mismatch: expected {manifest['sha256']}, got {actual_sha}")

    root = Path.home() / ".faangtrail"
    staging = root / ".tmp-testcase-bundle"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    try:
        archive = staging / "bundle.tar.gz"
        archive.write_bytes(payload)
        extracted = staging / "bundle"
        extracted.mkdir()
        expected = set(manifest["problems"])
        _safe_extract(archive, extracted, expected)
        for problem_id in expected:
            if not (extracted / problem_id / "testcases.json").exists():
                raise ValueError(f"Archive is missing testcase file for {problem_id}")
        metadata = dict(manifest)
        metadata.update({"manifest_url": resolved_url, "archive_url": archive_url, "installed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")})
        (extracted / ".bundle.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if BUNDLE_DIR.exists():
            shutil.rmtree(BUNDLE_DIR)
        BUNDLE_DIR.parent.mkdir(parents=True, exist_ok=True)
        extracted.rename(BUNDLE_DIR)
        return metadata
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
