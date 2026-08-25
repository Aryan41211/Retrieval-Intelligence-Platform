"""The production gate must refuse a copied placeholder signing secret.

``EnterpriseSettings.FORBIDDEN_SECRETS`` matches six exact strings, so the
shapes people actually paste - ``dev-secret-key-change-in-production-...``,
``test-secret-key-not-for-prod-use-...`` - passed every length and entropy
check. A predictable HS256 key means anyone can mint an admin token, so
``API_ENVIRONMENT=production`` now refuses to start on one.

Throwaway secrets stay legal outside production: that is where they belong, and
the test suite and CI both rely on them.
"""

from __future__ import annotations

import pytest

from backend.api.config import APISettings
from backend.enterprise.config import EnterpriseSettings

PLACEHOLDERS = [
    "dev-secret-key-change-in-production-32chars-long",
    "test-secret-key-not-for-prod-use-1234567890",
    "ci-only-not-a-real-secret-0123456789abcdef0123456789abcdef",
    "please-change-me-before-going-live-0123456789",
    "example-signing-key-for-the-docs-0123456789",
    "insecure-development-signing-key-0123456789",
]

GENERATED = [
    "9f2c41ab7d05e6389c1a4be27f0d8635a91c47e0bd23c8f7a15e6094db3f27ac",
    "4b81de07c93a5f26e0a7bc4318d5920fae63c07b18d4e2a95c60f73b8e1d4a02",
]


@pytest.mark.parametrize("secret", PLACEHOLDERS)
def test_placeholder_secrets_are_recognised(secret: str) -> None:
    """Each realistic placeholder shape is detected."""
    assert EnterpriseSettings.placeholder_marker(secret) is not None


@pytest.mark.parametrize("secret", GENERATED)
def test_generated_secrets_are_not_flagged(secret: str) -> None:
    """A `secrets.token_hex(32)` value is never mistaken for a placeholder."""
    assert EnterpriseSettings.placeholder_marker(secret) is None


@pytest.mark.parametrize("secret", PLACEHOLDERS)
def test_production_refuses_to_start_on_a_placeholder(
    monkeypatch: pytest.MonkeyPatch, secret: str
) -> None:
    """`validate_for_environment` raises in production for a placeholder."""
    monkeypatch.setattr(
        "backend.enterprise.config.get_enterprise_settings",
        lambda: EnterpriseSettings(jwt_secret_key=secret),
    )
    settings = APISettings(
        environment="production",
        cors_origins=["https://app.example.com"],
        trusted_hosts=["app.example.com"],
    )

    with pytest.raises(ValueError, match="looks like a placeholder"):
        settings.validate_for_environment()


def test_production_accepts_a_generated_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """A properly generated secret passes the production gate."""
    monkeypatch.setattr(
        "backend.enterprise.config.get_enterprise_settings",
        lambda: EnterpriseSettings(jwt_secret_key=GENERATED[0]),
    )
    settings = APISettings(
        environment="production",
        cors_origins=["https://app.example.com"],
        trusted_hosts=["app.example.com"],
    )

    settings.validate_for_environment()


@pytest.mark.parametrize("environment", ["development", "staging"])
def test_non_production_tolerates_a_placeholder(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    """Local and CI runs may keep using throwaway secrets."""
    monkeypatch.setattr(
        "backend.enterprise.config.get_enterprise_settings",
        lambda: EnterpriseSettings(jwt_secret_key=PLACEHOLDERS[0]),
    )
    settings = APISettings(environment=environment)

    settings.validate_for_environment()
