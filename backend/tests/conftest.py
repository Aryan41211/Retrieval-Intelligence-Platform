"""Shared pytest configuration for the backend test suite.

Applies the ``unit`` / ``integration`` / ``enterprise`` markers automatically
based on the directory a test lives in. CI selects tests with ``-m`` filters, so
markers that are never applied mean CI silently runs zero tests.
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_TESTS_ROOT = Path(__file__).resolve().parent

# Directory name under backend/tests/ -> marker applied to every test inside it.
_DIRECTORY_MARKERS = {
    "unit": "unit",
    "integration": "integration",
    "enterprise": "enterprise",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Tag each collected test with the marker for its top-level directory."""
    for item in items:
        try:
            relative = Path(str(item.fspath)).resolve().relative_to(_TESTS_ROOT)
        except ValueError:  # pragma: no cover - test outside backend/tests
            continue
        if not relative.parts:
            continue
        marker = _DIRECTORY_MARKERS.get(relative.parts[0])
        if marker is not None:
            item.add_marker(getattr(pytest.mark, marker))
