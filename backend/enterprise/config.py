"""
Enterprise configuration.

All values are environment-driven (prefix ``ENTERPRISE_``) and validated on
startup. The JWT signing secret is mandatory in production and must be sourced
from a secret manager, never committed.
"""

from functools import lru_cache
from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnterpriseSettings(BaseSettings):
    """Settings for enterprise/authentication features."""

    model_config = SettingsConfigDict(
        env_prefix="ENTERPRISE_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = Field(
        default="development", description="Deployment environment (dev/staging/prod)."
    )

    jwt_secret_key: str = Field(
        default="",
        description="Secret used to sign JWTs. REQUIRED and must be strong in production.",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_ttl_seconds: int = Field(
        default=900, ge=60, le=3600, description="Access token lifetime in seconds."
    )
    refresh_token_ttl_seconds: int = Field(
        default=604800, ge=3600, le=2592000, description="Refresh token lifetime in seconds."
    )
    password_reset_ttl_seconds: int = Field(
        default=3600, ge=300, le=86400, description="Password reset token lifetime."
    )
    email_verification_ttl_seconds: int = Field(
        default=86400, ge=3600, le=604800, description="Email verification token lifetime."
    )
    registration_enabled: bool = Field(default=True, description="Allow open self-registration.")
    email_verification_required: bool = Field(
        default=False, description="Require verified email before issuing tokens."
    )
    default_role: str = Field(default="member", description="Role assigned to new users.")
    audit_enabled: bool = Field(default=True, description="Persist audit/activity logs.")
    oauth_enabled: bool = Field(default=False, description="Enable OAuth login providers.")
    oauth_google_client_id: str | None = Field(default=None, description="Google OAuth client id.")
    oauth_google_client_secret: str | None = Field(
        default=None, description="Google OAuth client secret (secret)."
    )
    oauth_google_redirect_uri: str | None = Field(
        default=None, description="OAuth callback redirect URI."
    )
    smtp_host: str | None = Field(default=None, description="SMTP host for outbound email.")
    smtp_from: str | None = Field(default=None, description="From address for outbound email.")

    #: Minimum acceptable length for the JWT signing secret.
    MIN_JWT_SECRET_LENGTH: ClassVar[int] = 32

    #: Placeholder values that must never be used as a signing secret.
    FORBIDDEN_SECRETS: ClassVar[frozenset[str]] = frozenset(
        {
            "dev-insecure-change-me",
            "change-me",
            "changeme",
            "secret",
            "password",
            "your-secret-key",
        }
    )

    #: Substrings that mark a secret as a copied placeholder rather than a
    #: generated one. FORBIDDEN_SECRETS only matches exact strings, so values
    #: like "dev-secret-key-change-in-production-32chars-long" satisfied every
    #: length and entropy check while being entirely predictable. These are
    #: enforced in production only; throwaway values are fine for local and CI
    #: runs, which is exactly where they belong.
    PLACEHOLDER_MARKERS: ClassVar[tuple[str, ...]] = (
        "change-in-production",
        "change-me",
        "change_me",
        "changeme",
        "changein",
        "ci-only",
        "dev-secret",
        "dummy",
        "example",
        "insecure",
        "not-a-real",
        "not-for-prod",
        "placeholder",
        "sample",
        "test-secret",
        "your-secret",
    )

    @classmethod
    def placeholder_marker(cls, value: str) -> str | None:
        """Return the placeholder marker found in ``value``, if any.

        Args:
            value: A candidate signing secret.

        Returns:
            The first matching marker, or ``None`` when the value shows no sign
            of being a copied placeholder.
        """
        lowered = value.strip().lower()
        for marker in cls.PLACEHOLDER_MARKERS:
            if marker in lowered:
                return marker
        return None

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_secret(cls, value: str) -> str:
        """Reject absent, placeholder, or low-entropy signing secrets.

        The previous check only rejected two literal strings, so a 3-character
        secret passed validation and produced trivially forgeable tokens.
        """
        guidance = "Generate one with: openssl rand -hex 32"
        if not value:
            raise ValueError(f"ENTERPRISE_JWT_SECRET_KEY must be set. {guidance}")
        if value.strip().lower() in cls.FORBIDDEN_SECRETS:
            raise ValueError(
                f"ENTERPRISE_JWT_SECRET_KEY must not be a placeholder value. {guidance}"
            )
        if len(value) < cls.MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                "ENTERPRISE_JWT_SECRET_KEY must be at least "
                f"{cls.MIN_JWT_SECRET_LENGTH} characters (got {len(value)}). {guidance}"
            )
        if len(set(value)) < 8:
            raise ValueError(
                f"ENTERPRISE_JWT_SECRET_KEY has too little variety to be random. {guidance}"
            )
        return value


@lru_cache
def get_enterprise_settings() -> EnterpriseSettings:
    """Return a cached :class:`EnterpriseSettings` instance."""
    return EnterpriseSettings()


settings = get_enterprise_settings()
