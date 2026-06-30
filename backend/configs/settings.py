"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmbeddingValidationSettings(BaseSettings):
    """Settings for embedding validation."""

    expected_dimension: int | None = Field(default=None, description="Expected embedding dimension")
    duplicate_tolerance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Tolerance threshold for duplicate detection (0.0 = exact only)",
    )
    validation_enabled: bool = Field(default=True, description="Enable embedding validation")
    strict_mode: bool = Field(
        default=False,
        description="Raise exceptions on validation failures instead of collecting errors",
    )
    warning_mode: bool = Field(
        default=False,
        description="Treat all validation failures as warnings",
    )

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_VALIDATION_",
        env_file=".env",
        extra="ignore",
    )


class IngestionSettings(BaseSettings):
    """Settings for document ingestion."""

    max_file_size_mb: int = Field(default=100, ge=1, le=1000)
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".markdown"]
    )
    default_encoding: str = "utf-8"
    default_language: str = "en"
    validate_checksum: bool = True

    model_config = SettingsConfigDict(
        env_prefix="INGESTION_",
        env_file=".env",
        extra="ignore",
    )

    @field_validator("supported_extensions")
    @classmethod
    def validate_extensions(cls, v: list[str]) -> list[str]:
        """Ensure all extensions start with a dot."""
        normalized = []
        for ext in v:
            if not ext.startswith("."):
                normalized.append(f".{ext}")
            else:
                normalized.append(ext)
        return normalized


class PreprocessingSettings(BaseSettings):
    """Settings for text preprocessing."""

    normalize_unicode: bool = True
    normalize_whitespace: bool = True
    remove_excessive_blank_lines: bool = True
    max_consecutive_blanks: int = Field(default=2, ge=1, le=5)
    preserve_paragraphs: bool = True

    model_config = SettingsConfigDict(
        env_prefix="PREPROCESSING_",
        env_file=".env",
        extra="ignore",
    )


class Settings(BaseSettings):
    """Main application settings."""

    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    preprocessing: PreprocessingSettings = Field(default_factory=PreprocessingSettings)
    embedding_validation: EmbeddingValidationSettings = Field(
        default_factory=EmbeddingValidationSettings
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance with loaded configuration.
    """
    return Settings()
