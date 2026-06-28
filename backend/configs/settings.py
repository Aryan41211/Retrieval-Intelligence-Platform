"""Application settings using pydantic-settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
