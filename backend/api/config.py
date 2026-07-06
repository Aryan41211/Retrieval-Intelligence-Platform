"""
Runtime configuration for the FastAPI application.

Centralises environment-driven settings for the API layer: server binding,
CORS, logging, security headers, rate limiting, and observability. All values
are validated on startup (fail-fast) and read from environment variables with
the ``API_`` prefix so they never need to be hardcoded.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Runtime settings for the API process.

    Validation intentionally fails fast: an invalid combination (e.g. wildcard
    CORS origins together with credentialed requests) raises at import time so
    misconfiguration cannot reach production silently.
    """

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_file=".env",
        extra="ignore",
    )

    # --- Environment / identity ------------------------------------------------
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment; drives security and docs defaults.",
    )
    app_name: str = Field(
        default="retrieval-intelligence-platform",
        description="Human-readable service name used in logs and metrics.",
    )
    api_prefix: str = Field(
        default="/api/v1",
        description="URL prefix for all versioned API routers.",
    )

    # --- Server ----------------------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Bind host for the HTTP server.")
    port: int = Field(default=8000, ge=1, le=65535, description="Bind port for the HTTP server.")
    debug: bool = Field(
        default=False,
        description="Enable debug behaviour. Automatically disabled in production.",
    )
    docs_enabled: bool = Field(
        default=True,
        description="Expose /docs, /redoc and /openapi.json. Disabled in production by default.",
    )
    request_timeout_seconds: int = Field(
        default=30, ge=1, le=600, description="Max request processing time in seconds."
    )
    max_request_size_mb: int = Field(
        default=100, ge=1, le=2048, description="Maximum accepted request body size in MB."
    )

    # --- CORS ------------------------------------------------------------------
    cors_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed CORS origins. Avoid '*' together with credentials in production.",
    )
    cors_credentials: bool = Field(default=False, description="Allow credentialed CORS requests.")
    cors_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="Allowed CORS HTTP methods.",
    )
    cors_headers: list[str] = Field(
        default_factory=lambda: ["*"], description="Allowed CORS request headers."
    )

    # --- Rate limiting ---------------------------------------------------------
    rate_limit_per_minute: int = Field(
        default=120, ge=1, description="Sustained requests allowed per client IP per minute."
    )
    rate_limit_burst: int = Field(
        default=20, ge=1, description="Burst capacity above the sustained rate per client IP."
    )

    # --- Logging ---------------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Minimum log level for the root logger."
    )
    log_format: Literal["json", "text"] = Field(
        default="json", description="Structured JSON logging or human-readable text."
    )
    log_file: str | None = Field(
        default=None, description="Optional file path for logs; stdout/stderr when unset."
    )

    # --- Security headers ------------------------------------------------------
    security_headers_enabled: bool = Field(
        default=True, description="Emit baseline HTTP security headers on every response."
    )
    hsts_enabled: bool = Field(
        default=False, description="Emit Strict-Transport-Security. Enable only behind TLS."
    )
    csp_policy: str = Field(
        default="default-src 'self'",
        description="Content-Security-Policy value applied to HTML responses.",
    )

    # --- Observability ---------------------------------------------------------
    prometheus_enabled: bool = Field(
        default=True, description="Expose a Prometheus /metrics endpoint."
    )
    correlation_header: str = Field(
        default="X-Correlation-ID", description="Header used to carry request correlation IDs."
    )

    @field_validator("debug")
    @classmethod
    def _normalize_debug(cls, value: bool, info: object) -> bool:
        """Disable debug mode outside of development environments."""
        env = getattr(info, "data", {}).get("environment")
        if env == "production" and value:
            return False
        return value

    @field_validator("docs_enabled")
    @classmethod
    def _normalize_docs(cls, value: bool, info: object) -> bool:
        """Disable interactive docs in production by default."""
        env = getattr(info, "data", {}).get("environment")
        if env == "production" and value:
            return False
        return value

    def validate_for_environment(self) -> None:
        """Perform cross-field validation that pydantic cannot express alone.

        Raises:
            ValueError: If credentialed CORS is configured with a wildcard origin.
        """
        if self.cors_credentials and "*" in self.cors_origins:
            raise ValueError(
                "CORS misconfiguration: wildcard origin '*' cannot be used with "
                "credentialed requests (cors_credentials=True). Set explicit origins."
            )


@lru_cache
def get_settings() -> APISettings:
    """Return a cached :class:`APISettings` instance.

    Returns:
        Validated API settings loaded from the environment.
    """
    settings = APISettings()
    settings.validate_for_environment()
    return settings


# Backwards-compatible singleton used by modules that referenced ``settings``.
settings = get_settings()
