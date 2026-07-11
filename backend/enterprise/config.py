"""
Enterprise configuration.

All values are environment-driven (prefix ``ENTERPRISE_``) and validated on
startup. The JWT signing secret is mandatory in production and must be sourced
from a secret manager, never committed.
"""

from functools import lru_cache

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
    registration_enabled: bool = Field(
        default=True, description="Allow open self-registration."
    )
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

    @field_validator("jwt_secret_key")
    @classmethod
    def _validate_secret(cls, value: str) -> str:
        if not value or value in ("dev-insecure-change-me", "change-me"):
            raise ValueError(
                "ENTERPRISE_JWT_SECRET_KEY must be set to a strong, non-default value. "
                "Generate one with: openssl rand -hex 32"
            )
        return value


@lru_cache
def get_enterprise_settings() -> EnterpriseSettings:
    """Return a cached :class:`EnterpriseSettings` instance."""
    return EnterpriseSettings()


settings = get_enterprise_settings()
