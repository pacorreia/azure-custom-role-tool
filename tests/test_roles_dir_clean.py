"""Regression guard: tests must not leak role files into repository roles/ directory."""

from pathlib import Path
import re


_LIKELY_TEST_FILE_PATTERNS = [
    r"\.json\.json$",
    r"(^|[-_])(test|tmp|fixture|dummy|sample)([-_.]|$)",
    r"(^|[-_])(quick-save|save-test|prompt-target|duplicate|file-role)([-_.]|$)",
]


def _is_likely_test_artifact(filename: str) -> bool:
    """Best-effort heuristic for identifying files typically produced by tests."""
    if filename == ".gitkeep":
        return False

    lower_name = filename.lower()
    return any(re.search(pattern, lower_name) for pattern in _LIKELY_TEST_FILE_PATTERNS)


def test_repo_roles_dir_is_clean():
    """Ensure tests didn't leak likely test artifacts into repository roles/ directory."""
    repo_root = Path(__file__).resolve().parents[1]
    roles_dir = repo_root / "roles"

    assert roles_dir.exists(), "Expected repository roles/ directory to exist"

    entries = sorted(child.name for child in roles_dir.iterdir() if child.is_file())
    suspicious = [name for name in entries if _is_likely_test_artifact(name)]

    assert not suspicious, (
        "roles/ contains likely test artifacts. "
        "Tests should use isolated temp RoleManager directories. "
        f"Suspicious files: {suspicious}; all files: {entries}"
    )
