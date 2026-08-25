"""The deployment preflight must reject exactly what production rejects.

``scripts/bootstrap_deployment.py`` gated the signing secret on length alone.
``.env.example``'s own placeholder is 48 characters, so a fresh host ran
``bootstrap_deployment.py``, was told "Deployment prerequisites satisfied", and
then hit ``configuration validation failed`` the moment
``API_ENVIRONMENT=production`` was set - the preflight passed a host that could
not deploy.

The script cannot import ``EnterpriseSettings`` to reuse its rules, because that
module validates at import time and raises without a signing secret - precisely
the state the bootstrap exists to repair. The rules are therefore duplicated,
and these tests pin the copies to the originals.
"""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

from backend.enterprise.config import EnterpriseSettings

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bootstrap_deployment.py"


def _load_script():
    """Import the bootstrap script by path; ``scripts/`` is not a package."""
    spec = importlib.util.spec_from_file_location("bootstrap_deployment", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = _load_script()


@pytest.mark.unit
class TestRulesMirrorTheSettingsLayer:
    """The duplicated constants must not drift from EnterpriseSettings."""

    def test_placeholder_markers_match(self) -> None:
        assert bootstrap.PLACEHOLDER_MARKERS == EnterpriseSettings.PLACEHOLDER_MARKERS

    def test_minimum_length_matches(self) -> None:
        assert bootstrap.MIN_JWT_LENGTH == EnterpriseSettings.MIN_JWT_SECRET_LENGTH

    def test_placeholder_detection_agrees(self) -> None:
        secret = "dev-secret-key-change-in-production-32chars-long"
        assert bootstrap.placeholder_marker(secret) == EnterpriseSettings.placeholder_marker(secret)


@pytest.mark.unit
class TestSecretProblem:
    """A secret production would refuse must not pass the preflight."""

    @pytest.mark.parametrize(
        "secret",
        [
            "dev-secret-key-change-in-production-32chars-long",
            "test-secret-key-not-for-prod-use-1234567890",
            "ci-only-not-a-real-secret-0123456789abcdef0123456789abcdef",
            "example-signing-key-for-the-docs-0123456789",
        ],
    )
    def test_long_placeholders_are_rejected(self, secret: str) -> None:
        assert len(secret) >= bootstrap.MIN_JWT_LENGTH, "fixture must clear the length gate"
        assert bootstrap.secret_problem(secret) is not None

    def test_short_secret_is_rejected(self) -> None:
        assert "characters" in (bootstrap.secret_problem("abc123") or "")

    def test_low_variety_secret_is_rejected(self) -> None:
        assert bootstrap.secret_problem("ab" * 32) is not None

    def test_generated_secret_is_accepted(self) -> None:
        secret = "9f2c41ab7d05e6389c1a4be27f0d8635a91c47e0bd23c8f7a15e6094db3f27ac"
        assert bootstrap.secret_problem(secret) is None
