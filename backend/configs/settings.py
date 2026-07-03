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


class VectorStoreSettings(BaseSettings):
    """Settings for vector store."""

    provider: str = Field(default="faiss", description="Vector store provider (faiss, chromadb, etc.)")
    storage_dir: str = Field(default="./data/vectorstore", description="Directory for storing vector indexes")
    index_type: str = Field(default="flat", description="Default index type (flat, hnsw, ivf, pq)")
    distance_metric: str = Field(default="cosine", description="Default distance metric (cosine, euclidean, inner_product)")
    auto_save: bool = Field(default=True, description="Automatically save index after modifications")
    auto_load: bool = Field(default=True, description="Automatically load index on initialization")

    model_config = SettingsConfigDict(
        env_prefix="VECTOR_STORE_",
        env_file=".env",
        extra="ignore",
    )


class RetrievalSettings(BaseSettings):
    """Settings for retrieval engine."""

    top_k: int = Field(default=10, ge=1, le=1000, description="Default number of results to retrieve")
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    batch_size: int = Field(default=32, ge=1, le=1000, description="Batch size for batch retrieval operations")
    auto_load: bool = Field(default=True, description="Automatically load index on initialization")
    auto_save: bool = Field(default=True, description="Automatically save index after modifications")

    # Default filters (optional)
    default_languages: list[str] | None = Field(default=None, description="Default language filters")
    default_source_filenames: list[str] | None = Field(default=None, description="Default source filename filters")

    model_config = SettingsConfigDict(
        env_prefix="RETRIEVAL_",
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
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)

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
