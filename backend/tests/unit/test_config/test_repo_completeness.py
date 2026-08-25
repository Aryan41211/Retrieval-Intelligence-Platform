"""No backend source file may be hidden from git by an ignore rule.

``.gitignore`` carried a bare ``models/`` rule meant for downloaded weights. It
also matched ``backend/data/models/`` - the domain-model package - so five source
files were never committed while remaining present in the working tree, where
every local test run and every local Docker build used them happily. The gap only
surfaced when a clean clone was built and deployed:

    configuration validation failed:
    ModuleNotFoundError: No module named 'backend.data.models'

A working tree that passes is not evidence that a checkout does, so this asserts
against git's own view rather than the filesystem's.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]

#: Directories that legitimately hold generated or vendored files.
EXCLUDED = ("__pycache__", "node_modules", ".venv", "site-packages", ".egg-info")


def _git(*args: str) -> list[str]:
    """Run a git command in the repo root and return its non-empty output lines."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed"),
    pytest.mark.skipif(
        not (REPO_ROOT / ".git").exists(), reason="not a git checkout (sdist or image)"
    ),
]


def test_no_backend_source_file_is_git_ignored() -> None:
    """A Python file under backend/ that git ignores cannot reach a deployment."""
    ignored = _git("ls-files", "--others", "--ignored", "--exclude-standard", "backend")
    hidden = [
        path
        for path in ignored
        if path.endswith(".py") and not any(part in path for part in EXCLUDED)
    ]
    assert not hidden, (
        "These backend source files are excluded by .gitignore, so they exist locally "
        f"but are missing from any clone: {hidden}. Narrow the offending pattern."
    )
