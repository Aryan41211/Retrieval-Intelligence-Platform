"""Pytest configuration for loader tests."""


import pytest


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Provide a temporary directory for tests."""
    return tmp_path_factory.mktemp("test_data")
