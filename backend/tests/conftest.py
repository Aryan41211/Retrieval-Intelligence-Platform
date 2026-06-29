"""Pytest configuration for loader tests."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide a temporary directory for tests."""
    return tmp_path_factory.mktemp("test_data")
